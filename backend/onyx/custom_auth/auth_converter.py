from fastapi import HTTPException, status, Request
from typing import Optional
import logging

from .external_auth_client import external_auth_client
from onyx.db.models import User

logger = logging.getLogger(__name__)

async def validate_external_user_and_convert(request: Request) -> Optional[User]:
    """
    外部鉴权+用户转换的核心方法
    
    1. 提取用户令牌
    2. 调用外部服务验证令牌并获取用户信息
    3. 根据邮箱查找内部用户
    4. 返回 User 对象，保持接口不变
    """
    print(f"[AUTH_CONVERTER] Starting external user validation...")
    
    # 1. 提取认证信息 - 支持多种token传递方式
    auth_token = (
        request.headers.get("Authorization") or 
        request.headers.get("X-Auth-Token") or
        request.headers.get("X-User-Token")
    )
    
    print(f"[AUTH_CONVERTER] Request headers: {dict(request.headers)}")
    print(f"[AUTH_CONVERTER] Auth token found: {bool(auth_token)}")
    
    if not auth_token:
        print(f"[AUTH_CONVERTER] No auth token found in headers")
        return None
    
    # 清理token格式
    original_token = auth_token
    if auth_token.startswith("Bearer "):
        auth_token = auth_token[7:]
    
    print(f"[AUTH_CONVERTER] Original token: {original_token[:20]}...")
    print(f"[AUTH_CONVERTER] Cleaned token: {auth_token[:20]}...")
    
    # 2. 调用外部服务验证令牌
    try:
        print(f"[AUTH_CONVERTER] Calling external auth client...")
        auth_response = await external_auth_client.validate_token(auth_token)
        print(f"[AUTH_CONVERTER] External auth response: {auth_response}")
        
        if not auth_response or not auth_response.success:
            print(f"[AUTH_CONVERTER] External auth failed - response: {auth_response}")
            logger.warning(f"External auth failed for token")
            return None
        
        # 3. 检查是否有邮箱信息
        if not auth_response.email:
            print(f"[AUTH_CONVERTER] No email in auth response")
            logger.warning(f"No email returned from external auth service")
            return None
        
        print(f"[AUTH_CONVERTER] Got email from external auth: {auth_response.email}")
        
        # 4. 直接创建用户对象，不依赖数据库查找
        print(f"[AUTH_CONVERTER] Creating user object from external auth data")
        
        # 创建一个虚拟用户对象，用于外部鉴权
        from onyx.db.models import User
        virtual_user = User(
            id=auth_response.user_id,
            email=auth_response.email,
            is_active=True,
            is_superuser=False,
            is_verified=True
        )
        
        print(f"[AUTH_CONVERTER] Created virtual user: {virtual_user.email} (ID: {virtual_user.id})")
        logger.info(f"External auth success for email: {auth_response.email}")
        return virtual_user
    
    except Exception as e:
        print(f"[AUTH_CONVERTER] Exception in external auth conversion: {str(e)}")
        print(f"[AUTH_CONVERTER] Exception type: {type(e).__name__}")
        logger.error(f"Error in external auth conversion: {e}")
        return None

# 检查是否启用外部鉴权
try:
    from onyx.configs.app_configs import EXTERNAL_AUTH_ENABLED
except ImportError:
    EXTERNAL_AUTH_ENABLED = False
def is_external_auth_enabled() -> bool:
    return EXTERNAL_AUTH_ENABLED