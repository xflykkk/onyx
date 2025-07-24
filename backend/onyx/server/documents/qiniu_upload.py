"""
七牛云文件上传 API

提供专门的七牛云文件上传接口，支持：
- 直接上传文件到七牛云
- 自动创建连接器和凭证
- 触发索引任务
- 文件夹管理
"""

import os
import time
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from onyx.auth.users import current_curator_or_admin_user
from onyx.background.celery.versioned_apps.client import app as client_app
from onyx.configs.constants import DocumentSource, FileOrigin, OnyxCeleryPriority, OnyxCeleryTask
from onyx.connectors.qiniu_cloud.connector import QiniuCloudConnector
from onyx.connectors.models import InputType
from onyx.db.connector import create_connector
from onyx.db.connector_credential_pair import add_credential_to_connector
from onyx.db.credentials import create_credential
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import AccessType
from onyx.db.models import User
from onyx.server.documents.models import ConnectorBase, CredentialBase, ObjectCreationIdResponse
from onyx.server.models import StatusResponse
from onyx.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

router = APIRouter(prefix="/manage/qiniu")


class QiniuUploadRequest(BaseModel):
    """七牛云上传请求"""
    bucket_name: str
    bucket_domain: str
    region: str = "cn-east-1"
    prefix: str = ""
    folder_uuid: str = None  # 可选，指定文件夹
    connector_name: str = None  # 可选，连接器名称
    auto_index: bool = True  # 是否自动触发索引
    user_id: str = None  # 新增：用户ID，用于自动关联个人Persona


class QiniuUploadResponse(BaseModel):
    """七牛云上传响应"""
    connector_id: int
    credential_id: int
    cc_pair_id: int
    folder_uuid: str
    uploaded_files: List[str]
    document_set_id: int | None = None  # 新增：DocumentSet ID
    document_set_name: str | None = None  # 新增：DocumentSet 名称
    message: str


class QiniuFolderInfo(BaseModel):
    """七牛云文件夹信息"""
    folder_uuid: str
    file_count: int
    total_size: int
    created_at: str
    files: List[Dict[str, Any]]


@router.post("/upload")
def upload_files_to_qiniu(
    files: List[UploadFile],
    request: QiniuUploadRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> QiniuUploadResponse:
    """
    上传文件到七牛云并创建连接器
    
    Args:
        files: 要上传的文件列表
        request: 上传请求参数
        user: 当前用户
        db_session: 数据库会话
        
    Returns:
        上传响应
    """
    tenant_id = get_current_tenant_id()
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # 验证文件
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="File name cannot be empty")
    
    try:
        # 创建七牛云连接器实例
        qiniu_connector = QiniuCloudConnector(
            bucket_name=request.bucket_name,
            bucket_domain=request.bucket_domain,
            region=request.region,
            prefix=request.prefix,
            folder_uuid=request.folder_uuid,
            auto_create_folder=True,
            folder_uuid_length=10,
        )
        
        # 加载凭证（从环境变量或请求参数获取）
        from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
        
        credentials = {
            "access_key": QINIU_ACCESS_KEY,
            "secret_key": QINIU_SECRET_KEY,
            "bucket_domain": request.bucket_domain,
        }
        
        qiniu_connector.load_credentials(credentials)
        
        # 确定文件夹
        folder_uuid = request.folder_uuid
        if not folder_uuid:
            folder_uuid = qiniu_connector.create_folder()
        
        # 上传文件
        uploaded_files = []
        for file in files:
            # 保存文件到临时位置
            temp_file_path = f"/tmp/{file.filename}"
            with open(temp_file_path, "wb") as temp_file:
                content = file.file.read()
                temp_file.write(content)
            
            try:
                # 上传到七牛云
                folder_uuid, object_key = qiniu_connector.upload_file_to_folder(
                    temp_file_path,
                    filename=file.filename,
                    folder_uuid=folder_uuid
                )
                uploaded_files.append(object_key)
                
                logger.info(f"Uploaded file {file.filename} to Qiniu folder {folder_uuid}")
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        
        # 创建连接器
        connector_name = request.connector_name or f"Qiniu-{folder_uuid}-{int(time.time())}"
        
        connector_base = ConnectorBase(
            name=connector_name,
            source=DocumentSource.QINIU_CLOUD,
            input_type=InputType.LOAD_STATE,
            connector_specific_config={
                "bucket_name": request.bucket_name,
                "bucket_domain": request.bucket_domain,
                "region": request.region,
                "prefix": request.prefix,
                "folder_uuid": folder_uuid,
                "auto_create_folder": True,
                "folder_uuid_length": 10,
            },
            refresh_freq=None,
            prune_freq=None,
            indexing_start=None,
        )
        
        connector_response = create_connector(
            db_session=db_session,
            connector_data=connector_base,
        )
        
        # 创建凭证
        credential_base = CredentialBase(
            credential_json=credentials,
            admin_public=True,
            source=DocumentSource.QINIU_CLOUD,
            curator_public=True,
            groups=[],
            name=f"Qiniu-Credential-{int(time.time())}",
        )
        
        credential = create_credential(
            credential_data=credential_base,
            user=user,
            db_session=db_session,
        )
        
        # 创建连接器凭证对
        cc_pair = add_credential_to_connector(
            db_session=db_session,
            user=user,
            connector_id=connector_response.id,
            credential_id=credential.id,
            cc_pair_name=f"Qiniu-CCPair-{int(time.time())}",
            access_type=AccessType.PRIVATE,
            auto_sync_options=None,
            groups=[],
        )
        
        # 创建DocumentSet（可选）
        document_set_id = None
        document_set_name = None
        
        # 构建文件夹路径用于DocumentSet命名
        folder_path = f"{request.prefix}/{folder_uuid}".strip("/")
        
        try:
            # 导入DocumentSet工具
            from onyx.server.documents.oss_document_set_utils import create_oss_document_set_for_folder
            
            doc_set = create_oss_document_set_for_folder(
                folder_path=folder_path,
                cc_pair_id=cc_pair.data,
                user=user,
                db_session=db_session,
                description=f"OSS文件夹 {folder_path} 的文档集",
            )
            
            if doc_set:
                document_set_id = doc_set.id
                document_set_name = doc_set.name
                logger.info(f"Created DocumentSet: {document_set_name} (ID: {document_set_id})")
            
        except Exception as e:
            logger.warning(f"Failed to create DocumentSet, but upload succeeded: {e}")
        
        # 触发索引
        if request.auto_index:
            # 动态导入避免循环依赖
            from onyx.server.documents.connector import trigger_indexing_for_cc_pair
            
            num_triggers = trigger_indexing_for_cc_pair(
                specified_credential_ids=[credential.id],
                connector_id=connector_response.id,
                from_beginning=True,
                tenant_id=tenant_id,
                db_session=db_session,
            )
            
            logger.info(f"Triggered indexing for {num_triggers} cc_pairs")
        
        return QiniuUploadResponse(
            connector_id=connector_response.id,
            credential_id=credential.id,
            cc_pair_id=cc_pair.data,
            folder_uuid=folder_uuid,
            uploaded_files=uploaded_files,
            document_set_id=document_set_id,
            document_set_name=document_set_name,
            message=f"Successfully uploaded {len(uploaded_files)} files to Qiniu folder {folder_uuid}",
        )
        
    except Exception as e:
        logger.error(f"Failed to upload files to Qiniu: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/folders")
def list_qiniu_folders(
    bucket_name: str,
    bucket_domain: str,
    region: str = "cn-east-1",
    prefix: str = "",
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> List[str]:
    """
    列出七牛云存储桶中的文件夹
    
    Args:
        bucket_name: 存储桶名称
        bucket_domain: 存储桶域名
        region: 区域
        prefix: 前缀
        user: 当前用户
        db_session: 数据库会话
        
    Returns:
        文件夹列表
    """
    try:
        # 创建七牛云连接器实例
        qiniu_connector = QiniuCloudConnector(
            bucket_name=bucket_name,
            bucket_domain=bucket_domain,
            region=region,
            prefix=prefix,
        )
        
        # 加载凭证
        from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
        
        credentials = {
            "access_key": QINIU_ACCESS_KEY,
            "secret_key": QINIU_SECRET_KEY,
            "bucket_domain": bucket_domain,
        }
        
        qiniu_connector.load_credentials(credentials)
        
        # 获取文件夹列表
        folders = qiniu_connector.list_folders()
        
        return folders
        
    except Exception as e:
        logger.error(f"Failed to list Qiniu folders: {e}")
        raise HTTPException(status_code=500, detail=f"List folders failed: {str(e)}")


@router.get("/folders/{folder_uuid}")
def get_qiniu_folder_info(
    folder_uuid: str,
    bucket_name: str,
    bucket_domain: str,
    region: str = "cn-east-1",
    prefix: str = "",
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> QiniuFolderInfo:
    """
    获取七牛云文件夹信息
    
    Args:
        folder_uuid: 文件夹 UUID
        bucket_name: 存储桶名称
        bucket_domain: 存储桶域名
        region: 区域
        prefix: 前缀
        user: 当前用户
        db_session: 数据库会话
        
    Returns:
        文件夹信息
    """
    try:
        # 创建七牛云连接器实例
        qiniu_connector = QiniuCloudConnector(
            bucket_name=bucket_name,
            bucket_domain=bucket_domain,
            region=region,
            prefix=prefix,
        )
        
        # 加载凭证
        from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
        
        credentials = {
            "access_key": QINIU_ACCESS_KEY,
            "secret_key": QINIU_SECRET_KEY,
            "bucket_domain": bucket_domain,
        }
        
        qiniu_connector.load_credentials(credentials)
        
        # 获取文件夹信息
        folder_stats = qiniu_connector.get_folder_stats(folder_uuid)
        files = qiniu_connector.list_files_in_folder(folder_uuid)
        
        return QiniuFolderInfo(
            folder_uuid=folder_uuid,
            file_count=folder_stats.get("file_count", 0),
            total_size=folder_stats.get("total_size", 0),
            created_at=folder_stats.get("created_at", ""),
            files=files,
        )
        
    except Exception as e:
        logger.error(f"Failed to get Qiniu folder info: {e}")
        raise HTTPException(status_code=500, detail=f"Get folder info failed: {str(e)}")


@router.delete("/folders/{folder_uuid}")
def delete_qiniu_folder(
    folder_uuid: str,
    bucket_name: str,
    bucket_domain: str,
    region: str = "cn-east-1",
    prefix: str = "",
    force: bool = False,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> StatusResponse:
    """
    删除七牛云文件夹
    
    Args:
        folder_uuid: 文件夹 UUID
        bucket_name: 存储桶名称
        bucket_domain: 存储桶域名
        region: 区域
        prefix: 前缀
        force: 是否强制删除
        user: 当前用户
        db_session: 数据库会话
        
    Returns:
        状态响应
    """
    try:
        # 创建七牛云连接器实例
        qiniu_connector = QiniuCloudConnector(
            bucket_name=bucket_name,
            bucket_domain=bucket_domain,
            region=region,
            prefix=prefix,
        )
        
        # 加载凭证
        from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
        
        credentials = {
            "access_key": QINIU_ACCESS_KEY,
            "secret_key": QINIU_SECRET_KEY,
            "bucket_domain": bucket_domain,
        }
        
        qiniu_connector.load_credentials(credentials)
        
        # 删除文件夹
        success = qiniu_connector.delete_folder(folder_uuid, force=force)
        
        if success:
            return StatusResponse(
                success=True,
                message=f"Successfully deleted folder {folder_uuid}",
            )
        else:
            return StatusResponse(
                success=False,
                message=f"Failed to delete folder {folder_uuid}",
            )
        
    except Exception as e:
        logger.error(f"Failed to delete Qiniu folder: {e}")
        raise HTTPException(status_code=500, detail=f"Delete folder failed: {str(e)}")


@router.post("/folders/{folder_uuid}/upload")
def upload_files_to_existing_folder(
    folder_uuid: str,
    files: List[UploadFile],
    bucket_name: str,
    bucket_domain: str,
    region: str = "cn-east-1",
    prefix: str = "",
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> StatusResponse:
    """
    上传文件到已存在的七牛云文件夹
    
    Args:
        folder_uuid: 文件夹 UUID
        files: 要上传的文件列表
        bucket_name: 存储桶名称
        bucket_domain: 存储桶域名
        region: 区域
        prefix: 前缀
        user: 当前用户
        db_session: 数据库会话
        
    Returns:
        状态响应
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    try:
        # 创建七牛云连接器实例
        qiniu_connector = QiniuCloudConnector(
            bucket_name=bucket_name,
            bucket_domain=bucket_domain,
            region=region,
            prefix=prefix,
        )
        
        # 加载凭证
        from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
        
        credentials = {
            "access_key": QINIU_ACCESS_KEY,
            "secret_key": QINIU_SECRET_KEY,
            "bucket_domain": bucket_domain,
        }
        
        qiniu_connector.load_credentials(credentials)
        
        # 上传文件
        uploaded_files = []
        for file in files:
            # 保存文件到临时位置
            temp_file_path = f"/tmp/{file.filename}"
            with open(temp_file_path, "wb") as temp_file:
                content = file.file.read()
                temp_file.write(content)
            
            try:
                # 上传到七牛云
                _, object_key = qiniu_connector.upload_file_to_folder(
                    temp_file_path,
                    filename=file.filename,
                    folder_uuid=folder_uuid
                )
                uploaded_files.append(object_key)
                
                logger.info(f"Uploaded file {file.filename} to Qiniu folder {folder_uuid}")
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        
        return StatusResponse(
            success=True,
            message=f"Successfully uploaded {len(uploaded_files)} files to folder {folder_uuid}",
        )
        
    except Exception as e:
        logger.error(f"Failed to upload files to existing folder: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")