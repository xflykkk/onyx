#!/usr/bin/env python3
"""
快速清理历史连接器数据脚本
支持清理 INITIAL_INDEXING 和 PAUSED 状态的连接器
"""

import os
import time
from datetime import datetime, timedelta, timezone

from onyx.db.connector_credential_pair import get_connector_credential_pair_from_id
from onyx.db.engine.sql_engine import get_session_with_current_tenant, SqlEngine
from onyx.db.enums import ConnectorCredentialPairStatus
from onyx.db.models import ConnectorCredentialPair, Connector
from onyx.utils.logger import setup_logger
from sqlalchemy import and_, func, select, delete

logger = setup_logger()

def cleanup_old_initial_indexing_cc_pairs(days_threshold: int = 2, dry_run: bool = True):
    """快速清理历史 INITIAL_INDEXING CC Pairs (2天前的数据)"""
    
    logger.info(f"Starting {'DRY RUN' if dry_run else 'ACTUAL'} cleanup of INITIAL_INDEXING CC pairs older than {days_threshold} days")
    
    with get_session_with_current_tenant() as db_session:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        
        # 查找需要清理的 CC Pairs
        stmt = (
            select(ConnectorCredentialPair.id, Connector.time_created)
            .join(Connector, ConnectorCredentialPair.connector_id == Connector.id)
            .where(
                and_(
                    ConnectorCredentialPair.status == ConnectorCredentialPairStatus.INITIAL_INDEXING,
                    Connector.time_created < cutoff_time
                )
            )
        )
        
        result = db_session.execute(stmt).fetchall()
        cc_pair_ids = [row[0] for row in result]
        
        if not cc_pair_ids:
            logger.info("No old INITIAL_INDEXING CC pairs found for cleanup")
            return
            
        logger.info(f"Found {len(cc_pair_ids)} INITIAL_INDEXING CC pairs to clean up")
        logger.info(f"Oldest creation time: {min(row[1] for row in result)}")
        logger.info(f"Sample CC pair IDs: {cc_pair_ids[:10]}")
        
        if dry_run:
            logger.info(f"DRY RUN: Would delete {len(cc_pair_ids)} CC pairs and related data")
            return cc_pair_ids
        
        # 确认清理
        print(f"\n⚠️  DANGER: About to delete {len(cc_pair_ids)} CC pairs!")
        print(f"   This will delete CC pairs older than {days_threshold} days")
        print(f"   Sample IDs to delete: {cc_pair_ids[:5]}")
        
        confirm = input("\nType 'DELETE' to confirm (case sensitive): ")
        if confirm != "DELETE":
            logger.info("Cleanup cancelled by user")
            return
        
        # 批量删除 CC Pairs (简单方式，依赖数据库约束)
        try:
            delete_stmt = delete(ConnectorCredentialPair).where(
                ConnectorCredentialPair.id.in_(cc_pair_ids)
            )
            result = db_session.execute(delete_stmt)
            db_session.commit()
            
            logger.info(f"Successfully deleted {result.rowcount} CC pairs")
            
        except Exception as e:
            logger.error(f"Error during batch deletion: {e}")
            db_session.rollback()
            
            # 如果批量删除失败，尝试逐个删除
            logger.info("Attempting individual deletion...")
            success_count = 0
            for cc_pair_id in cc_pair_ids:
                try:
                    individual_delete_stmt = delete(ConnectorCredentialPair).where(
                        ConnectorCredentialPair.id == cc_pair_id
                    )
                    db_session.execute(individual_delete_stmt)
                    db_session.commit()
                    success_count += 1
                except Exception as individual_error:
                    logger.error(f"Error deleting CC pair {cc_pair_id}: {individual_error}")
                    db_session.rollback()
                    
            logger.info(f"Individual deletion completed: {success_count}/{len(cc_pair_ids)} successful")

def cleanup_paused_cc_pairs(dry_run: bool = True, force: bool = False):
    """快速清理所有 PAUSED 状态的历史 CC Pairs"""
    
    logger.info(f"Starting {'DRY RUN' if dry_run else 'ACTUAL'} cleanup of PAUSED CC pairs")
    
    with get_session_with_current_tenant() as db_session:
        # 查找需要清理的 PAUSED CC Pairs
        stmt = (
            select(ConnectorCredentialPair.id, Connector.source, Connector.time_created)
            .join(Connector, ConnectorCredentialPair.connector_id == Connector.id)
            .where(ConnectorCredentialPair.status == ConnectorCredentialPairStatus.PAUSED)
            .order_by(Connector.time_created)
        )
        
        result = db_session.execute(stmt).fetchall()
        cc_pair_ids = [row[0] for row in result]
        
        if not cc_pair_ids:
            logger.info("No PAUSED CC pairs found for cleanup")
            return
        
        # 统计按类型分布
        type_stats = {}
        for row in result:
            source = row[1]
            type_stats[source] = type_stats.get(source, 0) + 1
            
        logger.info(f"Found {len(cc_pair_ids)} PAUSED CC pairs to clean up")
        logger.info("Type distribution:")
        for source, count in type_stats.items():
            logger.info(f"  {source}: {count}")
        logger.info(f"Oldest creation time: {min(row[2] for row in result)}")
        logger.info(f"Sample CC pair IDs: {cc_pair_ids[:10]}")
        
        if dry_run:
            logger.info(f"DRY RUN: Would delete {len(cc_pair_ids)} PAUSED CC pairs and related data")
            return cc_pair_ids
        
        # 确认清理
        print(f"\n⚠️  DANGER: About to delete {len(cc_pair_ids)} PAUSED CC pairs!")
        print("   This includes:")
        for source, count in type_stats.items():
            print(f"     {source}: {count} pairs")
        print(f"   Sample IDs to delete: {cc_pair_ids[:5]}")
        
        if not force:
            confirm = input("\nType 'DELETE' to confirm (case sensitive): ")
            if confirm != "DELETE":
                logger.info("Cleanup cancelled by user")
                return
        else:
            logger.info("Force mode enabled, skipping confirmation")
            print("   FORCE mode: Proceeding with deletion...")
        
        # 首先清理所有相关的依赖表记录
        logger.info("Step 1: Cleaning up all related records...")
        try:
            from onyx.db.models import IndexAttempt
            from sqlalchemy import text
            
            # 分批处理，避免一次处理太多
            batch_size = 100
            total_errors_deleted = 0
            total_index_attempts_deleted = 0
            total_user_files_deleted = 0
            
            for i in range(0, len(cc_pair_ids), batch_size):
                batch_ids = cc_pair_ids[i:i+batch_size]
                
                # 1. 先删除 user_file 记录
                try:
                    delete_user_files_sql = text("DELETE FROM user_file WHERE cc_pair_id = ANY(:ids)")
                    result = db_session.execute(delete_user_files_sql, {"ids": batch_ids})
                    batch_user_files_deleted = result.rowcount if hasattr(result, 'rowcount') else 0
                    total_user_files_deleted += batch_user_files_deleted
                    logger.info(f"Batch {i//batch_size + 1}: Deleted {batch_user_files_deleted} user_file records")
                except Exception as e:
                    logger.warning(f"Error deleting user_file records: {e}")
                
                # 2. 获取相关的index_attempt ID
                index_attempt_query = select(IndexAttempt.id).where(
                    IndexAttempt.connector_credential_pair_id.in_(batch_ids)
                )
                index_attempt_result = db_session.execute(index_attempt_query).fetchall()
                index_attempt_ids = [row[0] for row in index_attempt_result]
                
                if index_attempt_ids:
                    # 3. 删除 index_attempt_errors 记录
                    try:
                        delete_errors_sql = text("DELETE FROM index_attempt_errors WHERE index_attempt_id = ANY(:ids)")
                        result = db_session.execute(delete_errors_sql, {"ids": index_attempt_ids})
                        batch_errors_deleted = result.rowcount if hasattr(result, 'rowcount') else 0
                        total_errors_deleted += batch_errors_deleted
                        logger.info(f"Batch {i//batch_size + 1}: Deleted {batch_errors_deleted} index_attempt_errors records")
                    except Exception as e:
                        logger.warning(f"Error deleting index_attempt_errors: {e}")
                
                # 4. 删除相关的index_attempt记录
                delete_index_stmt = delete(IndexAttempt).where(
                    IndexAttempt.connector_credential_pair_id.in_(batch_ids)
                )
                result = db_session.execute(delete_index_stmt) 
                batch_index_attempts_deleted = result.rowcount
                total_index_attempts_deleted += batch_index_attempts_deleted
                
                logger.info(f"Batch {i//batch_size + 1}: Deleted {batch_index_attempts_deleted} index_attempt records")
                
                # 提交每个批次的更改
                db_session.commit()
            
            logger.info(f"Total user_file records deleted: {total_user_files_deleted}")
            logger.info(f"Total index_attempt_errors deleted: {total_errors_deleted}")
            logger.info(f"Total index_attempt records deleted: {total_index_attempts_deleted}")
            
        except Exception as e:
            logger.error(f"Error during related records cleanup: {e}")
            db_session.rollback()
            return
        
        # 现在批量删除 CC Pairs
        logger.info("Step 2: Deleting connector credential pairs...")
        try:
            # 分批删除CC pairs
            batch_size = 100
            total_cc_pairs_deleted = 0
            
            for i in range(0, len(cc_pair_ids), batch_size):
                batch_ids = cc_pair_ids[i:i+batch_size]
                
                delete_stmt = delete(ConnectorCredentialPair).where(
                    ConnectorCredentialPair.id.in_(batch_ids)
                )
                result = db_session.execute(delete_stmt)
                total_cc_pairs_deleted += result.rowcount
                db_session.commit()
                
                logger.info(f"Batch {i//batch_size + 1}: Deleted {result.rowcount} CC pairs")
            
            logger.info(f"Successfully deleted {total_cc_pairs_deleted} PAUSED CC pairs")
            
        except Exception as e:
            logger.error(f"Error during CC pair deletion: {e}")
            db_session.rollback()
            return

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick cleanup of connector credential pairs")
    parser.add_argument("--mode", choices=['initial', 'paused'], default='paused',
                       help="Cleanup mode: 'initial' for INITIAL_INDEXING, 'paused' for PAUSED (default: paused)")
    parser.add_argument("--days", type=int, default=2, 
                       help="Delete CC pairs older than N days (only for initial mode, default: 2)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--force", action="store_true",
                       help="Skip interactive confirmation (use with caution)")
    
    args = parser.parse_args()
    
    # 初始化数据库引擎
    try:
        SqlEngine.init_engine(pool_size=5, max_overflow=10, app_name='cleanup_script')
        logger.info("Database engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}")
        return
    
    if not args.dry_run:
        print("⚠️  This will PERMANENTLY delete database records!")
        print("⚠️  Make sure you have a database backup!")
        print("⚠️  Use --dry-run first to see what will be deleted!")
        
    if args.mode == 'paused':
        cleanup_paused_cc_pairs(dry_run=args.dry_run, force=args.force)
    else:
        cleanup_old_initial_indexing_cc_pairs(
            days_threshold=args.days,
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    main()