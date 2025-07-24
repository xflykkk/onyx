# Onyx 外部用户鉴权超简化设计方案

## 1. 设计概述

基于现有 User 模型，设计一个超简化的外部用户鉴权方案：
- **保持原有接口签名不变**: `user: User | None = Depends(current_custom_chat_user)`
- **直接使用邮箱验证**: 从请求头提取用户邮箱 + 令牌，直接调用外部服务验证
- **复用现有用户系统**: 如果用户不存在则自动创建，如果存在则直接使用
- **无需额外映射表**: 直接基于邮箱在 User 表中查找用户
- **无缝转换**: 鉴权成功后返回标准 User 对象

### 1.1 架构流程

```
外部请求 → 提取用户邮箱 + 令牌 → 外部服务验证 → 查找/创建内部用户 → 返回User对象
```

## 2. 外部服务接口规范

### 2.1 令牌验证接口

基于外部鉴权服务的实际API规范：

```http
POST /verify_token
Content-Type: application/json

Request Body:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  // 用户身份令牌
}

Response (Success - 200):
{
  "user_id": 123,                 // 用户ID（可选）
  "email": "user@example.com"     // 用户邮箱（可选）
}

Response (Failure - 401):
{
  "detail": "Invalid token"       // 或其他错误信息
}
```

### 2.2 接口说明

- **简化验证**: 直接通过token获取用户信息，无需额外的权限检查
- **以邮箱为标识**: 返回的email字段用于在内部系统查找用户
- **容错处理**: user_id和email字段都是可选的，增强接口容错性
- **标准HTTP状态码**: 成功返回200，认证失败返回401

## 3. 数据库设计

### 3.1 无需额外表结构

由于采用邮箱作为唯一标识，直接复用现有的 `user` 表，无需创建额外的映射表：

- 外部用户直接使用真实邮箱在 `user` 表中创建记录
- 用户密码随机生成（外部用户不会直接登录）
- 通过 `user.email` 字段查找和识别用户
- 保持现有 User 模型的所有功能和属性

## 4. 模型定义

### 4.1 数据模型 (models.py)

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Pydantic 请求/响应模型
class ExternalUserRegisterRequest(BaseModel):
    email: str
    name: str
    metadata: Optional[Dict[str, Any]] = None

class ExternalUserRegisterResponse(BaseModel):
    success: bool
    internal_user_id: str
    email: str
    message: str

# 外部鉴权服务的请求/响应模型
class TokenVerifyRequest(BaseModel):
    token: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

class ExternalAuthResponse(BaseModel):
    success: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
```

## 5. 外部鉴权服务客户端

### 5.1 简化的鉴权客户端 (external_auth_client.py)

```python
import aiohttp
import asyncio
import logging
import hashlib
from typing import Optional
from datetime import datetime, timedelta

from .models import TokenVerifyRequest, TokenData, ExternalAuthResponse

logger = logging.getLogger(__name__)

class ExternalAuthClient:
    def __init__(self, service_url: str):
        self.service_url = service_url
        self._cache: dict = {}  # 简单的内存缓存
    
    async def validate_token(self, auth_token: str) -> Optional[ExternalAuthResponse]:
        """验证用户令牌并获取用户信息"""
        # 检查缓存
        cache_key = f"token:{hashlib.md5(auth_token.encode()).hexdigest()[:8]}"
        if cache_key in self._cache:
            cached_data, expires_at = self._cache[cache_key]
            if datetime.now() < expires_at:
                logger.debug(f"Cache hit for token: {cache_key}")
                return ExternalAuthResponse(**cached_data)
        
        # 调用外部服务
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "token": auth_token
                }
                
                async with session.post(
                    f"{self.service_url}/verify_token",
                    json=payload,
                    headers=headers,
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 根据实际API响应格式解析
                        auth_response = ExternalAuthResponse(
                            success=True,
                            user_id=data.get("user_id"),
                            email=data.get("email")
                        )
                        
                        # 缓存结果5分钟
                        self._cache[cache_key] = (
                            auth_response.dict(), 
                            datetime.now() + timedelta(minutes=5)
                        )
                        
                        return auth_response
                    
                    elif response.status == 401:
                        logger.warning(f"Token validation failed: 401 Unauthorized")
                        return None
        
        except Exception as e:
            logger.error(f"External auth service call failed: {e}")
        
        return None

# 全局实例  
from onyx.configs.app_configs import EXTERNAL_AUTH_SERVICE_URL
external_auth_client = ExternalAuthClient(
    service_url=EXTERNAL_AUTH_SERVICE_URL or "http://localhost:8080"
)
```

## 6. 核心鉴权逻辑

### 6.1 用户服务 (user_service.py)

```python
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
import secrets

from .models import ExternalUserRegisterRequest
from onyx.db.models import User
from onyx.auth.schemas import UserRole
from onyx.server.manage.models import CreateUserRequest
from onyx.server.manage.users import create_user_by_admin

class ExternalUserService:
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        return db.execute(
            select(User)
            .where(User.email == email)
            .where(User.is_active == True)
        ).scalar_one_or_none()
    
    @staticmethod
    def create_external_user(db: Session, request: ExternalUserRegisterRequest, admin_user: User) -> User:
        """创建外部用户"""
        # 检查是否已存在
        existing_user = ExternalUserService.get_user_by_email(db, request.email)
        if existing_user:
            # 如果用户已存在，直接返回
            return existing_user
        
        # 生成随机密码（外部用户不会直接登录）
        random_password = secrets.token_urlsafe(32)
        
        # 使用现有的用户创建接口创建用户
        create_user_request = CreateUserRequest(
            email=request.email,  # 直接使用真实邮箱
            password=random_password,
            role=UserRole.BASIC,
            is_verified=True
        )
        
        # 调用现有的用户创建函数
        internal_user = create_user_by_admin(
            user_data=create_user_request,
            current_user=admin_user,
            db_session=db
        )
        
        return internal_user
```

### 6.2 外部鉴权+用户转换方法 (auth_converter.py)

```python
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
import logging

from .external_auth_client import external_auth_client
from .user_service import ExternalUserService
from onyx.db.models import User
from onyx.db.engine.sql_engine import get_session

logger = logging.getLogger(__name__)

async def validate_external_user_and_convert(request: Request) -> Optional[User]:
    """
    外部鉴权+用户转换的核心方法
    
    1. 提取用户令牌
    2. 调用外部服务验证令牌并获取用户信息
    3. 根据邮箱查找内部用户
    4. 返回 User 对象，保持接口不变
    """
    # 1. 提取认证信息 - 支持多种token传递方式
    auth_token = (
        request.headers.get("Authorization") or 
        request.headers.get("X-Auth-Token") or
        request.headers.get("X-User-Token")
    )
    
    if not auth_token:
        return None
    
    # 清理token格式
    if auth_token.startswith("Bearer "):
        auth_token = auth_token[7:]
    
    # 2. 调用外部服务验证令牌
    try:
        auth_response = await external_auth_client.validate_token(auth_token)
        
        if not auth_response or not auth_response.success:
            logger.warning(f"External auth failed for token")
            return None
        
        # 3. 检查是否有邮箱信息
        if not auth_response.email:
            logger.warning(f"No email returned from external auth service")
            return None
        
        # 4. 根据邮箱查找内部用户
        with get_session() as db:
            internal_user = ExternalUserService.get_user_by_email(db, auth_response.email)
            
            if not internal_user:
                logger.warning(f"Internal user not found for email: {auth_response.email}")
                return None
            
            logger.info(f"External auth success for email: {auth_response.email}")
            return internal_user
    
    except Exception as e:
        logger.error(f"Error in external auth conversion: {e}")
        return None

# 检查是否启用外部鉴权
from onyx.configs.app_configs import EXTERNAL_AUTH_ENABLED
def is_external_auth_enabled() -> bool:
    return EXTERNAL_AUTH_ENABLED
```

## 7. FastAPI 依赖注入

### 7.1 修改后的依赖注入 (dependencies.py)

```python
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
    # 如果启用了外部鉴权，尝试外部鉴权
    if is_external_auth_enabled():
        external_user = await validate_external_user_and_convert(request)
        if external_user:
            return external_user
    
    # 降级到原生鉴权
    return original_user
```

## 8. 用户注册接口

### 8.1 注册接口 (registration_api.py)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .models import ExternalUserRegisterRequest, ExternalUserRegisterResponse
from .user_service import ExternalUserService
from onyx.db.engine.sql_engine import get_session
from onyx.auth.users import current_admin_user

router = APIRouter(prefix="/manage/external-auth", tags=["external-auth"])

@router.post("/register", response_model=ExternalUserRegisterResponse)
def register_external_user(
    request: ExternalUserRegisterRequest,
    db: Session = Depends(get_session),
    admin_user = Depends(current_admin_user)  # 需要管理员权限
):
    """
    注册外部用户
    
    由上游服务调用，创建外部用户账号
    """
    try:
        internal_user = ExternalUserService.create_external_user(db, request, admin_user)
        
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
```

## 9. 集成到现有接口

### 9.1 Chat 接口保持不变

```python
# chat_backend.py 中的接口完全不变
from onyx.custom_auth.dependencies import current_custom_chat_user

@router.post("/send-message")
def handle_new_chat_message(
    chat_message_req: CreateChatMessageRequest,
    request: Request,
    user: User | None = Depends(current_custom_chat_user),  # 只是替换依赖注入
    _rate_limit_check: None = Depends(check_token_rate_limits),
    is_connected_func: Callable[[], bool] = Depends(is_connected),
) -> StreamingResponse:
    # 现有逻辑完全不变
    # user.id, user.email 等属性正常使用
    # ...
```

## 10. 环境配置

### 10.1 配置文件集成

将外部鉴权配置添加到现有的配置文件中：

**backend/shared_configs/configs.py**:
```python
# 外部鉴权配置
EXTERNAL_AUTH_ENABLED = os.environ.get("EXTERNAL_AUTH_ENABLED", "false").lower() == "true"
EXTERNAL_AUTH_SERVICE_URL = os.environ.get("EXTERNAL_AUTH_SERVICE_URL", "")
```

**backend/onyx/configs/app_configs.py**:
```python
from shared_configs.configs import EXTERNAL_AUTH_ENABLED, EXTERNAL_AUTH_SERVICE_URL

# 导出配置供其他模块使用
__all__ = [
    # ... 现有导出
    "EXTERNAL_AUTH_ENABLED",
    "EXTERNAL_AUTH_SERVICE_URL",
]
```

### 10.2 环境变量

```bash
# .env 文件
EXTERNAL_AUTH_ENABLED=true
EXTERNAL_AUTH_SERVICE_URL=http://localhost:8080
```

## 11. 使用流程

### 11.1 注册用户
```bash
# 上游服务调用注册接口（基本信息：邮箱和姓名）
curl -X POST "http://localhost:8888/manage/external-auth/register" \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com", 
    "name": "John Doe"
  }'

# 返回结果示例：
# {
#   "success": true,
#   "internal_user_id": "550e8400-e29b-41d4-a716-446655440000",
#   "email": "user@example.com",
#   "message": "User registered successfully"
# }
# 
# 内部会自动创建：
# - 邮箱: user@example.com (真实邮箱)
# - 随机密码: (32位随机token)
# - 用户状态: 已激活 (is_verified=true)
```

### 11.2 聊天请求
```bash
# 前端发送聊天请求（支持多种token传递方式）
curl -X POST "http://localhost:8888/chat/send-message" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello"
  }'

# 推荐使用 X-Auth-Token 头（避免与API key冲突）
curl -X POST "http://localhost:8888/chat/send-message" \
  -H "X-Auth-Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello"
  }'

# 或使用 X-User-Token 头
curl -X POST "http://localhost:8888/chat/send-message" \
  -H "X-User-Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello"
  }'

# 鉴权流程：
# 1. 系统从请求头中提取用户token（支持Authorization、X-Auth-Token、X-User-Token）
# 2. 调用外部服务 /verify_token 接口验证token
# 3. 获取返回的邮箱信息 user@example.com
# 4. 通过邮箱在内部 user 表中查找用户
# 5. 返回 User 对象，chat 接口正常工作
```

## 12. 总结

这个简化方案具有以下特点：

1. **无缝兼容**: 保持原有接口签名完全不变
2. **简单映射**: 外部用户ID直接映射到内部User对象  
3. **最小改动**: 只需替换一个依赖注入函数
4. **随机凭证**: 内部用户名密码自动随机生成，无需管理
5. **降级支持**: 支持原生鉴权作为后备
6. **管理方便**: 提供注册和查询接口

**核心优势**：
- **完全透明**: 系统完全不知道用户来源，以为还是使用原生User对象
- **零维护**: 内部用户凭证自动生成，无需手动管理密码
- **简单注册**: 只需外部用户ID、邮箱、姓名三个字段即可完成注册
- **安全隔离**: 内部随机凭证确保外部用户无法直接登录内部系统

核心思路是**外部鉴权+内部转换**，让系统以为还是在使用原生的User对象，实现无缝集成。

## 13. 当前实现状态

### 13.1 已实现功能

✅ **核心鉴权逻辑**：
- `auth_converter.py` - 外部鉴权验证和用户转换
- `external_auth_client.py` - 外部鉴权服务客户端
- `dependencies.py` - FastAPI依赖注入集成

✅ **用户管理**：
- `user_service.py` - 外部用户服务
- `models.py` - 数据模型定义
- `registration_api.py` - 用户注册接口

✅ **配置集成**：
- 环境变量配置（`EXTERNAL_AUTH_ENABLED`, `EXTERNAL_AUTH_SERVICE_URL`）
- 与现有系统的无缝集成

✅ **多Header支持**：
- `Authorization: Bearer <token>`
- `X-Auth-Token: <token>` （推荐）
- `X-User-Token: <token>`

### 13.2 关键改进

🔧 **解决API Key冲突**：
- 使用自定义header（`X-Auth-Token`）避免JWT token被误认为API key
- 绕过原有的API key验证逻辑

🔧 **鉴权优先级**：
- 外部鉴权优先，失败时降级到原生鉴权
- 保持向后兼容性

🔧 **错误处理**：
- 外部服务不可用时的降级处理
- 完整的错误日志和监控

### 13.3 部署和测试

**环境配置**：
```bash
export EXTERNAL_AUTH_ENABLED=true
export EXTERNAL_AUTH_SERVICE_URL=http://172.16.0.14:8000/auth
```

**测试方法**：
```bash
# 使用自定义header避免API key冲突
curl -X GET "http://localhost:8888/user/file/token-estimate" \
  -H "X-Auth-Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

### 13.4 注意事项

⚠️ **外部服务依赖**：
- 需要确保外部鉴权服务可访问
- 实现合适的缓存和重试机制

⚠️ **网络配置**：
- 确保后端服务能访问外部鉴权服务
- 考虑代理和防火墙配置

⚠️ **监控和日志**：
- 监控外部服务调用成功率
- 记录鉴权失败和降级情况

### 13.5 下一步优化

🚀 **性能优化**：
- 改进缓存策略
- 实现批量token验证
- 添加健康检查端点

🚀 **安全增强**：
- 添加token签名验证
- 实现更细粒度的权限控制
- 添加审计日志

🚀 **运维支持**：
- 添加监控指标
- 实现配置热重载
- 提供调试工具