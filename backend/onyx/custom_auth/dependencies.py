from fastapi import Depends, Request
from typing import Optional

from onyx.db.models import User
from onyx.auth.users import current_chat_accessible_user as original_current_chat_accessible_user
from .auth_converter import validate_external_user_and_convert, is_external_auth_enabled

async def current_custom_chat_user(
    request: Request,
    original_user: Optional[User] = Depends(original_current_chat_accessible_user)
) -> Optional[User]:
    """
    自定义鉴权依赖注入，保持原有接口签名不变
    
    优先级：外部鉴权 > 原生鉴权
    """
    import logging
    from onyx.server.utils import BasicAuthenticationError
    logger = logging.getLogger(__name__)
    
    # 如果启用了外部鉴权，强制使用外部鉴权
    if is_external_auth_enabled():
        print("[CUSTOM_AUTH] External auth enabled, attempting external authentication")
        logger.info("External auth enabled, attempting external authentication")
        external_user = await validate_external_user_and_convert(request)
        if external_user:
            print(f"[CUSTOM_AUTH] External auth success, user: {external_user.email}")
            logger.info(f"External auth success, user: {external_user.email}")
            return external_user
        else:
            print("[CUSTOM_AUTH] External auth failed, raising authentication error")
            logger.warning("External auth failed, raising authentication error")
            # 外部鉴权启用时，认证失败应该抛出异常而不是返回None
            raise BasicAuthenticationError(detail="Authentication required")
    
    # 外部鉴权未启用，使用原生鉴权
    logger.info("External auth disabled, using original auth")
    return original_user