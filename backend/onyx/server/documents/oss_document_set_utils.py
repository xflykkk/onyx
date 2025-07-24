"""
OSS DocumentSet 管理工具

为OSS连接器提供简化的DocumentSet管理功能，遵循Onyx标准架构
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from onyx.db.document_set import insert_document_set, get_document_set_by_name
from onyx.db.models import User, DocumentSetDBModel
from onyx.server.documents.models import DocumentSetCreationRequest
from onyx.utils.logger import setup_logger

logger = setup_logger()


def create_oss_document_set_for_folder(
    folder_path: str,
    cc_pair_id: int,
    user: User,
    db_session: Session,
    description: Optional[str] = None,
) -> Optional[DocumentSetDBModel]:
    """
    为OSS文件夹创建DocumentSet（如果不存在）
    
    Args:
        folder_path: OSS文件夹路径
        cc_pair_id: 连接器凭证对ID
        user: 当前用户
        db_session: 数据库会话
        description: 可选描述
        
    Returns:
        DocumentSet数据库模型，如果创建失败返回None
    """
    # 生成标准化的DocumentSet名称
    doc_set_name = generate_oss_document_set_name(folder_path)
    
    # 检查是否已存在
    existing_doc_set = get_document_set_by_name(db_session, doc_set_name)
    if existing_doc_set:
        logger.info(f"DocumentSet already exists: {doc_set_name}")
        return existing_doc_set
    
    # 生成描述
    if not description:
        description = f"自动创建的OSS文档集：{folder_path}"
    
    # 创建DocumentSet请求
    doc_set_request = DocumentSetCreationRequest(
        name=doc_set_name,
        description=description,
        cc_pair_ids=[cc_pair_id],
        is_public=True,  # 设为公开，方便管理员后续管理
        users=[],  # 空用户列表，使用公开访问
        groups=[],
    )
    
    try:
        # 创建DocumentSet
        doc_set, _ = insert_document_set(
            document_set_creation_request=doc_set_request,
            user_id=user.id,
            db_session=db_session,
        )
        
        logger.info(f"Created DocumentSet: {doc_set_name} (ID: {doc_set.id})")
        return doc_set
        
    except Exception as e:
        logger.error(f"Failed to create DocumentSet for {folder_path}: {e}")
        return None


def generate_oss_document_set_name(folder_path: str) -> str:
    """
    生成标准化的OSS DocumentSet名称
    
    Args:
        folder_path: OSS文件夹路径
        
    Returns:
        标准化的DocumentSet名称
    """
    # 清理文件夹路径，移除特殊字符
    clean_path = folder_path.replace("/", "-").replace("\\", "-").strip("-")
    # 限制长度，避免名称过长
    if len(clean_path) > 50:
        clean_path = clean_path[:50]
    return f"OSS-{clean_path}"


def get_oss_document_set_info(
    folder_path: str,
    db_session: Session,
) -> Optional[tuple[int, str]]:
    """
    获取OSS文件夹对应的DocumentSet信息
    
    Args:
        folder_path: OSS文件夹路径
        db_session: 数据库会话
        
    Returns:
        (document_set_id, document_set_name) 元组，如果不存在则返回None
    """
    doc_set_name = generate_oss_document_set_name(folder_path)
    doc_set = get_document_set_by_name(db_session, doc_set_name)
    
    if doc_set:
        return doc_set.id, doc_set.name
    return None