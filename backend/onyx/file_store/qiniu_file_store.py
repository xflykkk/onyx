"""
七牛云文件存储后端

为 Onyx 文件存储系统提供七牛云支持，用于替代 S3 作为文件存储后端。
"""

import tempfile
import uuid
from abc import ABC
from io import BytesIO
from typing import Any, Dict, IO, Optional

from qiniu import Auth, put_data, BucketManager
import puremagic
import requests
from sqlalchemy.orm import Session

from onyx.configs.constants import FileOrigin
from onyx.db.file_record import delete_filerecord_by_file_id
from onyx.db.file_record import get_filerecord_by_file_id
from onyx.db.file_record import get_filerecord_by_file_id_optional
from onyx.db.file_record import upsert_filerecord
from onyx.db.models import FileRecord as FileStoreModel
from onyx.file_store.file_store import FileStore
from onyx.utils.file import FileWithMimeType
from onyx.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


class QiniuFileStore(FileStore):
    """七牛云文件存储后端"""

    def __init__(
        self,
        db_session: Session,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        bucket_domain: str,
        region: str = "cn-east-1",
        prefix: str = "onyx-files",
    ) -> None:
        self.db_session = db_session
        self._auth: Optional[Auth] = None
        self._bucket_manager: Optional[BucketManager] = None
        self._bucket_name = bucket_name
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket_domain = bucket_domain.rstrip("/")
        self._region = region
        self._prefix = prefix

    def _get_auth(self) -> Auth:
        """获取七牛云认证对象"""
        if self._auth is None:
            try:
                self._auth = Auth(self._access_key, self._secret_key)
            except Exception as e:
                logger.error(f"Failed to initialize Qiniu auth: {e}")
                raise RuntimeError(f"Failed to initialize Qiniu auth: {e}")
        return self._auth

    def _get_bucket_manager(self) -> BucketManager:
        """获取七牛云存储桶管理器"""
        if self._bucket_manager is None:
            auth = self._get_auth()
            self._bucket_manager = BucketManager(auth)
        return self._bucket_manager

    def _get_bucket_name(self) -> str:
        """获取存储桶名称"""
        if not self._bucket_name:
            raise RuntimeError("Qiniu bucket name is required for Qiniu file store")
        return self._bucket_name

    def _get_qiniu_key(self, file_id: str) -> str:
        """生成七牛云对象键"""
        tenant_id = get_current_tenant_id()
        
        # 类似 S3 的键结构
        if tenant_id:
            qiniu_key = f"{self._prefix}/{tenant_id}/{file_id}"
        else:
            qiniu_key = f"{self._prefix}/{file_id}"
        
        # 限制键长度
        if len(qiniu_key) > 1024:
            logger.info(f"File ID was too long and was truncated: {file_id}")
            # 使用 hash 缩短键长度
            import hashlib
            hash_part = hashlib.md5(file_id.encode()).hexdigest()
            if tenant_id:
                qiniu_key = f"{self._prefix}/{tenant_id}/{hash_part}"
            else:
                qiniu_key = f"{self._prefix}/{hash_part}"
        
        return qiniu_key

    def initialize(self) -> None:
        """初始化七牛云文件存储"""
        bucket_manager = self._get_bucket_manager()
        bucket_name = self._get_bucket_name()
        
        # 检查存储桶是否存在（通过列举对象测试）
        try:
            ret, eof, info = bucket_manager.list(bucket_name, limit=1)
            if ret is None and "no such bucket" in str(info).lower():
                # 七牛云不支持通过 API 创建存储桶，需要在控制台创建
                logger.error(f"Qiniu bucket '{bucket_name}' does not exist. Please create it in Qiniu console.")
                raise RuntimeError(f"Qiniu bucket '{bucket_name}' does not exist. Please create it in Qiniu console.")
            logger.info(f"Qiniu bucket '{bucket_name}' is accessible")
        except Exception as e:
            logger.error(f"Failed to check Qiniu bucket '{bucket_name}': {e}")
            raise RuntimeError(f"Failed to check Qiniu bucket '{bucket_name}': {e}")

    def has_file(
        self,
        file_id: str,
        file_origin: FileOrigin,
        file_type: str,
    ) -> bool:
        """检查文件是否存在"""
        file_record = get_filerecord_by_file_id_optional(
            file_id=file_id, db_session=self.db_session
        )
        return (
            file_record is not None
            and file_record.file_origin == file_origin
            and file_record.file_type == file_type
        )

    def save_file(
        self,
        content: IO,
        display_name: str | None,
        file_origin: FileOrigin,
        file_type: str,
        file_metadata: Dict[str, Any] | None = None,
        file_id: str | None = None,
    ) -> str:
        """保存文件到七牛云"""
        if file_id is None:
            file_id = str(uuid.uuid4())

        auth = self._get_auth()
        bucket_name = self._get_bucket_name()
        qiniu_key = self._get_qiniu_key(file_id)

        # 读取文件内容
        if hasattr(content, "read"):
            file_content = content.read()
            if hasattr(content, "seek"):
                content.seek(0)
        else:
            file_content = content

        try:
            # 获取上传 token
            token = auth.upload_token(bucket_name, qiniu_key)
            
            # 上传到七牛云
            ret, info = put_data(token, qiniu_key, file_content)
            
            if ret is None:
                logger.error(f"Failed to upload file to Qiniu: {info}")
                raise RuntimeError(f"Failed to upload file to Qiniu: {info}")
            
            # 保存元数据到数据库
            upsert_filerecord(
                file_id=file_id,
                display_name=display_name or file_id,
                file_origin=file_origin,
                file_type=file_type,
                bucket_name=bucket_name,
                object_key=qiniu_key,
                db_session=self.db_session,
                file_metadata=file_metadata,
            )
            self.db_session.commit()
            
            logger.info(f"Successfully saved file {file_id} to Qiniu")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to save file {file_id} to Qiniu: {e}")
            self.db_session.rollback()
            raise

    def read_file(
        self, file_id: str, mode: str | None = None, use_tempfile: bool = False
    ) -> IO[bytes]:
        """从七牛云读取文件"""
        file_record = get_filerecord_by_file_id(
            file_id=file_id, db_session=self.db_session
        )

        auth = self._get_auth()
        try:
            # 生成下载链接
            download_url = f"http://{self._bucket_domain}/{file_record.object_key}"
            
            # 生成私有下载链接（1小时有效）
            private_url = auth.private_download_url(download_url, expires=3600)
            
            # 下载文件
            response = requests.get(private_url, timeout=30)
            response.raise_for_status()
            file_content = response.content
            
            if use_tempfile:
                # 使用临时文件
                temp_file = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
                temp_file.write(file_content)
                temp_file.seek(0)
                return temp_file
            else:
                return BytesIO(file_content)
                
        except Exception as e:
            logger.error(f"Failed to read file {file_id} from Qiniu: {e}")
            raise

    def read_file_record(self, file_id: str) -> FileStoreModel:
        """读取文件记录"""
        file_record = get_filerecord_by_file_id(
            file_id=file_id, db_session=self.db_session
        )
        return file_record

    def delete_file(self, file_id: str) -> None:
        """删除文件"""
        try:
            file_record = get_filerecord_by_file_id(
                file_id=file_id, db_session=self.db_session
            )

            # 从七牛云删除文件
            bucket_manager = self._get_bucket_manager()
            ret, info = bucket_manager.delete(
                file_record.bucket_name, file_record.object_key
            )

            if ret is None and "no such file or directory" not in str(info).lower():
                logger.error(f"Failed to delete file from Qiniu: {info}")
                raise RuntimeError(f"Failed to delete file from Qiniu: {info}")

            # 从数据库删除元数据
            delete_filerecord_by_file_id(file_id=file_id, db_session=self.db_session)

            self.db_session.commit()
            logger.info(f"Successfully deleted file {file_id} from Qiniu")

        except Exception as e:
            logger.error(f"Failed to delete file {file_id} from Qiniu: {e}")
            self.db_session.rollback()
            raise

    def get_file_with_mime_type(self, filename: str) -> FileWithMimeType | None:
        """获取文件及其 MIME 类型"""
        mime_type: str = "application/octet-stream"
        try:
            file_io = self.read_file(filename, mode="b")
            file_content = file_io.read()
            matches = puremagic.magic_string(file_content)
            if matches:
                mime_type = matches[0].mime_type
            return FileWithMimeType(data=file_content, mime_type=mime_type)
        except Exception:
            return None


def get_qiniu_file_store(db_session: Session) -> QiniuFileStore:
    """
    返回七牛云文件存储实现
    """
    from onyx.configs.app_configs import (
        QINIU_ACCESS_KEY,
        QINIU_SECRET_KEY,
        QINIU_DEFAULT_BUCKET,
        QINIU_BUCKET_DOMAIN,
        QINIU_REGION,
    )
    
    # 检查必需的配置
    if not QINIU_DEFAULT_BUCKET:
        raise RuntimeError(
            "QINIU_DEFAULT_BUCKET configuration is required for Qiniu file store"
        )
    
    if not QINIU_ACCESS_KEY or not QINIU_SECRET_KEY:
        raise RuntimeError(
            "QINIU_ACCESS_KEY and QINIU_SECRET_KEY configuration is required for Qiniu file store"
        )
    
    if not QINIU_BUCKET_DOMAIN:
        raise RuntimeError(
            "QINIU_BUCKET_DOMAIN configuration is required for Qiniu file store"
        )

    return QiniuFileStore(
        db_session=db_session,
        bucket_name=QINIU_DEFAULT_BUCKET,
        access_key=QINIU_ACCESS_KEY,
        secret_key=QINIU_SECRET_KEY,
        bucket_domain=QINIU_BUCKET_DOMAIN,
        region=QINIU_REGION,
        prefix="onyx-files",
    )