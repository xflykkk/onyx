#!/usr/bin/env python3
"""
Celery Proxy API
代理访问 Flower 的 Celery 监控 API
"""
import httpx
from fastapi import APIRouter, HTTPException
from onyx.utils.logger import setup_logger
import time

logger = setup_logger()

router = APIRouter(prefix="/api/celery")

FLOWER_BASE_URL = "http://localhost:5001"

# Cache to avoid too frequent logs
_last_error_time = 0
_error_cache_seconds = 60  # Only log errors every 60 seconds


def _should_log_error():
    """Check if we should log error based on rate limiting"""
    global _last_error_time
    current_time = time.time()
    if current_time - _last_error_time > _error_cache_seconds:
        _last_error_time = current_time
        return True
    return False


@router.get("/pending")
async def get_pending_tasks():
    """获取待处理的 Celery 任务"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FLOWER_BASE_URL}/api/tasks?state=PENDING")
            if response.status_code == 200:
                return response.json()
            else:
                if _should_log_error():
                    logger.warning(f"Flower API returned status {response.status_code}")
                return {"pending_tasks": []}
    except Exception as e:
        if _should_log_error():
            logger.warning(f"Failed to connect to Flower: {e}")
        return {"pending_tasks": []}


@router.get("/active")
async def get_active_tasks():
    """获取正在执行的 Celery 任务"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FLOWER_BASE_URL}/api/tasks?state=ACTIVE")
            if response.status_code == 200:
                return response.json()
            else:
                if _should_log_error():
                    logger.warning(f"Flower API returned status {response.status_code}")
                return {"active_tasks": []}
    except Exception as e:
        if _should_log_error():
            logger.warning(f"Failed to connect to Flower: {e}")
        return {"active_tasks": []}


@router.get("/workers")
async def get_workers():
    """获取 Celery worker 状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FLOWER_BASE_URL}/api/workers")
            if response.status_code == 200:
                return response.json()
            else:
                if _should_log_error():
                    logger.warning(f"Flower API returned status {response.status_code}")
                return {"workers": {}}
    except Exception as e:
        if _should_log_error():
            logger.warning(f"Failed to connect to Flower: {e}")
        return {"workers": {}}