#!/usr/bin/env python3
"""
批量安全清理 - 分批处理 INITIAL_INDEXING CC Pairs
"""

import time
from datetime import datetime, timedelta, timezone
from onyx.db.engine.sql_engine import get_session_with_current_tenant, SqlEngine
from onyx.db.enums import ConnectorCredentialPairStatus
from onyx.db.models import (
    ConnectorCredentialPair, 
    Connector, 
    IndexAttempt, 
    IndexAttemptError,
    UserFile,
    DocumentSet__ConnectorCredentialPair,
    UserGroup__ConnectorCredentialPair,
    Persona__UserFile,
    DocumentByConnectorCredentialPair
)
from onyx.utils.logger import setup_logger
from sqlalchemy import and_, func, select, delete

logger = setup_logger()

def cleanup_cc_pairs_batch(cc_pair_ids: list[int], batch_size: int = 100) -> dict:
    """分批清理CC Pairs"""
    total_results = {
        'processed': 0,
        'successful': 0,
        'failed': 0,
        'cc_pairs': 0,
        'index_attempts': 0,
        'index_errors': 0,
        'user_files': 0,
        'persona_user_files': 0,
        'document_set_assocs': 0,
        'user_group_assocs': 0,
        'documents': 0
    }
    
    # 分批处理
    for i in range(0, len(cc_pair_ids), batch_size):
        batch_ids = cc_pair_ids[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}: CC pairs {batch_ids[0]} to {batch_ids[-1]} ({len(batch_ids)} items)")
        
        try:
            with get_session_with_current_tenant() as db_session:
                # 批量删除相关数据
                
                # 1. Index Attempt Errors
                index_errors_stmt = delete(IndexAttemptError).where(
                    IndexAttemptError.connector_credential_pair_id.in_(batch_ids)
                )
                result = db_session.execute(index_errors_stmt)
                total_results['index_errors'] += result.rowcount
                
                # 2. Index Attempts
                index_attempts_stmt = delete(IndexAttempt).where(
                    IndexAttempt.connector_credential_pair_id.in_(batch_ids)
                )
                result = db_session.execute(index_attempts_stmt)
                total_results['index_attempts'] += result.rowcount
                
                # 3. Persona-UserFile 关联
                persona_userfile_stmt = delete(Persona__UserFile).where(
                    Persona__UserFile.user_file_id.in_(
                        select(UserFile.id).where(UserFile.cc_pair_id.in_(batch_ids))
                    )
                )
                result = db_session.execute(persona_userfile_stmt)
                total_results['persona_user_files'] += result.rowcount
                
                # 4. User Files
                user_files_stmt = delete(UserFile).where(UserFile.cc_pair_id.in_(batch_ids))
                result = db_session.execute(user_files_stmt)
                total_results['user_files'] += result.rowcount
                
                # 5. Document Set 关联
                doc_set_stmt = delete(DocumentSet__ConnectorCredentialPair).where(
                    DocumentSet__ConnectorCredentialPair.connector_credential_pair_id.in_(batch_ids)
                )
                result = db_session.execute(doc_set_stmt)
                total_results['document_set_assocs'] += result.rowcount
                
                # 6. User Group 关联
                user_group_stmt = delete(UserGroup__ConnectorCredentialPair).where(
                    UserGroup__ConnectorCredentialPair.cc_pair_id.in_(batch_ids)
                )
                result = db_session.execute(user_group_stmt)
                total_results['user_group_assocs'] += result.rowcount
                
                # 7. 清理 Documents (批量获取connector_id和credential_id)
                cc_pair_info_stmt = select(
                    ConnectorCredentialPair.connector_id,
                    ConnectorCredentialPair.credential_id
                ).where(ConnectorCredentialPair.id.in_(batch_ids))
                cc_pair_info = db_session.execute(cc_pair_info_stmt).fetchall()
                
                for connector_id, credential_id in cc_pair_info:
                    docs_stmt = delete(DocumentByConnectorCredentialPair).where(
                        and_(
                            DocumentByConnectorCredentialPair.connector_id == connector_id,
                            DocumentByConnectorCredentialPair.credential_id == credential_id
                        )
                    )
                    result = db_session.execute(docs_stmt)
                    total_results['documents'] += result.rowcount
                
                # 8. 最后删除 CC Pairs
                cc_pair_stmt = delete(ConnectorCredentialPair).where(
                    ConnectorCredentialPair.id.in_(batch_ids)
                )
                result = db_session.execute(cc_pair_stmt)
                total_results['cc_pairs'] += result.rowcount
                
                # 提交批次
                db_session.commit()
                total_results['processed'] += len(batch_ids)
                total_results['successful'] += len(batch_ids)
                
                logger.info(f"Batch {i//batch_size + 1} completed successfully - deleted {len(batch_ids)} CC pairs")
                
                # 避免过快处理
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
            total_results['failed'] += len(batch_ids)
            continue
    
    return total_results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch cleanup of old INITIAL_INDEXING CC pairs")
    parser.add_argument("--days", type=int, default=1, help="Delete CC pairs older than N days (default: 1)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing (default: 100)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    # 初始化数据库引擎
    try:
        SqlEngine.init_engine(pool_size=10, max_overflow=20, app_name='batch_cleanup_script')
        logger.info("Database engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}")
        return
    
    logger.info(f"Starting {'DRY RUN' if args.dry_run else 'ACTUAL'} batch cleanup of INITIAL_INDEXING CC pairs older than {args.days} days")
    
    # 获取需要清理的 CC Pairs
    with get_session_with_current_tenant() as db_session:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=args.days)
        
        stmt = (
            select(ConnectorCredentialPair.id)
            .join(Connector, ConnectorCredentialPair.connector_id == Connector.id)
            .where(
                and_(
                    ConnectorCredentialPair.status == ConnectorCredentialPairStatus.INITIAL_INDEXING,
                    Connector.time_created < cutoff_time
                )
            )
            .order_by(ConnectorCredentialPair.id)
        )
        
        result = db_session.execute(stmt).fetchall()
        cc_pair_ids = [row[0] for row in result]
    
    if not cc_pair_ids:
        logger.info("No CC pairs found for cleanup")
        return
    
    logger.info(f"Found {len(cc_pair_ids)} INITIAL_INDEXING CC pairs to clean up")
    logger.info(f"Will process in batches of {args.batch_size}")
    
    if args.dry_run:
        logger.info(f"DRY RUN: Would clean up {len(cc_pair_ids)} CC pairs in {(len(cc_pair_ids) + args.batch_size - 1) // args.batch_size} batches")
        return
    
    # 确认清理
    if not args.force:
        print(f"\n⚠️  DANGER: About to permanently delete {len(cc_pair_ids)} CC pairs and ALL related data!")
        print(f"   Processing in batches of {args.batch_size}")
        print(f"   Make sure you have a database backup!")
        
        confirm = input("\nType 'DELETE_ALL' to confirm (case sensitive): ")
        if confirm != "DELETE_ALL":
            logger.info("Cleanup cancelled by user")
            return
    
    # 执行清理
    logger.info("Starting batch cleanup...")
    results = cleanup_cc_pairs_batch(cc_pair_ids, args.batch_size)
    
    logger.info("=== Batch Cleanup Results ===")
    logger.info(f"Processed: {results['processed']}")
    logger.info(f"Successful: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"CC Pairs deleted: {results['cc_pairs']}")
    logger.info(f"Index attempts deleted: {results['index_attempts']}")
    logger.info(f"Index errors deleted: {results['index_errors']}")
    logger.info(f"User files deleted: {results['user_files']}")
    logger.info(f"Persona-UserFile associations deleted: {results['persona_user_files']}")
    logger.info(f"Document set associations deleted: {results['document_set_assocs']}")
    logger.info(f"User group associations deleted: {results['user_group_assocs']}")
    logger.info(f"Documents deleted: {results['documents']}")

if __name__ == "__main__":
    main()