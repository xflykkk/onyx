#!/usr/bin/env python3
"""
清理 Celery 和 Redis 中的脏数据脚本

主要解决：
1. fence not found 错误
2. 清理 Redis 中的索引任务状态
3. 清理 Celery 队列中的脏任务
4. 重置所有连接器的 Redis 状态
"""

import argparse
import logging
import sys
import time
from typing import Any

import redis
from celery import Celery
from redis import Redis

# 添加父目录到 Python 路径
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from onyx.background.celery.celery_redis import celery_get_queue_length
from onyx.configs.app_configs import REDIS_DB_NUMBER_CELERY, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
from onyx.redis.redis_pool import RedisPool
from onyx.redis.redis_connector_index import RedisConnectorIndex
from onyx.redis.redis_connector_delete import RedisConnectorDelete
from onyx.redis.redis_connector_prune import RedisConnectorPrune
from onyx.redis.redis_connector_doc_perm_sync import RedisConnectorPermissionSync
from onyx.redis.redis_connector_ext_group_sync import RedisConnectorExternalGroupSync
from onyx.redis.redis_document_set import RedisDocumentSet
from onyx.redis.redis_usergroup import RedisUserGroup
from onyx.redis.redis_connector_credential_pair import RedisGlobalConnectorCredentialPair
from onyx.redis.redis_connector_stop import RedisConnectorStop

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

def get_redis_connection() -> Redis:
    """获取 Redis 连接"""
    pool = RedisPool.create_pool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB_NUMBER_CELERY,
        password=REDIS_PASSWORD or "",
        ssl=False,
        ssl_cert_reqs="optional",
        ssl_ca_certs=None,
    )
    return Redis(connection_pool=pool)

def purge_celery_queue(redis_conn: Redis, queue_name: str, dry_run: bool = True) -> int:
    """清理指定的 Celery 队列"""
    logger.info(f"正在清理队列: {queue_name}")
    
    length = celery_get_queue_length(queue_name, redis_conn)
    logger.info(f"队列 {queue_name} 当前长度: {length}")
    
    if dry_run:
        logger.info(f"[DRY RUN] 将清理队列 {queue_name} 中的 {length} 个任务")
        return length
    
    # Celery 使用优先级队列，需要清理所有优先级的队列
    total_deleted = 0
    from onyx.configs.constants import OnyxCeleryPriority
    from onyx.background.celery.configs.base import CELERY_SEPARATOR
    
    # 清理主队列和所有优先级队列
    for priority in range(len(OnyxCeleryPriority)):
        queue_key = f"{queue_name}{CELERY_SEPARATOR}{priority}" if priority > 0 else queue_name
        
        # 获取队列长度
        current_length = redis_conn.llen(queue_key)
        if current_length > 0:
            # 删除队列
            deleted = redis_conn.delete(queue_key)
            logger.info(f"删除了队列 {queue_key}，长度: {current_length}，删除结果: {deleted}")
            total_deleted += current_length
        
    # 也清理 unacked 任务
    unacked_key = f"unacked_{queue_name}"
    if redis_conn.exists(unacked_key):
        redis_conn.delete(unacked_key)
        logger.info(f"删除了 unacked 队列: {unacked_key}")
    
    logger.info(f"队列 {queue_name} 总共清理了 {total_deleted} 个任务")
    return total_deleted

def reset_all_redis_connectors(redis_conn: Redis, dry_run: bool = True) -> None:
    """重置所有连接器的 Redis 状态"""
    logger.info("正在重置所有连接器的 Redis 状态...")
    
    reset_functions = [
        ("索引任务", RedisConnectorIndex.reset_all),
        ("删除任务", RedisConnectorDelete.reset_all),
        ("修剪任务", RedisConnectorPrune.reset_all),
        ("权限同步任务", RedisConnectorPermissionSync.reset_all),
        ("外部组同步任务", RedisConnectorExternalGroupSync.reset_all),
        ("文档集任务", RedisDocumentSet.reset_all),
        ("用户组任务", RedisUserGroup.reset_all),
        ("全局连接器任务", RedisGlobalConnectorCredentialPair.reset_all),
        ("连接器停止任务", RedisConnectorStop.reset_all),
    ]
    
    for name, reset_func in reset_functions:
        try:
            if dry_run:
                logger.info(f"[DRY RUN] 将重置 {name}")
            else:
                logger.info(f"正在重置 {name}...")
                reset_func(redis_conn)
                logger.info(f"已重置 {name}")
        except Exception as e:
            logger.error(f"重置 {name} 时出错: {e}")

def clean_redis_patterns(redis_conn: Redis, patterns: list[str], dry_run: bool = True) -> int:
    """清理 Redis 中匹配指定模式的键"""
    total_deleted = 0
    
    for pattern in patterns:
        logger.info(f"正在扫描模式: {pattern}")
        keys_to_delete = []
        
        for key in redis_conn.scan_iter(match=pattern, count=1000):
            keys_to_delete.append(key)
            if len(keys_to_delete) >= 1000:  # 批量处理
                if dry_run:
                    logger.info(f"[DRY RUN] 将删除 {len(keys_to_delete)} 个键 (模式: {pattern})")
                else:
                    deleted = redis_conn.delete(*keys_to_delete)
                    logger.info(f"删除了 {deleted} 个键 (模式: {pattern})")
                    total_deleted += deleted
                keys_to_delete = []
        
        # 处理剩余的键
        if keys_to_delete:
            if dry_run:
                logger.info(f"[DRY RUN] 将删除 {len(keys_to_delete)} 个键 (模式: {pattern})")
            else:
                deleted = redis_conn.delete(*keys_to_delete)
                logger.info(f"删除了 {deleted} 个键 (模式: {pattern})")
                total_deleted += deleted
    
    return total_deleted

def clean_celery_metadata(redis_conn: Redis, dry_run: bool = True) -> int:
    """清理 Celery 任务元数据"""
    logger.info("正在清理 Celery 任务元数据...")
    
    patterns = [
        "celery-task-meta-*",
        "*reply.celery.pidbox*",
        "*celery*result*",
    ]
    
    return clean_redis_patterns(redis_conn, patterns, dry_run)

def cleanup_indexing_fences(redis_conn: Redis, dry_run: bool = True) -> int:
    """专门清理索引相关的 fence"""
    logger.info("正在清理索引 fence...")
    
    patterns = [
        "connectorindexing_fence_*",
        "connectorindexing_*",
        "connectorindexing+*",
    ]
    
    return clean_redis_patterns(redis_conn, patterns, dry_run)

def main():
    parser = argparse.ArgumentParser(description="清理 Celery 和 Redis 中的脏数据")
    parser.add_argument("--dry-run", action="store_true", help="只显示将要执行的操作，不实际执行")
    parser.add_argument("--reset-connectors", action="store_true", help="重置所有连接器的 Redis 状态")
    parser.add_argument("--clean-queues", action="store_true", help="清理 Celery 队列")
    parser.add_argument("--clean-metadata", action="store_true", help="清理 Celery 任务元数据")
    parser.add_argument("--clean-fences", action="store_true", help="清理索引 fence")
    parser.add_argument("--all", action="store_true", help="执行所有清理操作")
    parser.add_argument("--queue", type=str, help="指定要清理的队列名称")
    
    args = parser.parse_args()
    
    if not any([args.reset_connectors, args.clean_queues, args.clean_metadata, 
                args.clean_fences, args.all, args.queue]):
        parser.print_help()
        sys.exit(1)
    
    dry_run = args.dry_run
    if dry_run:
        logger.info("=== DRY RUN 模式 - 只显示将要执行的操作 ===")
    else:
        logger.info("=== 实际执行清理操作 ===")
        response = input("确认要执行清理操作吗？(y/N): ")
        if response.lower() != 'y':
            logger.info("操作已取消")
            sys.exit(0)
    
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        logger.info("Redis 连接成功")
    except Exception as e:
        logger.error(f"无法连接到 Redis: {e}")
        sys.exit(1)
    
    total_operations = 0
    
    # 清理指定队列
    if args.queue:
        total_operations += purge_celery_queue(redis_conn, args.queue, dry_run)
    
    # 清理所有队列
    if args.clean_queues or args.all:
        queues_to_clean = [
            "celery",
            "connector_indexing", 
            "user_files_indexing",
            "vespa_metadata_sync",
            "connector_deletion",
            "doc_permissions_upsert",
            "checkpoint_cleanup",
            "connector_pruning",
            "connector_doc_permissions_sync",
            "connector_external_group_sync",
            "csv_generation",
            "monitoring",
            "kg_processing"
        ]
        
        for queue in queues_to_clean:
            total_operations += purge_celery_queue(redis_conn, queue, dry_run)
    
    # 清理索引 fence
    if args.clean_fences or args.all:
        total_operations += cleanup_indexing_fences(redis_conn, dry_run)
    
    # 重置连接器状态
    if args.reset_connectors or args.all:
        reset_all_redis_connectors(redis_conn, dry_run)
    
    # 清理元数据
    if args.clean_metadata or args.all:
        total_operations += clean_celery_metadata(redis_conn, dry_run)
    
    if dry_run:
        logger.info(f"=== DRY RUN 完成 - 总计将执行 {total_operations} 个清理操作 ===")
        logger.info("要实际执行清理，请移除 --dry-run 参数")
    else:
        logger.info(f"=== 清理完成 - 总计执行了 {total_operations} 个操作 ===")
        logger.info("建议重启 Celery workers 以确保状态同步")

if __name__ == "__main__":
    main() 