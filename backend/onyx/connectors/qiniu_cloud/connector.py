"""
七牛云存储连接器

提供七牛云对象存储服务的完整集成，支持：
- 文件上传和下载
- 通过前缀模拟文件夹管理
- 文档索引和同步
- 增量和全量数据处理
"""

import os
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Set, Tuple

from qiniu import Auth, put_file, put_data, BucketManager
import requests

from onyx.configs.app_configs import INDEX_BATCH_SIZE
from onyx.configs.constants import DocumentSource, FileOrigin
from onyx.connectors.qiniu_cloud.exceptions import (
    QiniuConnectorError,
    QiniuCredentialError,
    QiniuBucketError,
    QiniuUploadError,
    QiniuDownloadError,
    handle_qiniu_exception,
)
from onyx.connectors.cross_connector_utils.miscellaneous_utils import (
    process_onyx_metadata,
)
from onyx.connectors.exceptions import ConnectorValidationError
from onyx.connectors.interfaces import GenerateDocumentsOutput, LoadConnector, PollConnector, SecondsSinceUnixEpoch
from onyx.connectors.models import ConnectorMissingCredentialError, Document, ImageSection, TextSection
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.file_processing.extract_file_text import extract_text_and_images, get_file_ext, is_accepted_file_ext, OnyxExtensionType
from onyx.file_processing.image_utils import store_image_and_create_section
from onyx.utils.logger import setup_logger

logger = setup_logger()


class QiniuCloudConnector(LoadConnector, PollConnector):
    """
    七牛云存储连接器
    
    支持文件上传、下载、索引和同步功能
    """
    
    def __init__(
        self,
        bucket_name: str,
        bucket_domain: str,
        region: str = "cn-east-1",
        prefix: str = "",
        folder_uuid: str = None,
        auto_create_folder: bool = True,
        folder_uuid_length: int = 10,
        batch_size: int = INDEX_BATCH_SIZE,
    ):
        """
        初始化七牛云存储连接器
        
        Args:
            bucket_name: 存储桶名称
            bucket_domain: 存储桶域名
            region: 区域
            prefix: 对象键前缀
            folder_uuid: 文件夹 UUID
            auto_create_folder: 是否自动创建文件夹
            folder_uuid_length: 文件夹 UUID 长度
            batch_size: 批处理大小
        """
        self.bucket_name = bucket_name
        self.bucket_domain = bucket_domain.rstrip("/")
        self.region = region
        self.prefix = prefix.rstrip("/") if prefix else ""
        self.folder_uuid = folder_uuid
        self.auto_create_folder = auto_create_folder
        self.folder_uuid_length = folder_uuid_length
        self.batch_size = batch_size
        
        # 七牛云认证和管理对象
        self.auth: Optional[Auth] = None
        self.bucket_manager: Optional[BucketManager] = None
        
        # 图像处理设置
        self._allow_images: bool = True
        
        # 连接器状态
        self._is_initialized = False
        
        # 文件夹分隔符和占位文件名
        self.folder_separator = "/"
        self.placeholder_filename = ".folder_placeholder"
    
    def set_allow_images(self, allow_images: bool) -> None:
        """设置是否允许处理图像"""
        logger.info(f"Setting allow_images to {allow_images}")
        self._allow_images = allow_images
    
    @handle_qiniu_exception
    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        加载七牛云存储凭证
        
        Args:
            credentials: 凭证字典，包含：
                - access_key: 访问密钥
                - secret_key: 密钥
                - bucket_domain: 可选，存储桶域名
        
        Returns:
            None
        """
        logger.debug(f"Loading Qiniu credentials for bucket: {self.bucket_name}")
        
        # 检查必需的凭证，支持环境变量回退
        from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
        
        access_key = credentials.get("access_key") or QINIU_ACCESS_KEY
        secret_key = credentials.get("secret_key") or QINIU_SECRET_KEY
        
        if not access_key or not secret_key:
            raise ConnectorMissingCredentialError("七牛云存储")
        
        # 获取存储桶域名，支持环境变量回退
        from onyx.configs.app_configs import QINIU_BUCKET_DOMAIN
        
        bucket_domain = credentials.get("bucket_domain") or QINIU_BUCKET_DOMAIN
        if bucket_domain:
            self.bucket_domain = bucket_domain.rstrip("/")
        
        # 创建认证对象
        self.auth = Auth(access_key, secret_key)
        self.bucket_manager = BucketManager(self.auth)
        
        # 标记为已初始化
        self._is_initialized = True
        
        logger.info(f"Qiniu client initialized for bucket: {self.bucket_name}")
        return None
    
    def _ensure_initialized(self) -> None:
        """确保连接器已初始化"""
        if not self._is_initialized or not self.auth:
            raise ConnectorMissingCredentialError("七牛云存储")
    
    def _get_folder_prefix(self, folder_uuid: str) -> str:
        """获取文件夹前缀"""
        if self.prefix:
            return f"{self.prefix}/{folder_uuid}"
        return folder_uuid
    
    def _create_placeholder_key(self, folder_uuid: str) -> str:
        """创建占位文件键"""
        folder_prefix = self._get_folder_prefix(folder_uuid)
        return f"{folder_prefix}/{self.placeholder_filename}"
    
    def create_object_key(self, folder_uuid: str, filename: str) -> str:
        """创建对象键"""
        folder_prefix = self._get_folder_prefix(folder_uuid)
        return f"{folder_prefix}/{filename}"
    
    def parse_object_key(self, object_key: str) -> Tuple[str, str]:
        """解析对象键，提取文件夹前缀和文件名"""
        # 移除前缀
        if self.prefix and object_key.startswith(f"{self.prefix}/"):
            object_key = object_key[len(self.prefix) + 1:]
        
        # 分离文件夹和文件名
        parts = object_key.split("/")
        if len(parts) < 2:
            # 如果没有文件夹结构，使用根目录
            return "root", object_key
        
        folder_prefix = parts[0]
        filename = "/".join(parts[1:])
        
        return folder_prefix, filename
    
    def discover_existing_folders(self) -> Set[str]:
        """
        发现七牛云OSS中已有的文件夹前缀
        
        Returns:
            已有文件夹前缀的集合
        """
        folders = set()
        
        try:
            # 构建基础前缀
            base_prefix = self.prefix + "/" if self.prefix else ""
            
            # 列出对象
            marker = None
            while True:
                ret, eof, info = self.bucket_manager.list(
                    self.bucket_name,
                    prefix=base_prefix,
                    marker=marker,
                    limit=1000
                )
                
                if ret is None:
                    logger.warning(f"Failed to list objects: {info}")
                    break
                
                for item in ret.get("items", []):
                    object_key = item.get("key", "")
                    if object_key:
                        # 解析对象键，提取文件夹前缀
                        try:
                            folder_prefix, _ = self.parse_object_key(object_key)
                            if folder_prefix and folder_prefix != "root":
                                folders.add(folder_prefix)
                        except Exception as e:
                            logger.debug(f"Failed to parse object key {object_key}: {e}")
                            continue
                
                if eof:
                    break
                marker = ret.get("marker")
            
            logger.info(f"Discovered {len(folders)} existing folders: {sorted(folders)}")
            return folders
            
        except Exception as e:
            logger.error(f"Error discovering existing folders: {e}")
            return set()
    
    @handle_qiniu_exception
    def _download_object(self, object_key: str) -> bytes:
        """
        下载七牛云对象
        
        Args:
            object_key: 对象键
            
        Returns:
            对象内容字节
        """
        self._ensure_initialized()
        
        logger.info(f"Downloading object: {object_key}")
        
        # 生成下载链接
        download_url = f"http://{self.bucket_domain}/{object_key}"
        
        # 如果是私有空间，需要生成签名URL
        private_url = self.auth.private_download_url(download_url, expires=3600)
        
        # 使用 requests session 确保连接正确关闭，避免资源泄漏
        with requests.Session() as session:
            response = session.get(private_url, timeout=30)
            response.raise_for_status()
            
            content = response.content
            content_size = len(content)
            logger.info(f"Downloaded {object_key}: {content_size} bytes")
            
            return content
    
    @handle_qiniu_exception
    def _get_object_metadata(self, object_key: str) -> Dict[str, Any]:
        """
        获取对象元数据
        
        Args:
            object_key: 对象键
            
        Returns:
            对象元数据
        """
        self._ensure_initialized()
        
        ret, info = self.bucket_manager.stat(self.bucket_name, object_key)
        
        if ret is None:
            raise QiniuDownloadError(object_key, f"获取对象元数据失败: {info}")
        
        return {
            "content_length": ret.get("fsize", 0),
            "content_type": ret.get("mimeType", "application/octet-stream"),
            "last_modified": datetime.fromtimestamp(ret.get("putTime", 0) / 10000000, tz=timezone.utc),
            "etag": ret.get("hash", ""),
            "metadata": ret
        }
    
    def _get_qiniu_link(self, object_key: str) -> str:
        """
        生成七牛云对象链接
        
        Args:
            object_key: 对象键
            
        Returns:
            七牛云对象链接
        """
        return f"http://{self.bucket_domain}/{object_key}"
    
    def _create_image_section(
        self, 
        image_data: bytes, 
        object_key: str, 
        filename: str,
        link: str,
        db_session
    ) -> ImageSection:
        """
        创建图像节
        
        Args:
            image_data: 图像数据
            object_key: 对象键
            filename: 文件名
            link: 链接
            db_session: 数据库会话
            
        Returns:
            图像节
        """
        # 生成唯一的文件 ID
        file_id = f"QINIU_{self.bucket_name}_{object_key.replace('/', '_')}"
        
        # 存储图像并创建节
        section, _ = store_image_and_create_section(
            db_session=db_session,
            image_data=image_data,
            file_id=file_id,
            display_name=filename,
            link=link,
            file_origin=FileOrigin.CONNECTOR,
        )
        
        return section
    
    def _process_qiniu_object(
        self, 
        object_key: str, 
        last_modified: datetime,
        db_session
    ) -> Document | None:
        """
        处理七牛云对象并转换为 Document
        
        Args:
            object_key: 对象键
            last_modified: 最后修改时间
            db_session: 数据库会话
            
        Returns:
            Document 对象或 None
        """
        try:
            # 解析对象键
            folder_uuid, filename = self.parse_object_key(object_key)
            
            # 跳过占位文件
            if filename == self.placeholder_filename:
                return None
            
            # 检查文件扩展名
            file_ext = get_file_ext(filename)
            if not is_accepted_file_ext(file_ext, OnyxExtensionType.All):
                logger.debug(f"Skipping unsupported file: {filename}")
                return None
            
            # 下载对象内容
            object_content = self._download_object(object_key)
            
            # 生成链接
            link = self._get_qiniu_link(object_key)
            
            # 生成文档 ID
            doc_id = f"QINIU_CLOUD:{self.bucket_name}:{object_key}"
            
            # 处理图像文件
            if file_ext in LoadConnector.IMAGE_EXTENSIONS:
                if not self._allow_images:
                    logger.debug(f"Skipping image file: {object_key} (image processing disabled)")
                    return None
                
                image_section = self._create_image_section(
                    object_content, object_key, filename, link, db_session
                )
                
                return Document(
                    id=doc_id,
                    sections=[image_section],
                    source=DocumentSource.QINIU_CLOUD,
                    semantic_identifier=filename,
                    doc_updated_at=last_modified,
                    metadata={"folder_prefix": folder_uuid}
                )
            
            # 处理文档文件
            try:
                extraction_result = extract_text_and_images(
                    BytesIO(object_content), 
                    file_name=filename
                )
                
                # 处理 Onyx 元数据
                onyx_metadata, custom_tags = process_onyx_metadata(
                    extraction_result.metadata or {}
                )
                
                # 处理source链接 - 优先级：front matter link > metadata link > OSS链接
                source_link = (
                    extraction_result.metadata.get('source_link') or  # Markdown front matter link
                    onyx_metadata.link or                            # 传统onyx metadata link
                    link                                             # OSS生成的链接
                )
                
                # 使用元数据或默认值
                file_display_name = onyx_metadata.file_display_name or filename
                time_updated = onyx_metadata.doc_updated_at or last_modified
                primary_owners = onyx_metadata.primary_owners
                secondary_owners = onyx_metadata.secondary_owners
                
                # 添加文件夹信息到元数据
                custom_tags["folder_prefix"] = folder_uuid  # 现在使用实际的文件夹前缀
                custom_tags["object_key"] = object_key
                
                # 创建文档节
                sections: List[TextSection | ImageSection] = []
                
                # 添加文本节
                if extraction_result.text_content.strip():
                    sections.append(
                        TextSection(
                            link=source_link,
                            text=extraction_result.text_content.strip()
                        )
                    )
                
                # 添加嵌入图像节
                for idx, (img_data, img_name) in enumerate(
                    extraction_result.embedded_images, start=1
                ):
                    try:
                        image_section = self._create_image_section(
                            img_data, f"{object_key}_image_{idx}", 
                            f"{filename} - image {idx}", source_link, db_session
                        )
                        sections.append(image_section)
                    except Exception as e:
                        logger.warning(f"Failed to process embedded image {idx} in {filename}: {e}")
                
                # 创建文档
                return Document(
                    id=doc_id,
                    sections=sections if sections else [TextSection(link=source_link, text="")],
                    source=DocumentSource.QINIU_CLOUD,
                    semantic_identifier=file_display_name,
                    doc_updated_at=time_updated,
                    metadata=custom_tags,
                    primary_owners=primary_owners,
                    secondary_owners=secondary_owners
                )
                
            except Exception as e:
                logger.error(f"Failed to process document {object_key}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to process Qiniu object {object_key}: {e}")
            return None
    
    def _yield_qiniu_objects(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> GenerateDocumentsOutput:
        """
        生成七牛云对象文档
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Yields:
            Document 批次
        """
        self._ensure_initialized()
        
        batch: List[Document] = []
        total_objects = 0
        processed_objects = 0
        successful_documents = 0
        
        logger.info(f"Starting Qiniu objects processing with prefix: {self.prefix}")
        
        try:
            # 使用分页获取对象列表
            marker = None
            
            with get_session_with_current_tenant() as db_session:
                while True:
                    ret, eof, info = self.bucket_manager.list(
                        self.bucket_name,
                        prefix=self.prefix,
                        marker=marker,
                        limit=1000
                    )
                    
                    if ret is None:
                        logger.error(f"Failed to list objects: {info}")
                        break
                    
                    for item in ret.get("items", []):
                        object_key = item["key"]
                        total_objects += 1
                        
                        # 跳过目录
                        if object_key.endswith("/"):
                            continue
                        
                        # 检查时间范围
                        put_time = item.get("putTime", 0)
                        last_modified = datetime.fromtimestamp(put_time / 10000000, tz=timezone.utc)
                        
                        if not (start_time <= last_modified <= end_time):
                            continue
                        
                        processed_objects += 1
                        logger.info(f"Processing file: {object_key}")
                        
                        # 处理对象
                        document = self._process_qiniu_object(
                            object_key, last_modified, db_session
                        )
                        
                        if document:
                            batch.append(document)
                            successful_documents += 1
                            logger.info(f"Successfully processed: {object_key} -> Document ID: {document.id}")
                            
                            # 达到批次大小时生成批次
                            if len(batch) >= self.batch_size:
                                yield batch
                                batch = []
                        else:
                            logger.warning(f"Failed to create document for: {object_key}")
                    
                    if eof:
                        break
                    marker = ret.get("marker")
                
                # 生成最后一个批次
                if batch:
                    yield batch
                
                logger.info(f"Qiniu processing complete - Total: {total_objects}, Processed: {processed_objects}, Success: {successful_documents}")
                    
        except Exception as e:
            logger.error(f"Error yielding Qiniu objects: {e}")
            raise
    
    def load_from_state(self) -> GenerateDocumentsOutput:
        """
        全量加载文档
        
        Returns:
            Document 生成器
        """
        logger.info(f"Loading all documents from Qiniu bucket: {self.bucket_name}")
        
        return self._yield_qiniu_objects(
            start_time=datetime(1970, 1, 1, tzinfo=timezone.utc),
            end_time=datetime.now(timezone.utc)
        )
    
    def poll_source(
        self, 
        start: SecondsSinceUnixEpoch, 
        end: SecondsSinceUnixEpoch
    ) -> GenerateDocumentsOutput:
        """
        增量同步文档
        
        Args:
            start: 开始时间戳
            end: 结束时间戳
            
        Returns:
            Document 生成器
        """
        start_datetime = datetime.fromtimestamp(start, tz=timezone.utc)
        end_datetime = datetime.fromtimestamp(end, tz=timezone.utc)
        
        logger.info(f"Polling Qiniu documents from {start_datetime} to {end_datetime}")
        
        return self._yield_qiniu_objects(start_datetime, end_datetime)
    
    @handle_qiniu_exception
    def validate_connector_settings(self) -> None:
        """验证连接器设置"""
        self._ensure_initialized()
        
        if not self.bucket_name:
            raise ConnectorValidationError("存储桶名称不能为空")
        
        if not self.bucket_domain:
            raise ConnectorValidationError("存储桶域名不能为空")
        
        try:
            # 测试列举对象权限
            ret, eof, info = self.bucket_manager.list(
                self.bucket_name,
                prefix=self.prefix,
                limit=1
            )
            
            if ret is None:
                raise ConnectorValidationError(f"无法访问存储桶: {info}")
            
            logger.info(f"Qiniu connector validation successful for bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Qiniu connector validation failed: {e}")
            raise
    
    # 扩展功能：文件上传和下载
    
    @handle_qiniu_exception
    def create_folder(self, folder_uuid: str = None) -> str:
        """创建文件夹（通过占位文件）"""
        if folder_uuid is None:
            folder_uuid = str(uuid.uuid4())[:self.folder_uuid_length]
        
        # 创建占位文件以确保文件夹存在
        placeholder_key = self._create_placeholder_key(folder_uuid)
        
        # 使用简单的字符串作为占位内容
        placeholder_content = f"Folder created at {datetime.now().isoformat()}"
        
        # 获取上传 token
        token = self.auth.upload_token(self.bucket_name, placeholder_key)
        
        # 上传占位文件
        ret, info = put_data(token, placeholder_key, placeholder_content.encode('utf-8'))
        
        if ret is None:
            logger.error(f"Failed to create folder placeholder: {info}")
            raise QiniuConnectorError(f"创建文件夹占位文件失败: {info}")
        
        logger.info(f"Created folder: {folder_uuid}")
        return folder_uuid
    
    @handle_qiniu_exception
    def folder_exists(self, folder_uuid: str) -> bool:
        """检查文件夹是否存在"""
        try:
            placeholder_key = self._create_placeholder_key(folder_uuid)
            ret, info = self.bucket_manager.stat(self.bucket_name, placeholder_key)
            return ret is not None
        except Exception:
            return False
    
    @handle_qiniu_exception
    def upload_file_to_folder(
        self, 
        local_file_path: str, 
        filename: str = None,
        folder_uuid: str = None
    ) -> Tuple[str, str]:
        """
        上传文件到指定或新创建的文件夹
        
        Args:
            local_file_path: 本地文件路径
            filename: 目标文件名，默认使用本地文件名
            folder_uuid: 文件夹 UUID，如果为 None 则创建新文件夹
            
        Returns:
            (folder_uuid, object_key) 元组
        """
        self._ensure_initialized()
        
        if not os.path.exists(local_file_path):
            raise QiniuUploadError(local_file_path, "本地文件不存在")
        
        # 确定文件名
        if filename is None:
            filename = os.path.basename(local_file_path)
        
        # 确定文件夹
        if folder_uuid is None:
            if self.auto_create_folder:
                folder_uuid = self.create_folder()
            else:
                raise QiniuUploadError(filename, "未指定文件夹且禁用自动创建")
        elif not self.folder_exists(folder_uuid):
            if self.auto_create_folder:
                self.create_folder(folder_uuid)
            else:
                raise QiniuUploadError(filename, f"文件夹 {folder_uuid} 不存在")
        
        # 创建对象键
        object_key = self.create_object_key(folder_uuid, filename)
        
        # 生成上传token
        token = self.auth.upload_token(self.bucket_name, object_key)
        
        # 上传文件
        ret, info = put_file(token, object_key, local_file_path)
        
        if ret is None:
            raise QiniuUploadError(filename, f"上传失败: {info}")
        
        logger.info(f"Uploaded file {filename} to folder {folder_uuid}")
        return folder_uuid, object_key
    
    @handle_qiniu_exception
    def download_file_from_folder(
        self, 
        folder_uuid: str, 
        filename: str, 
        local_path: str
    ) -> bool:
        """
        从指定文件夹下载文件
        
        Args:
            folder_uuid: 文件夹 UUID
            filename: 文件名
            local_path: 本地保存路径
            
        Returns:
            是否成功下载
        """
        self._ensure_initialized()
        
        try:
            # 创建对象键
            object_key = self.create_object_key(folder_uuid, filename)
            
            # 下载文件
            object_content = self._download_object(object_key)
            
            # 保存到本地
            with open(local_path, 'wb') as f:
                f.write(object_content)
            
            logger.info(f"Downloaded file {filename} from folder {folder_uuid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download file {filename} from folder {folder_uuid}: {e}")
            return False
    
    def upload_files_to_folder(
        self, 
        file_paths: List[str], 
        folder_uuid: str = None
    ) -> Tuple[str, List[str]]:
        """
        批量上传文件到同一文件夹
        
        Args:
            file_paths: 本地文件路径列表
            folder_uuid: 文件夹 UUID，如果为 None 则创建新文件夹
            
        Returns:
            (folder_uuid, object_keys) 元组
        """
        self._ensure_initialized()
        
        # 确定文件夹
        if folder_uuid is None and self.auto_create_folder:
            folder_uuid = self.create_folder()
        elif folder_uuid is None:
            raise QiniuUploadError("multiple files", "未指定文件夹且禁用自动创建")
        
        object_keys = []
        
        for file_path in file_paths:
            try:
                _, object_key = self.upload_file_to_folder(
                    file_path, folder_uuid=folder_uuid
                )
                object_keys.append(object_key)
            except Exception as e:
                logger.error(f"Failed to upload file {file_path}: {e}")
                continue
        
        return folder_uuid, object_keys
    
    def list_folders(self) -> List[str]:
        """列出所有文件夹"""
        self._ensure_initialized()
        
        folders = set()
        
        try:
            # 列举所有对象
            marker = None
            while True:
                ret, eof, info = self.bucket_manager.list(
                    self.bucket_name, 
                    prefix=self.prefix,
                    marker=marker,
                    limit=1000
                )
                
                if ret is None:
                    logger.error(f"Failed to list objects: {info}")
                    break
                
                # 提取文件夹前缀
                for item in ret.get("items", []):
                    key = item["key"]
                    try:
                        folder_prefix, _ = self.parse_object_key(key)
                        if folder_prefix and folder_prefix != "root":
                            folders.add(folder_prefix)
                    except Exception:
                        continue
                
                if eof:
                    break
                marker = ret.get("marker")
        
        except Exception as e:
            logger.error(f"Failed to list folders: {e}")
            return []
        
        return sorted(list(folders))
    
    def list_files_in_folder(self, folder_uuid: str) -> List[Dict[str, Any]]:
        """列出指定文件夹中的文件"""
        self._ensure_initialized()
        
        files = []
        folder_prefix = self._get_folder_prefix(folder_uuid)
        
        try:
            marker = None
            while True:
                ret, eof, info = self.bucket_manager.list(
                    self.bucket_name,
                    prefix=f"{folder_prefix}/",
                    marker=marker,
                    limit=1000
                )
                
                if ret is None:
                    logger.error(f"Failed to list files in folder {folder_uuid}: {info}")
                    break
                
                for item in ret.get("items", []):
                    key = item["key"]
                    
                    # 跳过占位文件
                    if key.endswith(self.placeholder_filename):
                        continue
                    
                    try:
                        _, filename = self.parse_object_key(key)
                        files.append({
                            "filename": filename,
                            "key": key,
                            "size": item.get("fsize", 0),
                            "last_modified": item.get("putTime", 0) / 10000000,  # 七牛云时间戳转换
                            "etag": item.get("hash", ""),
                            "mime_type": item.get("mimeType", "application/octet-stream")
                        })
                    except Exception as e:
                        logger.warning(f"Failed to parse object key {key}: {e}")
                        continue
                
                if eof:
                    break
                marker = ret.get("marker")
        
        except Exception as e:
            logger.error(f"Failed to list files in folder {folder_uuid}: {e}")
            return []
        
        return files
    
    def delete_folder(self, folder_uuid: str, force: bool = False) -> bool:
        """删除文件夹"""
        self._ensure_initialized()
        
        try:
            # 检查文件夹是否存在
            if not self.folder_exists(folder_uuid):
                logger.warning(f"Folder {folder_uuid} does not exist")
                return False
            
            # 获取文件夹中的所有文件
            files = self.list_files_in_folder(folder_uuid)
            
            if files and not force:
                logger.warning(f"Folder {folder_uuid} is not empty, use force=True to delete")
                return False
            
            # 删除所有文件
            keys_to_delete = []
            for file_info in files:
                keys_to_delete.append(file_info["key"])
            
            # 添加占位文件
            placeholder_key = self._create_placeholder_key(folder_uuid)
            keys_to_delete.append(placeholder_key)
            
            # 批量删除
            if keys_to_delete:
                from qiniu import BucketManager
                ops = [BucketManager.delete_op(self.bucket_name, key) for key in keys_to_delete]
                ret, info = self.bucket_manager.batch(ops)
                
                if ret is None:
                    logger.error(f"Failed to delete folder {folder_uuid}: {info}")
                    return False
            
            logger.info(f"Deleted folder: {folder_uuid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete folder {folder_uuid}: {e}")
            return False
    
    def get_folder_stats(self, folder_uuid: str) -> Dict[str, Any]:
        """获取文件夹统计信息"""
        self._ensure_initialized()
        
        try:
            files = self.list_files_in_folder(folder_uuid)
            
            file_count = len(files)
            total_size = sum(file_info["size"] for file_info in files)
            
            # 计算创建时间（最早的文件时间）
            created_at = ""
            if files:
                earliest_time = min(file_info["last_modified"] for file_info in files)
                created_at = datetime.fromtimestamp(earliest_time).isoformat()
            
            return {
                "file_count": file_count,
                "total_size": total_size,
                "created_at": created_at,
                "files": files
            }
            
        except Exception as e:
            logger.error(f"Failed to get folder stats for {folder_uuid}: {e}")
            return {
                "file_count": 0,
                "total_size": 0,
                "created_at": "",
                "files": []
            }