#!/usr/bin/env python3
"""
检查存储的 embedding provider API key
"""

import os
import sys
sys.path.insert(0, '/Users/zhuxiaofeng/Github/onyx/backend')

from sqlalchemy import select
from onyx.db.engine.sql_engine import get_session, SqlEngine
from onyx.db.models import CloudEmbeddingProvider as CloudEmbeddingProviderModel
from onyx.db.models import LLMProvider, ModelConfiguration
from onyx.db.llm import fetch_existing_embedding_providers
from shared_configs.enums import EmbeddingProvider

def check_embedding_api_keys():
    """检查所有 embedding provider 的 API key"""
    
    for db_session in get_session():
        print("=== 检查 Embedding Provider API Keys ===\n")
        
        # 方法1：使用 fetch_existing_embedding_providers
        print("1. 使用 fetch_existing_embedding_providers 函数:")
        providers = fetch_existing_embedding_providers(db_session)
        for provider in providers:
            print(f"  Provider: {provider.provider_type}")
            print(f"  API URL: {provider.api_url}")
            print(f"  API Key: {provider.api_key}")
            print(f"  API Key 长度: {len(provider.api_key) if provider.api_key else 0}")
            print(f"  API Key 类型: {type(provider.api_key)}")
            print()
        
        # 方法2：直接查询数据库
        print("\n2. 直接查询数据库:")
        stmt = select(CloudEmbeddingProviderModel)
        results = db_session.execute(stmt).scalars().all()
        
        for provider in results:
            print(f"  Provider: {provider.provider_type}")
            print(f"  API URL: {provider.api_url}")
            print(f"  API Key (原始): {provider.api_key}")
            print(f"  API Key 长度: {len(provider.api_key) if provider.api_key else 0}")
            print(f"  API Key 类型: {type(provider.api_key)}")
            
            # 检查是否是我们期望的 key
            expected_key = "sk-Zd7gzQGylVwOyUUMvOBhow"
            if provider.api_key:
                if provider.api_key == expected_key:
                    print("  ✓ API Key 匹配预期值")
                else:
                    print("  ✗ API Key 不匹配预期值")
                    print(f"    期望: {expected_key}")
                    print(f"    实际: {provider.api_key}")
            print()
        
        # 方法3：专门检查 LITELLM provider
        print("\n3. 专门检查 LITELLM provider:")
        litellm_provider = db_session.scalar(
            select(CloudEmbeddingProviderModel).where(
                CloudEmbeddingProviderModel.provider_type == EmbeddingProvider.LITELLM
            )
        )
        
        if litellm_provider:
            print(f"  找到 LITELLM provider")
            print(f"  API Key: {litellm_provider.api_key}")
            print(f"  API URL: {litellm_provider.api_url}")
            
            # 测试解密是否正常工作
            if litellm_provider.api_key and litellm_provider.api_key.startswith("sk-"):
                print("  ✓ API Key 格式正确 (以 'sk-' 开头)")
            else:
                print("  ✗ API Key 格式不正确")
        else:
            print("  未找到 LITELLM provider")

def check_llm_providers():
    """检查所有 LLM provider 的配置和 API key"""
    
    for db_session in get_session():
        print("\n=== 检查 LLM Provider 配置 ===\n")
        
        # 查询所有 LLM providers
        stmt = select(LLMProvider)
        llm_providers = db_session.execute(stmt).scalars().all()
        
        if not llm_providers:
            print("未找到任何 LLM Provider")
            return
            
        for provider in llm_providers:
            print(f"Provider ID: {provider.id}")
            print(f"Provider Name: {provider.name}")
            print(f"Provider Type: {provider.provider}")
            print(f"API Key: {provider.api_key}")
            print(f"API Key 长度: {len(provider.api_key) if provider.api_key else 0}")
            print(f"API Base: {provider.api_base}")
            print(f"API Version: {provider.api_version}")
            print(f"Default Model: {provider.default_model_name}")
            print(f"Fast Default Model: {provider.fast_default_model_name}")
            print(f"Deployment Name: {provider.deployment_name}")
            print(f"Is Default Provider: {provider.is_default_provider}")
            print(f"Is Default Vision Provider: {provider.is_default_vision_provider}")
            print(f"Default Vision Model: {provider.default_vision_model}")
            print(f"Is Public: {provider.is_public}")
            
            if provider.custom_config:
                print("Custom Config:")
                for key, value in provider.custom_config.items():
                    # 隐藏敏感信息
                    if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
                        masked_value = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
                        print(f"  {key}: {masked_value}")
                    else:
                        print(f"  {key}: {value}")
            
            # 查询关联的模型配置
            model_configs = db_session.execute(
                select(ModelConfiguration).where(
                    ModelConfiguration.llm_provider_id == provider.id
                )
            ).scalars().all()
            
            if model_configs:
                print("Associated Models:")
                for model_config in model_configs:
                    print(f"  - {model_config.name}")
                    print(f"    Visible: {model_config.is_visible}")
                    print(f"    Max Input Tokens: {model_config.max_input_tokens}")
            
            print("-" * 60)

def check_all_providers():
    """检查所有类型的 provider"""
    print("=== 完整的 Provider 检查报告 ===")
    check_embedding_api_keys()
    check_llm_providers()

if __name__ == "__main__":
    # 初始化数据库引擎
    SqlEngine.init_engine(pool_size=5, max_overflow=10)
    check_all_providers()