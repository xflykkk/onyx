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
                print(f"[EXTERNAL_AUTH] Cache hit for token: {cache_key}")
                logger.debug(f"Cache hit for token: {cache_key}")
                return ExternalAuthResponse(**cached_data)
        
        # 调用外部服务
        print(f"[EXTERNAL_AUTH] Starting external auth call...")
        print(f"[EXTERNAL_AUTH] Service URL: {self.service_url}")
        print(f"[EXTERNAL_AUTH] Token (first 10 chars): {auth_token[:10]}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "token": auth_token
                }
                
                print(f"[EXTERNAL_AUTH] Request URL: {self.service_url}/auth/verify_token")
                print(f"[EXTERNAL_AUTH] Request headers: {headers}")
                print(f"[EXTERNAL_AUTH] Request payload: {payload}")
                
                async with session.post(
                    f"{self.service_url}/auth/verify_token",
                    json=payload,
                    headers=headers,
                    timeout=5
                ) as response:
                    print(f"[EXTERNAL_AUTH] Response status: {response.status}")
                    print(f"[EXTERNAL_AUTH] Response headers: {dict(response.headers)}")
                    
                    response_text = await response.text()
                    print(f"[EXTERNAL_AUTH] Response body: {response_text}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"[EXTERNAL_AUTH] Parsed JSON data: {data}")
                        
                        # 根据实际API响应格式解析
                        auth_response = ExternalAuthResponse(
                            success=True,
                            user_id=data.get("ext_user_id"),
                            email=data.get("email")
                        )
                        print(f"[EXTERNAL_AUTH] Created auth response: {auth_response}")
                        
                        # 缓存结果5分钟
                        self._cache[cache_key] = (
                            auth_response.dict(), 
                            datetime.now() + timedelta(minutes=5)
                        )
                        print(f"[EXTERNAL_AUTH] Cached response for key: {cache_key}")
                        
                        return auth_response
                    
                    elif response.status == 401:
                        print(f"[EXTERNAL_AUTH] Token validation failed: 401 Unauthorized")
                        logger.warning(f"Token validation failed: 401 Unauthorized")
                        return None
                    else:
                        print(f"[EXTERNAL_AUTH] Unexpected response status: {response.status}")
                        logger.warning(f"External auth unexpected status: {response.status}")
                        return None
        
        except Exception as e:
            print(f"[EXTERNAL_AUTH] Exception occurred: {str(e)}")
            print(f"[EXTERNAL_AUTH] Exception type: {type(e).__name__}")
            logger.error(f"External auth service call failed: {e}")
        
        print(f"[EXTERNAL_AUTH] Returning None (auth failed)")
        return None

# 全局实例  
try:
    from onyx.configs.app_configs import EXTERNAL_AUTH_SERVICE_URL
except ImportError:
    # 防止循环导入，在模块内部延迟导入
    EXTERNAL_AUTH_SERVICE_URL = None
external_auth_client = ExternalAuthClient(
    service_url=EXTERNAL_AUTH_SERVICE_URL or "http://172.16.0.14:8000"
)