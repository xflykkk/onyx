#!/usr/bin/env python3
"""
直接测试 embedding 配置，绕过可能的 API key 问题
"""

import os
import sys
sys.path.insert(0, '/Users/zhuxiaofeng/Github/onyx/backend')

from sqlalchemy.orm import Session
from onyx.db.engine.sql_engine import get_session_factory
from onyx.db.llm import remove_embedding_provider, upsert_cloud_embedding_provider
from onyx.server.manage.embedding.models import CloudEmbeddingProviderCreationRequest
from shared_configs.enums import EmbeddingProvider

def clean_and_setup_embedding():
    """清理旧配置并设置新的 embedding provider"""
    
    session_factory = get_session_factory()
    
    with session_factory() as db_session:
        # 1. 删除现有的 litellm provider
        print("1. 删除现有的 LiteLLM embedding provider...")
        try:
            remove_embedding_provider(db_session, EmbeddingProvider.LITELLM)
            db_session.commit()
            print("✓ 删除成功")
        except Exception as e:
            print(f"✗ 删除失败: {e}")
            db_session.rollback()
        
        # 2. 创建新的 provider
        print("\n2. 创建新的 LiteLLM embedding provider...")
        try:
            provider_request = CloudEmbeddingProviderCreationRequest(
                provider_type=EmbeddingProvider.LITELLM,
                api_key="sk-Zd7gzQGylVwOyUUMvOBhow",
                api_url="http://172.16.0.120:4000/v1",
                api_version=None,
                deployment_name=None
            )
            
            result = upsert_cloud_embedding_provider(db_session, provider_request)
            print(f"✓ 创建成功: {result}")
            
            # 验证 API key 是否正确存储
            print(f"  Provider type: {result.provider_type}")
            print(f"  API URL: {result.api_url}")
            print(f"  API Key (前4位): {result.api_key[:4] if result.api_key else 'None'}...")
            
        except Exception as e:
            print(f"✗ 创建失败: {e}")
            db_session.rollback()

if __name__ == "__main__":
    clean_and_setup_embedding()