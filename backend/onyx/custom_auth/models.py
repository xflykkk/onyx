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
    user_id: Optional[str] = None
    email: Optional[str] = None

class ExternalAuthResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None