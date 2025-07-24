from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .models import ExternalUserRegisterRequest, ExternalUserRegisterResponse
from .user_service import ExternalUserService
from onyx.db.engine.sql_engine import get_session
from onyx.auth.users import current_admin_user, get_user_manager
from onyx.db.models import User

router = APIRouter(prefix="/manage/external-auth", tags=["external-auth"])

@router.post("/register", response_model=ExternalUserRegisterResponse)
async def register_external_user(
    request: ExternalUserRegisterRequest,
    db: Session = Depends(get_session),
    admin_user: User = Depends(current_admin_user),  # 需要管理员权限
    user_manager = Depends(get_user_manager)
):
    """
    注册外部用户
    
    由上游服务调用，创建外部用户账号
    """
    try:
        internal_user = await ExternalUserService.create_external_user(
            request, user_manager, db
        )
        
        return ExternalUserRegisterResponse(
            success=True,
            internal_user_id=str(internal_user.id),
            email=internal_user.email,
            message="User registered successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to register user: {str(e)}"
        )