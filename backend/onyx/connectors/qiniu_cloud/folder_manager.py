"""
七牛云存储文件夹管理器

提供七牛云存储的文件夹结构管理功能，包括：
- 文件夹创建和删除
- 文件组织和路径管理
- 文件夹统计信息
- 批量操作支持
"""

import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from qiniu import Auth, BucketManager
from qiniu.storage import BucketManager as StorageBucketManager

from onyx.connectors.qiniu_cloud.exceptions import (
    QiniuFolderError,
    handle_qiniu_exception,
)
from onyx.utils.logger import setup_logger

logger = setup_logger()


class QiniuFolderManager:
    """七牛云文件夹管理器"""
    
    def __init__(self, auth: Auth, bucket_name: str, prefix: str = ""):
        """
        初始化文件夹管理器
        
        Args:
            auth: 七牛云认证对象
            bucket_name: 存储桶名称
            prefix: 对象键前缀
        """
        self.auth = auth
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip("/")
        self.bucket_manager = BucketManager(auth)
        
        # 文件夹分隔符
        self.folder_separator = "/"
        
        # 占位文件名
        self.placeholder_filename = ".folder_placeholder"
    
    def _get_folder_prefix(self, folder_uuid: str) -> str:
        """
        获取文件夹前缀
        
        Args:
            folder_uuid: 文件夹 UUID
            
        Returns:
            文件夹前缀
        """
        if self.prefix:
            return f"{self.prefix}/{folder_uuid}"
        return folder_uuid
    
    def _create_placeholder_key(self, folder_uuid: str) -> str:
        """
        创建占位文件键
        
        Args:
            folder_uuid: 文件夹 UUID
            
        Returns:
            占位文件键
        """
        folder_prefix = self._get_folder_prefix(folder_uuid)
        return f"{folder_prefix}/{self.placeholder_filename}"
    
    @handle_qiniu_exception
    def create_folder(self, folder_uuid: str = None, uuid_length: int = 10) -> str:
        """
        创建文件夹
        
        Args:
            folder_uuid: 文件夹 UUID，如果为 None 则自动生成
            uuid_length: UUID 长度
            
        Returns:
            创建的文件夹 UUID
        """
        if folder_uuid is None:
            folder_uuid = str(uuid.uuid4())[:uuid_length]
        
        # 创建占位文件以确保文件夹存在
        placeholder_key = self._create_placeholder_key(folder_uuid)
        
        # 使用简单的字符串作为占位内容
        placeholder_content = f"Folder created at {datetime.now().isoformat()}"
        
        # 获取上传 token
        token = self.auth.upload_token(self.bucket_name, placeholder_key)
        
        # 上传占位文件
        from qiniu import put_data
        ret, info = put_data(token, placeholder_key, placeholder_content.encode('utf-8'))
        
        if ret is None:
            logger.error(f"Failed to create folder placeholder: {info}")
            raise QiniuFolderError(folder_uuid, f"创建文件夹占位文件失败: {info}")
        
        logger.info(f"Created folder: {folder_uuid}")
        return folder_uuid
    
    @handle_qiniu_exception
    def folder_exists(self, folder_uuid: str) -> bool:
        """
        检查文件夹是否存在
        
        Args:
            folder_uuid: 文件夹 UUID
            
        Returns:
            是否存在
        """
        try:
            placeholder_key = self._create_placeholder_key(folder_uuid)
            ret, info = self.bucket_manager.stat(self.bucket_name, placeholder_key)
            return ret is not None
        except Exception:
            return False
    
    @handle_qiniu_exception
    def create_object_key(self, folder_uuid: str, filename: str) -> str:
        """
        创建对象键
        
        Args:
            folder_uuid: 文件夹 UUID
            filename: 文件名
            
        Returns:
            对象键
        """
        folder_prefix = self._get_folder_prefix(folder_uuid)
        return f"{folder_prefix}/{filename}"
    
    @handle_qiniu_exception
    def parse_object_key(self, object_key: str) -> Tuple[str, str]:
        """
        解析对象键，提取文件夹 UUID 和文件名
        
        Args:
            object_key: 对象键
            
        Returns:
            (folder_uuid, filename) 元组
        """
        # 移除前缀
        if self.prefix and object_key.startswith(f"{self.prefix}/"):
            object_key = object_key[len(self.prefix) + 1:]
        
        # 分离文件夹和文件名
        parts = object_key.split("/")
        if len(parts) < 2:
            raise QiniuFolderError("unknown", f"无效的对象键格式: {object_key}")
        
        folder_uuid = parts[0]
        filename = "/".join(parts[1:])
        
        return folder_uuid, filename
    
    @handle_qiniu_exception
    def list_folders(self) -> List[str]:
        """
        列出所有文件夹
        
        Returns:
            文件夹 UUID 列表
        """
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
                
                # 提取文件夹 UUID
                for item in ret.get("items", []):
                    key = item["key"]
                    try:
                        folder_uuid, _ = self.parse_object_key(key)
                        folders.add(folder_uuid)
                    except Exception:
                        continue
                
                if eof:
                    break
                marker = ret.get("marker")
        
        except Exception as e:
            logger.error(f"Failed to list folders: {e}")
            return []
        
        return sorted(list(folders))
    
    @handle_qiniu_exception
    def list_files_in_folder(self, folder_uuid: str) -> List[Dict[str, Any]]:
        """
        列出文件夹中的文件
        
        Args:
            folder_uuid: 文件夹 UUID
            
        Returns:
            文件信息列表
        """
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
    
    @handle_qiniu_exception
    def delete_folder(self, folder_uuid: str, force: bool = False) -> bool:
        """
        删除文件夹
        
        Args:
            folder_uuid: 文件夹 UUID
            force: 是否强制删除（即使包含文件）
            
        Returns:
            是否成功删除
        """
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
    
    @handle_qiniu_exception
    def get_folder_stats(self, folder_uuid: str) -> Dict[str, Any]:
        """
        获取文件夹统计信息
        
        Args:
            folder_uuid: 文件夹 UUID
            
        Returns:
            统计信息字典
        """
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