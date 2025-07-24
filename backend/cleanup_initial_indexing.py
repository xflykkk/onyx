#!/usr/bin/env python3
"""
安全清理历史 INITIAL_INDEXING CC Pairs 脚本

清理逻辑:
1. 只清理 2 天前创建的 INITIAL_INDEXING CC Pairs  
2. 保留最近 2 天的数据避免误删正在处理的任务
3. 使用现有的 connector_deletion 框架确保数据完整性
"""

import time
from datetime import datetime, timedelta, timezone

from onyx.background.celery.tasks.connector_deletion.tasks import (
    connector_deletion_task,
)
from onyx.db.connector_credential_pair import get_connector_credential_pair_from_id
from onyx.db.engine import get_session_with_current_tenant
from onyx.db.enums import ConnectorCredentialPairStatus
from onyx.db.models import ConnectorCredentialPair, Connector
from onyx.utils.logger import setup_logger
from sqlalchemy import and_, func, select

logger = setup_logger()

def get_old_initial_indexing_cc_pairs(days_threshold: int = 2) -> list[int]:
    """获取超过指定天数的 INITIAL_INDEXING CC Pairs"""
    with get_session_with_current_tenant() as db_session:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        
        stmt = (
            select(ConnectorCredentialPair.id)
            .join(Connector, ConnectorCredentialPair.connector_id == Connector.id)
            .where(
                and_(
                    ConnectorCredentialPair.status == ConnectorCredentialPairStatus.INITIAL_INDEXING,
                    Connector.time_created < cutoff_time
                )
            )
        )
        
        result = db_session.execute(stmt)
        cc_pair_ids = [row[0] for row in result.fetchall()]
        
        logger.info(f"Found {len(cc_pair_ids)} INITIAL_INDEXING CC pairs older than {days_threshold} days")
        return cc_pair_ids

def get_cleanup_statistics(cc_pair_ids: list[int]) -> dict:
    """获取清理统计信息"""
    if not cc_pair_ids:
        return {}
        
    with get_session_with_current_tenant() as db_session:
        # 统计相关数据量
        from onyx.db.models import IndexAttempt, UserFile
        from onyx.db.document import DocumentByConnectorCredentialPair
        
        stats = {}
        
        # Index attempts
        index_attempts = db_session.execute(
            select(func.count(IndexAttempt.id))
            .where(IndexAttempt.connector_credential_pair_id.in_(cc_pair_ids))
        ).scalar()
        stats['index_attempts'] = index_attempts
        
        # User files  
        user_files = db_session.execute(
            select(func.count(UserFile.id))
            .where(UserFile.cc_pair_id.in_(cc_pair_ids))
        ).scalar()
        stats['user_files'] = user_files
        
        # Documents (approximate)
        documents = db_session.execute(
            select(func.count())
            .select_from(DocumentByConnectorCredentialPair)
            .join(ConnectorCredentialPair, 
                  and_(
                      DocumentByConnectorCredentialPair.connector_id == ConnectorCredentialPair.connector_id,
                      DocumentByConnectorCredentialPair.credential_id == ConnectorCredentialPair.credential_id
                  ))
            .where(ConnectorCredentialPair.id.in_(cc_pair_ids))
        ).scalar()
        stats['documents'] = documents
        
        return stats

def safe_cleanup_initial_indexing(days_threshold: int = 2, dry_run: bool = True):
    """安全清理历史 INITIAL_INDEXING CC Pairs"""
    
    logger.info(f"Starting {'DRY RUN' if dry_run else 'ACTUAL'} cleanup of INITIAL_INDEXING CC pairs older than {days_threshold} days")
    
    # 获取需要清理的 CC Pairs
    cc_pair_ids = get_old_initial_indexing_cc_pairs(days_threshold)
    
    if not cc_pair_ids:
        logger.info("No CC pairs found for cleanup")
        return
    
    # 获取统计信息
    stats = get_cleanup_statistics(cc_pair_ids)
    logger.info(f"Cleanup will affect: {stats}")
    
    if dry_run:
        logger.info(f"DRY RUN: Would delete {len(cc_pair_ids)} CC pairs and related data")
        logger.info(f"CC Pair IDs: {cc_pair_ids[:10]}{'...' if len(cc_pair_ids) > 10 else ''}")
        return
    
    # 确认清理
    print(f"\n⚠️  DANGER: About to delete {len(cc_pair_ids)} CC pairs and related data:")
    print(f"   - CC Pairs: {len(cc_pair_ids)}")
    print(f"   - Index Attempts: {stats.get('index_attempts', 0)}")
    print(f"   - User Files: {stats.get('user_files', 0)}")
    print(f"   - Documents: {stats.get('documents', 0)}")
    
    confirm = input("\nType 'DELETE' to confirm (case sensitive): ")
    if confirm != "DELETE":
        logger.info("Cleanup cancelled by user")
        return
    
    # 执行清理
    logger.info("Starting actual cleanup...")
    success_count = 0
    error_count = 0
    
    for cc_pair_id in cc_pair_ids:
        try:
            logger.info(f"Deleting CC pair {cc_pair_id}")
            
            # 使用现有的 connector_deletion_task 确保完整清理
            with get_session_with_current_tenant() as db_session:
                cc_pair = get_connector_credential_pair_from_id(db_session, cc_pair_id)
                if cc_pair:
                    # 标记为 DELETING 状态
                    cc_pair.status = ConnectorCredentialPairStatus.DELETING
                    db_session.commit()
                    
                    # 调用删除任务
                    connector_deletion_task.apply_async(args=[cc_pair_id])
                    success_count += 1
                    
                    # 避免过快删除
                    time.sleep(0.1)
                else:
                    logger.warning(f"CC pair {cc_pair_id} not found, may have been deleted already")
                    
        except Exception as e:
            logger.error(f"Error deleting CC pair {cc_pair_id}: {e}")
            error_count += 1
    
    logger.info(f"Cleanup completed: {success_count} successful, {error_count} errors")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up old INITIAL_INDEXING CC pairs")
    parser.add_argument("--days", type=int, default=2, help="Delete CC pairs older than N days (default: 2)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    safe_cleanup_initial_indexing(
        days_threshold=args.days,
        dry_run=args.dry_run
    )