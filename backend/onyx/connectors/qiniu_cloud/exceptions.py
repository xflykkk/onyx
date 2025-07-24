"""
七牛云存储连接器异常处理模块

提供七牛云存储操作的异常类型定义和统一错误处理机制
"""

import functools
from typing import Any, Callable, TypeVar

from onyx.utils.logger import setup_logger

logger = setup_logger()

F = TypeVar("F", bound=Callable[..., Any])


class QiniuConnectorError(Exception):
    """七牛云连接器基础异常"""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error
        self.message = message


class QiniuCredentialError(QiniuConnectorError):
    """七牛云凭证相关异常"""
    
    def __init__(self, message: str = "七牛云凭证配置错误", original_error: Exception = None):
        super().__init__(message, original_error)


class QiniuBucketError(QiniuConnectorError):
    """七牛云存储桶相关异常"""
    
    def __init__(self, bucket_name: str, message: str = None, original_error: Exception = None):
        self.bucket_name = bucket_name
        full_message = f"存储桶 '{bucket_name}' 操作失败"
        if message:
            full_message += f": {message}"
        super().__init__(full_message, original_error)


class QiniuUploadError(QiniuConnectorError):
    """七牛云上传异常"""
    
    def __init__(self, filename: str, message: str = None, original_error: Exception = None):
        self.filename = filename
        full_message = f"文件 '{filename}' 上传失败"
        if message:
            full_message += f": {message}"
        super().__init__(full_message, original_error)


class QiniuDownloadError(QiniuConnectorError):
    """七牛云下载异常"""
    
    def __init__(self, filename: str, message: str = None, original_error: Exception = None):
        self.filename = filename
        full_message = f"文件 '{filename}' 下载失败"
        if message:
            full_message += f": {message}"
        super().__init__(full_message, original_error)


class QiniuFolderError(QiniuConnectorError):
    """七牛云文件夹操作异常"""
    
    def __init__(self, folder_uuid: str, message: str = None, original_error: Exception = None):
        self.folder_uuid = folder_uuid
        full_message = f"文件夹 '{folder_uuid}' 操作失败"
        if message:
            full_message += f": {message}"
        super().__init__(full_message, original_error)


def handle_qiniu_exception(func: F) -> F:
    """
    七牛云异常处理装饰器
    
    统一处理七牛云 SDK 异常，转换为自定义异常类型
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except QiniuConnectorError:
            # 自定义异常直接抛出
            raise
        except Exception as e:
            # 其他异常转换为通用连接器异常
            logger.error(f"七牛云操作异常 in {func.__name__}: {str(e)}")
            
            # 根据异常类型和消息判断具体的错误类型
            error_msg = str(e).lower()
            
            if "auth" in error_msg or "credential" in error_msg or "access" in error_msg:
                raise QiniuCredentialError(f"凭证验证失败: {str(e)}", e)
            elif "bucket" in error_msg:
                raise QiniuBucketError("unknown", f"存储桶操作失败: {str(e)}", e)
            elif "upload" in error_msg or "put" in error_msg:
                raise QiniuUploadError("unknown", f"上传失败: {str(e)}", e)
            elif "download" in error_msg or "get" in error_msg:
                raise QiniuDownloadError("unknown", f"下载失败: {str(e)}", e)
            else:
                raise QiniuConnectorError(f"未知错误: {str(e)}", e)
    
    return wrapper