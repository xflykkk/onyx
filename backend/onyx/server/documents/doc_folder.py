"""
Document folder management API

Provides endpoints for:
- Receiving upstream notifications when files are uploaded to Qiniu OSS
- Querying indexing status for all files in a specified folder
"""

import re
import time
from typing import Any, Dict
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from onyx.auth.users import current_curator_or_admin_user
from onyx.configs.constants import DocumentSource, OnyxCeleryPriority
from onyx.connectors.models import InputType
from onyx.connectors.qiniu_cloud.connector import QiniuCloudConnector
from onyx.db.connector import create_connector
from onyx.db.connector_credential_pair import add_credential_to_connector, get_connector_credential_pair
from onyx.db.credentials import create_credential
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import AccessType, ConnectorCredentialPairStatus
from onyx.db.models import User, Connector, ConnectorCredentialPair, DocumentByConnectorCredentialPair, Persona
from onyx.db.document import get_document_ids_for_connector_credential_pair
from onyx.db.user_documents import upsert_user_folder, get_user_folder_by_name
from onyx.db.document_set import insert_document_set, get_document_set_by_name
from onyx.db.persona import get_personas_for_user
from onyx.server.documents.connector import trigger_indexing_for_cc_pair
from onyx.server.documents.models import ConnectorBase, CredentialBase
from onyx.server.features.document_set.models import DocumentSetCreationRequest
from onyx.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

router = APIRouter(prefix="/doc")


def create_oss_document_set_and_associate(
    folder_path: str,
    cc_pair_id: int,
    user: User | None,
    db_session: Session,
) -> tuple[int | None, str | None, int | None, str | None]:
    """
    为OSS文件夹创建DocumentSet并尝试关联到用户的Persona
    
    Returns:
        (document_set_id, document_set_name, persona_id, persona_name)
    """
    try:
        # 1. 创建DocumentSet
        doc_set_name = f"OSS-{folder_path.replace('/', '-').strip('-')}"
        # 限制名称长度
        if len(doc_set_name) > 50:
            doc_set_name = doc_set_name[:50]
        
        # 检查是否已存在
        existing_doc_set = get_document_set_by_name(db_session, doc_set_name)
        if existing_doc_set:
            logger.info(f"DocumentSet already exists: {doc_set_name}")
            doc_set = existing_doc_set
        else:
            # 创建新DocumentSet
            doc_set_request = DocumentSetCreationRequest(
                name=doc_set_name,
                description=f"自动创建的OSS文档集：{folder_path}",
                cc_pair_ids=[cc_pair_id],
                is_public=user is None,  # 如果没有用户，设为公共
                users=[user.id] if user else [],  # 只有在有用户时才设置访问权限
                groups=[],
            )
            
            doc_set, _ = insert_document_set(
                document_set_creation_request=doc_set_request,
                user_id=user.id if user else None,
                db_session=db_session,
            )
            logger.info(f"Created DocumentSet: {doc_set_name}")
        
        # 2. 尝试关联到用户的第一个可用Persona（仅在有用户时）
        persona_id = None
        persona_name = None
        
        if user:
            user_personas = get_personas_for_user(user, db_session, get_editable=True)
            
            if user_personas:
                # 使用用户的第一个Persona
                first_persona = user_personas[0]
                
                # 检查是否已关联
                if doc_set not in first_persona.document_sets:
                    first_persona.document_sets.append(doc_set)
                    db_session.commit()
                    logger.info(f"Associated DocumentSet {doc_set_name} with Persona {first_persona.name}")
                
                persona_id = first_persona.id
                persona_name = first_persona.name
            else:
                logger.warning(f"User {user.email} has no personas available for association")
        else:
            logger.info("No user provided, skipping Persona association")
        
        return doc_set.id, doc_set_name, persona_id, persona_name
        
    except Exception as e:
        logger.error(f"Failed to create DocumentSet and associate: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return None, None, None, None


def sanitize_folder_name_for_user_folder(folder_name: str) -> str:
    """
    Convert doc_folder_name to a safe UserFolder name
    - Add prefix to avoid conflicts with existing folders
    """
    # Add prefix to identify OSS-originated folders
    return f"OSS-{folder_name}"


def find_user_folder_id_by_doc_folder_name(doc_folder_name: str, db_session: Session) -> int | None:
    """
    Find the corresponding UserFolder ID for a given doc_folder_name
    """
    safe_folder_name = sanitize_folder_name_for_user_folder(doc_folder_name)
    user_folder = get_user_folder_by_name(db_session, safe_folder_name)
    return user_folder.id if user_folder else None


class DocFilePathUploadRequest(BaseModel):
    """Document folder upload notification request"""
    user_id: UUID | None = None
    doc_folder_name: str = Field(..., description="Document folder name")
    crawl_url: str | None = Field(None, description="Source crawl URL")
    doc_folder_oss_url: str = Field(..., description="OSS folder URL")
    file_count: int = Field(..., description="Number of files in folder")
    crawl_detail: str | None = Field(None, description="Crawl detail information")

    @validator('doc_folder_name')
    def validate_folder_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Folder name cannot be empty")
        # Allow common folder name characters including backslash for Windows paths
        if not re.match(r'^[a-zA-Z0-9\-_/\\.\\\\]+$', v):
            raise ValueError("Folder name contains invalid characters")
        return v.strip()

    @validator('file_count')
    def validate_file_count(cls, v):
        if v < 0:
            raise ValueError("File count must be non-negative")
        return v

    @validator('doc_folder_oss_url')
    def validate_oss_url(cls, v):
        if not v or not v.strip():
            raise ValueError("OSS URL cannot be empty")
        # Basic URL validation
        try:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid OSS URL format")
        except Exception:
            raise ValueError("Invalid OSS URL format")
        return v.strip()


class DocFilePathUploadResponse(BaseModel):
    """Document folder upload notification response"""
    doc_folder_name: str
    crawl_url: str | None = None
    success: bool
    message: str | None = None
    connector_id: int | None = None
    cc_pair_id: int | None = None
    indexed_files_count: int | None = None
    folder_id: int | None = None  # 对应的 UserFolder ID
    document_set_id: int | None = None  # 新增：创建的DocumentSet ID
    document_set_name: str | None = None  # 新增：DocumentSet名称
    persona_id: int | None = None  # 新增：关联的Persona ID（如果成功关联）
    persona_name: str | None = None  # 新增：Persona名称


class DocFileInfoRequest(BaseModel):
    """Document folder status query request"""
    doc_folder_name: str = Field(..., description="Document folder name")
    crawl_url: str | None = Field(None, description="Source crawl URL")

    @validator('doc_folder_name')
    def validate_folder_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Folder name cannot be empty")
        # Allow common folder name characters including backslash for Windows paths
        if not re.match(r'^[a-zA-Z0-9\-_/\\.\\\\]+$', v):
            raise ValueError("Folder name contains invalid characters")
        return v.strip()


class DocFileInfoResponse(BaseModel):
    """Document folder status query response"""
    doc_folder_name: str
    folder_id: int | None = None  # 用于后续 chat 时使用的文件夹 ID
    crawl_url: str | None = None
    file_ids: dict[str, bool] = Field(..., description="File paths to indexing status mapping")
    status: str = Field(..., description="Overall status: 00=waiting, 10=processing, 60=success, 61=failed")
    desc: str = Field(..., description="Status description")
    folder_stats: dict[str, Any] | None = None


def _parse_qiniu_oss_url(oss_url: str) -> tuple[str, str, str]:
    """
    Parse Qiniu OSS URL to extract bucket info and folder prefix
    
    Args:
        oss_url: OSS URL like "https://bucket.domain.com/folder_prefix/" or
                           "https://cdn.example.com/folder_prefix/"
        
    Returns:
        (bucket_name, bucket_domain, folder_prefix)
    """
    try:
        logger.debug(f"[_parse_qiniu_oss_url] Parsing URL: {oss_url}")
        parsed = urlparse(oss_url)
        
        # Extract domain from netloc
        domain = parsed.netloc
        
        # For Qiniu, we need to use the configured bucket info from environment
        # because the URL might be a CDN domain which doesn't contain bucket info
        from onyx.configs.app_configs import QINIU_DEFAULT_BUCKET, QINIU_BUCKET_DOMAIN
        
        # Use configured values
        bucket_name = QINIU_DEFAULT_BUCKET
        bucket_domain = QINIU_BUCKET_DOMAIN
        
        # Extract folder prefix from path
        folder_prefix = parsed.path.strip('/')
        
        logger.info(f"[_parse_qiniu_oss_url] Successfully parsed - bucket: {bucket_name}, domain: {bucket_domain}, prefix: {folder_prefix}")
        
        return bucket_name, bucket_domain, folder_prefix
        
    except Exception as e:
        logger.error(f"[_parse_qiniu_oss_url] Failed to parse OSS URL {oss_url}: {e}", exc_info=True)
        raise ValueError(f"Invalid OSS URL format: {oss_url}")


def _get_or_create_qiniu_connector(
    folder_name: str,
    bucket_name: str,
    bucket_domain: str,
    folder_prefix: str,
    crawl_url: str | None,
    db_session: Session
) -> tuple[Connector, int, int]:
    """
    Get or create Qiniu connector for the specified folder
    
    Returns:
        (connector, credential_id, cc_pair_id)
    """
    logger.info(f"[_get_or_create_qiniu_connector] Starting for folder: {folder_name}")
    
    # Check if connector already exists for this folder pattern
    existing_connector = db_session.query(Connector).filter(
        Connector.name.like(f"DocFolder-{folder_name}-%")
    ).first()
    
    if existing_connector:
        logger.info(f"[_get_or_create_qiniu_connector] Using existing connector: {existing_connector.name} (id={existing_connector.id})")
        connector = existing_connector
    else:
        # Create new connector
        connector_name = f"DocFolder-{folder_name}-{int(time.time())}"
        logger.info(f"[_get_or_create_qiniu_connector] Creating new connector: {connector_name}")
        connector_base = ConnectorBase(
            name=connector_name,
            source=DocumentSource.QINIU_CLOUD,
            input_type=InputType.LOAD_STATE,
            connector_specific_config={
                "bucket_name": bucket_name,
                "bucket_domain": bucket_domain,
                "region": "cn-east-1",
                "prefix": folder_prefix,
                "folder_uuid": folder_name,
                "auto_create_folder": True,
                "folder_uuid_length": 10,
            },
            refresh_freq=None,
            prune_freq=None,
            indexing_start=None,
        )
        
        connector = create_connector(
            db_session=db_session,
            connector_data=connector_base,
        )
        logger.info(f"[_get_or_create_qiniu_connector] Created new connector: {connector_name} (id={connector.id})")
    
    # Load Qiniu credentials from app_configs
    logger.debug(f"[_get_or_create_qiniu_connector] Loading Qiniu credentials from config...")
    from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
    
    if not QINIU_ACCESS_KEY or not QINIU_SECRET_KEY:
        logger.error(f"[_get_or_create_qiniu_connector] Qiniu credentials not configured!")
        raise HTTPException(
            status_code=500,
            detail="Qiniu credentials not configured"
        )
    
    # Create new credential for this folder
    credential_name = f"DocFolder-Credential-{folder_name}-{int(time.time())}"
    logger.info(f"[_get_or_create_qiniu_connector] Creating new credential: {credential_name}")
    credential_base = CredentialBase(
        credential_json={
            "access_key": QINIU_ACCESS_KEY,
            "secret_key": QINIU_SECRET_KEY,
            "bucket_domain": bucket_domain,
        },
        admin_public=True,
        source=DocumentSource.QINIU_CLOUD,
        curator_public=True,
        groups=[],
        name=credential_name,
    )
    
    credential = create_credential(
        credential_data=credential_base,
        user=None,  # System credential
        db_session=db_session,
    )
    logger.info(f"Created new credential: {credential_name}")
    
    # Get or create connector-credential pair
    logger.info(f"[_get_or_create_qiniu_connector] Checking for existing CC pair...")
    try:
        cc_pair = get_connector_credential_pair(
            db_session=db_session,
            connector_id=connector.id,
            credential_id=credential.id,
        )
        logger.info(f"[_get_or_create_qiniu_connector] Using existing CC pair: {cc_pair.id}")
        cc_pair_id = cc_pair.id
    except Exception as e:
        logger.debug(f"[_get_or_create_qiniu_connector] No existing CC pair found: {e}")
        # Create new CC pair
        cc_pair_name = f"DocFolder-CCPair-{folder_name}-{int(time.time())}"
        logger.info(f"[_get_or_create_qiniu_connector] Creating new CC pair: {cc_pair_name}")
        cc_pair_response = add_credential_to_connector(
            db_session=db_session,
            user=None,  # System operation
            connector_id=connector.id,
            credential_id=credential.id,
            cc_pair_name=cc_pair_name,
            access_type=AccessType.PUBLIC,
            auto_sync_options=None,
            groups=[],
        )
        logger.info(f"[_get_or_create_qiniu_connector] Created new CC pair: {cc_pair_name} (id={cc_pair_response.data})")
        cc_pair_id = cc_pair_response.data
    
    logger.info(f"[_get_or_create_qiniu_connector] Completed - connector_id={connector.id}, credential_id={credential.id}, cc_pair_id={cc_pair_id}")
    return connector, credential.id, cc_pair_id


def _get_real_file_ids_mapping(
    db_session: Session,
    connector_id: int,
    credential_id: int,
    bucket_name: str,
    folder_prefix: str,
    actual_file_count: int
) -> Dict[str, bool]:
    """
    获取真实的文件ID和索引状态映射
    
    Args:
        actual_file_count: 七牛云中实际的文件数量，用于生成占位符
    
    Returns:
        Dict[str, bool]: 文件路径 -> 是否已索引的映射
    """
    try:
        # 获取所有已索引的文档ID和相关信息
        indexed_docs_stmt = select(
            DocumentByConnectorCredentialPair.id,
            DocumentByConnectorCredentialPair.has_been_indexed
        ).where(
            and_(
                DocumentByConnectorCredentialPair.connector_id == connector_id,
                DocumentByConnectorCredentialPair.credential_id == credential_id,
            )
        )
        indexed_docs = db_session.execute(indexed_docs_stmt).fetchall()
        
        # 解析文档ID获取文件路径，并构建映射
        file_status_map = {}
        
        for doc_id, is_indexed in indexed_docs:
            # 七牛云文档ID格式: QINIU_CLOUD:{bucket_name}:{object_key}
            if doc_id.startswith(f"QINIU_CLOUD:{bucket_name}:"):
                object_key = doc_id[len(f"QINIU_CLOUD:{bucket_name}:"):]
                
                # 检查是否属于指定文件夹
                if folder_prefix:
                    if not object_key.startswith(folder_prefix):
                        continue
                    # 获取相对于文件夹的路径
                    relative_path = object_key[len(folder_prefix):].lstrip("/")
                else:
                    relative_path = object_key
                
                if relative_path:  # 排除空路径
                    file_status_map[relative_path] = bool(is_indexed)
        
        # 如果数据库中的文件数量少于实际文件数量，生成占位符文件
        indexed_count = len(file_status_map)
        if indexed_count < actual_file_count:
            pending_count = actual_file_count - indexed_count
            
            # 生成待处理文件的占位符
            for i in range(pending_count):
                placeholder_name = f"文件{i+1+indexed_count}.待处理"
                file_status_map[placeholder_name] = False
        
        logger.info(f"Found {len(file_status_map)} files mapping for folder {folder_prefix} (indexed: {indexed_count}, total: {actual_file_count})")
        return file_status_map
        
    except Exception as e:
        logger.error(f"Error getting real file IDs mapping: {e}")
        # 如果出错，生成占位符文件状态
        placeholder_map = {}
        for i in range(actual_file_count):
            placeholder_map[f"文件{i+1}.未知状态"] = False
        return placeholder_map


def _get_folder_file_count_from_qiniu(
    bucket_name: str,
    bucket_domain: str,
    folder_prefix: str
) -> int:
    """
    Get actual file count from Qiniu OSS for the specified folder
    
    Returns:
        Number of files in the folder
    """
    try:
        logger.info(f"[_get_folder_file_count_from_qiniu] Starting - bucket={bucket_name}, folder_prefix={folder_prefix}")
        
        # Create QiniuCloudConnector instance
        # Don't set prefix here since folder_prefix is already the full path
        qiniu_connector = QiniuCloudConnector(
            bucket_name=bucket_name,
            bucket_domain=bucket_domain,
            region="cn-east-1",
            prefix="",  # Empty prefix since folder_prefix is already full path
        )
        
        # Load credentials
        logger.debug(f"[_get_folder_file_count_from_qiniu] Loading Qiniu credentials...")
        from onyx.configs.app_configs import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
        
        credentials = {
            "access_key": QINIU_ACCESS_KEY,
            "secret_key": QINIU_SECRET_KEY,
            "bucket_domain": bucket_domain,
        }
        
        qiniu_connector.load_credentials(credentials)
        
        # Use folder_prefix as folder_uuid to list files
        # folder_prefix is already the full path like "crawl_results/task_id"
        logger.info(f"[_get_folder_file_count_from_qiniu] Listing files in Qiniu folder: {folder_prefix}")
        files = qiniu_connector.list_files_in_folder(folder_prefix)
        
        file_count = len(files)
        logger.info(f"[_get_folder_file_count_from_qiniu] Found {file_count} files in folder")
        return file_count
        
    except Exception as e:
        logger.error(f"[_get_folder_file_count_from_qiniu] Failed to get file count from Qiniu: {e}", exc_info=True)
        return 0


def _calculate_folder_status(cc_pair: ConnectorCredentialPair, file_count: int, indexed_count: int = 0) -> tuple[str, str]:
    """
    Calculate overall folder status based on CC pair status and actual indexed count
    
    Returns:
        (status_code, description)
    """
    if not cc_pair:
        return "00", "等待处理"
    
    # Check CC pair status
    if cc_pair.status == ConnectorCredentialPairStatus.PAUSED:
        return "61", "处理失败"
    elif cc_pair.status == ConnectorCredentialPairStatus.INITIAL_INDEXING:
        # Initial indexing is in progress
        if indexed_count == 0:
            return "10", "首次索引中"
        elif indexed_count < file_count:
            return "10", f"首次索引中 ({indexed_count}/{file_count})"
        else:
            return "60", "处理成功"
    elif cc_pair.status == ConnectorCredentialPairStatus.SCHEDULED:
        # Task is scheduled but not yet started
        return "10", "等待开始索引"
    elif cc_pair.status == ConnectorCredentialPairStatus.ACTIVE:
        if file_count == 0:
            return "00", "文件夹为空"
        elif indexed_count == 0:
            if cc_pair.last_successful_index_time:
                return "10", "索引中"
            else:
                return "00", "等待处理"
        elif indexed_count < file_count:
            return "10", f"索引中 ({indexed_count}/{file_count})"
        else:
            return "60", "处理成功"
    else:
        # For any other status (SCHEDULED, etc.)
        return "00", "等待处理"


@router.post("/file/upload-path", response_model=DocFilePathUploadResponse)
async def handle_document_folder_upload(
    request: DocFilePathUploadRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> DocFilePathUploadResponse:
    """
    Handle document folder upload notification
    
    This endpoint receives notifications from upstream systems when files
    are uploaded to Qiniu OSS, then triggers indexing for all files in the folder.
    """
    try:
        logger.info(f"[UPLOAD_PATH] Step 1: API Request received - folder={request.doc_folder_name}, oss_url={request.doc_folder_oss_url}, file_count={request.file_count}")
        
        # Parse OSS URL to extract bucket and folder information
        logger.info(f"[UPLOAD_PATH] Step 2: Parsing OSS URL...")
        bucket_name, bucket_domain, folder_prefix = _parse_qiniu_oss_url(request.doc_folder_oss_url)
        logger.info(f"[UPLOAD_PATH] Step 2 Complete: bucket={bucket_name}, domain={bucket_domain}, prefix={folder_prefix}")
        
        # Get actual file count from Qiniu OSS
        logger.info(f"[UPLOAD_PATH] Step 3: Verifying file count from Qiniu OSS...")
        actual_file_count = _get_folder_file_count_from_qiniu(
            bucket_name, bucket_domain, folder_prefix
        )
        logger.info(f"[UPLOAD_PATH] Step 3 Complete: found {actual_file_count} files in Qiniu")
        
        if actual_file_count == 0:
            logger.warning(f"[UPLOAD_PATH] No files found in folder: {request.doc_folder_name}")
            return DocFilePathUploadResponse(
                doc_folder_name=request.doc_folder_name,
                crawl_url=request.crawl_url,
                success=False,
                message=f"No files found in folder: {request.doc_folder_name}",
                indexed_files_count=0,
                folder_id=None,
                document_set_id=None,
                document_set_name=None,
                persona_id=None,
                persona_name=None
            )
        
        # Get or create connector and credentials
        logger.info(f"[UPLOAD_PATH] Step 4: Getting or creating Qiniu connector...")
        connector, credential_id, cc_pair_id = _get_or_create_qiniu_connector(
            request.doc_folder_name,
            bucket_name,
            bucket_domain,
            folder_prefix,
            request.crawl_url,
            db_session
        )
        logger.info(f"[UPLOAD_PATH] Step 4 Complete: connector_id={connector.id}, credential_id={credential_id}, cc_pair_id={cc_pair_id}")
        
        # Step 4.5: Create or get corresponding UserFolder
        logger.info(f"[UPLOAD_PATH] Step 4.5: Creating/getting corresponding UserFolder...")
        safe_folder_name = sanitize_folder_name_for_user_folder(request.doc_folder_name)
        user_folder = upsert_user_folder(
            db_session=db_session,
            user_id=user.id if user else None,
            name=safe_folder_name,
            description=f"Auto-created from OSS upload notification. Original path: {request.doc_folder_name}, Source: {request.crawl_url or 'Direct upload'}"
        )
        logger.info(f"[UPLOAD_PATH] Step 4.5 Complete: user_folder_id={user_folder.id}, safe_name='{safe_folder_name}'")
        
        # Step 4.6: Create DocumentSet and try to associate with user's Persona
        logger.info(f"[UPLOAD_PATH] Step 4.6: Creating DocumentSet and associating with Persona...")
        doc_set_id, doc_set_name, persona_id, persona_name = create_oss_document_set_and_associate(
            folder_path=request.doc_folder_name,
            cc_pair_id=cc_pair_id,
            user=user,
            db_session=db_session,
        )
        logger.info(f"[UPLOAD_PATH] Step 4.6 Complete: doc_set_id={doc_set_id}, persona_id={persona_id}")
        
        # Trigger indexing pipeline
        tenant_id = get_current_tenant_id()
        logger.info(f"[UPLOAD_PATH] Step 5: Triggering indexing for CC pair...")
        num_triggered = trigger_indexing_for_cc_pair(
            specified_credential_ids=[credential_id],
            connector_id=connector.id,
            from_beginning=True,
            tenant_id=tenant_id,
            db_session=db_session,
        )
        logger.info(f"[UPLOAD_PATH] Step 5 Complete: triggered {num_triggered} indexing tasks")
        
        logger.info(f"Triggered indexing for {num_triggered} cc_pairs in folder: {request.doc_folder_name}")
        
        return DocFilePathUploadResponse(
            doc_folder_name=request.doc_folder_name,
            crawl_url=request.crawl_url,
            success=True,
            message=f"Successfully triggered indexing for {actual_file_count} files",
            connector_id=connector.id,
            cc_pair_id=cc_pair_id,
            indexed_files_count=actual_file_count,
            folder_id=user_folder.id,
            document_set_id=doc_set_id,
            document_set_name=doc_set_name,
            persona_id=persona_id,
            persona_name=persona_name
        )
        
    except Exception as e:
        logger.error(f"[UPLOAD_PATH] ERROR: Failed to handle folder upload notification: {e}", exc_info=True)
        return DocFilePathUploadResponse(
            doc_folder_name=request.doc_folder_name,
            crawl_url=request.crawl_url,
            success=False,
            message=f"Failed to process folder upload: {str(e)}",
            folder_id=None,
            document_set_id=None,
            document_set_name=None,
            persona_id=None,
            persona_name=None
        )


@router.get("/file/status", response_model=DocFileInfoResponse)
async def query_document_folder_status(
    doc_folder_name: str = Query(..., description="Document folder name"),
    crawl_url: str | None = Query(None, description="Source crawl URL"),
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> DocFileInfoResponse:
    """
    Query indexing status for all files in a specified folder
    
    Returns the indexing status of all files in the folder and overall folder status.
    """
    try:
        logger.info(f"[QUERY_STATUS] Starting - folder: {doc_folder_name}")
        
        # Find connector by name pattern
        # Support both full path and just task ID
        if "/" in doc_folder_name:
            # Full path provided (e.g., "crawl_results/task_xxx")
            connector_name_pattern = f"DocFolder-{doc_folder_name}-"
        else:
            # Just task ID provided (e.g., "task_xxx")
            connector_name_pattern = f"DocFolder-%{doc_folder_name}-%"
        
        logger.debug(f"[QUERY_STATUS] Searching with pattern: {connector_name_pattern}")
        
        connector = db_session.query(Connector).filter(
            Connector.name.like(f"{connector_name_pattern}%")
        ).order_by(Connector.id.desc()).first()  # Get the most recent one if multiple exist
        
        if not connector:
            logger.warning(f"[QUERY_STATUS] No connector found for folder: {doc_folder_name} with pattern: {connector_name_pattern}")
            return DocFileInfoResponse(
                doc_folder_name=doc_folder_name,
                folder_id=find_user_folder_id_by_doc_folder_name(doc_folder_name, db_session),
                crawl_url=crawl_url,
                file_ids={},
                status="00",
                desc="文件夹未找到或未开始处理",
                folder_stats={
                    "connector_found": False,
                    "file_count": 0
                }
            )
        
        logger.info(f"[QUERY_STATUS] Found connector: {connector.name} (id={connector.id})")
        
        # Get connector-credential pair
        cc_pair = db_session.query(ConnectorCredentialPair).filter(
            ConnectorCredentialPair.connector_id == connector.id
        ).first()
        
        if not cc_pair:
            logger.warning(f"[QUERY_STATUS] No CC pair found for connector: {connector.name}")
            return DocFileInfoResponse(
                doc_folder_name=doc_folder_name,
                folder_id=find_user_folder_id_by_doc_folder_name(doc_folder_name, db_session),
                crawl_url=crawl_url,
                file_ids={},
                status="00",
                desc="连接器配置未找到",
                folder_stats={
                    "connector_found": True,
                    "cc_pair_found": False,
                    "file_count": 0
                }
            )
        
        # Get folder configuration from connector
        config = connector.connector_specific_config
        bucket_name = config.get("bucket_name", "")
        bucket_domain = config.get("bucket_domain", "")
        folder_prefix = config.get("prefix", "")
        
        # Get actual file count from Qiniu OSS
        actual_file_count = _get_folder_file_count_from_qiniu(
            bucket_name, bucket_domain, folder_prefix
        )
        
        # Get real file IDs mapping from database
        file_ids = _get_real_file_ids_mapping(
            db_session=db_session,
            connector_id=connector.id,
            credential_id=cc_pair.credential_id,
            bucket_name=bucket_name,
            folder_prefix=folder_prefix,
            actual_file_count=actual_file_count
        )
        
        indexed_count = sum(1 for is_indexed in file_ids.values() if is_indexed)
        
        logger.info(f"[QUERY_STATUS] Debug - file_count={actual_file_count}, indexed_count={indexed_count}, cc_pair_status={cc_pair.status}")
        
        # Calculate folder status based on actual indexed count
        status_code, status_desc = _calculate_folder_status(cc_pair, actual_file_count, indexed_count)
        
        logger.info(f"[QUERY_STATUS] Status calculation result: {status_code} - {status_desc}")
        
        folder_stats = {
            "connector_found": True,
            "cc_pair_found": True,
            "file_count": actual_file_count,
            "indexed_document_count": indexed_count if actual_file_count > 0 else 0,
            "indexing_progress": f"{indexed_count}/{actual_file_count}" if actual_file_count > 0 else "0/0",
            "connector_id": connector.id,
            "cc_pair_id": cc_pair.id,
            "last_successful_index_time": cc_pair.last_successful_index_time.isoformat() if cc_pair.last_successful_index_time else None,
            "status": cc_pair.status.value,
            "bucket_name": bucket_name,
            "folder_prefix": folder_prefix
        }
        
        # 详细打印文件处理状态
        file_status_summary = f"总文件数: {actual_file_count}, 已索引: {indexed_count}, 进度: {indexed_count}/{actual_file_count}"
        if file_ids:
            indexed_files = [file_path for file_path, is_indexed in file_ids.items() if is_indexed]
            pending_files = [file_path for file_path, is_indexed in file_ids.items() if not is_indexed]
            
            # 限制显示的文件数量，避免日志过长
            max_files_to_show = 5
            if len(indexed_files) > max_files_to_show:
                indexed_files_display = indexed_files[:max_files_to_show] + [f"...等{len(indexed_files) - max_files_to_show}个文件"]
            else:
                indexed_files_display = indexed_files
            
            if len(pending_files) > max_files_to_show:
                pending_files_display = pending_files[:max_files_to_show] + [f"...等{len(pending_files) - max_files_to_show}个文件"]
            else:
                pending_files_display = pending_files
            
            file_status_summary += f", 已完成文件: {indexed_files_display}, 待处理文件: {pending_files_display}"
        
        logger.info(f"Folder status for {doc_folder_name}: {status_code} - {status_desc}")
        logger.info(f"File processing details: {file_status_summary}")
        logger.info(f"Connector details: ID={connector.id}, CC_Pair_ID={cc_pair.id}, Status={cc_pair.status.value}")
        logger.info(f"Last successful index time: {cc_pair.last_successful_index_time}")
        logger.info(f"Real file mapping: Found {len(file_ids)} files in database")
        
        return DocFileInfoResponse(
            doc_folder_name=doc_folder_name,
            folder_id=find_user_folder_id_by_doc_folder_name(doc_folder_name, db_session),
            crawl_url=crawl_url,
            file_ids=file_ids,
            status=status_code,
            desc=status_desc,
            folder_stats=folder_stats
        )
        
    except Exception as e:
        logger.error(f"Failed to query folder status: {e}")
        return DocFileInfoResponse(
            doc_folder_name=doc_folder_name,
            folder_id=find_user_folder_id_by_doc_folder_name(doc_folder_name, db_session),
            crawl_url=crawl_url,
            file_ids={},
            status="61",
            desc=f"查询状态失败: {str(e)}",
            folder_stats={
                "error": str(e)
            }
        )