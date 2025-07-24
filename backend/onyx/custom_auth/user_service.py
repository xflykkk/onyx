from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
import secrets

from .models import ExternalUserRegisterRequest
from onyx.db.models import User
from onyx.auth.schemas import UserRole, UserCreate

class ExternalUserService:
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        return db.execute(
            select(User)
            .where(User.email == email)
            .where(User.is_active == True)
        ).unique().scalar_one_or_none()
    
    @staticmethod
    async def create_external_user(
        request: ExternalUserRegisterRequest, 
        user_manager,
        db: Session
    ) -> User:
        """创建外部用户"""
        # 检查是否已存在
        existing_user = ExternalUserService.get_user_by_email(db, request.email)
        if existing_user:
            # 如果用户已存在，直接返回
            return existing_user
        
        # 生成随机密码（外部用户不会直接登录）
        random_password = secrets.token_urlsafe(32)
        
        # 使用现有的用户创建接口创建用户
        user_create = UserCreate(
            email=request.email,  # 直接使用真实邮箱
            password=random_password,
            role=UserRole.BASIC,
            is_verified=True,
            is_active=True
        )
        
        # 调用现有的用户创建函数
        internal_user = await user_manager.create(user_create, safe=False, request=None)
        
        return internal_user