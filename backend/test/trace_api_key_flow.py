#!/usr/bin/env python3
"""
追踪 embedding 模型请求时 API key 的完整处理流程
"""

import sys
import os
sys.path.insert(0, '/Users/zhuxiaofeng/Github/onyx/backend')

from onyx.db.engine.sql_engine import get_session, SqlEngine
from onyx.db.models import CloudEmbeddingProvider as CloudEmbeddingProviderModel
from onyx.db.llm import fetch_existing_embedding_providers
from shared_configs.enums import EmbeddingProvider

def trace_api_key_processing():
    """
    追踪 qwen3-embedding-0.6b 模型请求时 API key 的处理流程
    """
    print("=== Embedding API Key 处理流程追踪 ===\n")
    
    # 步骤1：从数据库获取 embedding provider 配置
    print("步骤1: 从数据库获取 Embedding Provider 配置")
    print("=" * 50)
    
    for db_session in get_session():
        # 获取 LITELLM provider（这是 qwen3-embedding-0.6b 使用的）
        providers = fetch_existing_embedding_providers(db_session)
        litellm_provider = None
        
        for provider in providers:
            if provider.provider_type == EmbeddingProvider.LITELLM:
                litellm_provider = provider
                break
        
        if not litellm_provider:
            print("❌ 未找到 LITELLM provider")
            return
        
        print(f"✅ 找到 LITELLM Provider:")
        print(f"   - Provider Type: {litellm_provider.provider_type}")
        print(f"   - API URL: {litellm_provider.api_url}")
        print(f"   - API Key (加密): {litellm_provider.api_key}")
        print(f"   - API Key 长度: {len(litellm_provider.api_key) if litellm_provider.api_key else 0}")
        
        # 这里 API Key 是加密状态（如果设置了 ENCRYPTION_KEY_SECRET）
        encrypted_api_key = litellm_provider.api_key
        
        print(f"\n数据库中存储的 API Key: {encrypted_api_key}")
        print("📝 说明: 这是在数据库中存储的加密形式")
        break
    
    # 步骤2：模型初始化时的 API Key 处理
    print(f"\n步骤2: EmbeddingModel 初始化")
    print("=" * 50)
    print("在 onyx/natural_language_processing/search_nlp_models.py 中:")
    print("class EmbeddingModel:")
    print("    def __init__(self, ...")
    print("        self.api_key = api_key  # 这里接收解密后的 API key")
    print("        self.provider_type = provider_type")
    print("")
    print("📝 说明: 在这一步，API key 已经被解密为明文")
    
    # 步骤3：构建 EmbedRequest
    print(f"\n步骤3: 构建 EmbedRequest")
    print("=" * 50)
    print("在模型处理文本时，会构建 EmbedRequest:")
    print("embed_request = EmbedRequest(")
    print("    model_name=self.model_name,  # 'openai/qwen3-embedding-0.6b'")
    print("    texts=text_batch,")
    print("    api_key=self.api_key,        # 明文 API key")
    print("    provider_type=self.provider_type,  # EmbeddingProvider.LITELLM")
    print("    api_url=self.api_url,        # 'http://172.16.0.120:4000/v1'")
    print("    ...)")
    print("")
    print("📝 说明: API key 以明文形式传递给 model server")
    
    # 步骤4：Model Server 处理
    print(f"\n步骤4: Model Server 处理 (encoders.py)")
    print("=" * 50)
    print("在 model_server/encoders.py 中:")
    print("async def route_bi_encoder_embed(embed_request: EmbedRequest):")
    print("    # 调用 embed_text 函数")
    print("    await embed_text(")
    print("        api_key=embed_request.api_key,  # 明文 API key")
    print("        provider_type=embed_request.provider_type,")
    print("        ...)")
    print("")
    
    # 步骤5：CloudEmbedding 初始化
    print(f"\n步骤5: CloudEmbedding 初始化")
    print("=" * 50)
    print("async with CloudEmbedding(")
    print("    api_key=api_key,           # 明文 API key")
    print("    provider=provider_type,    # EmbeddingProvider.LITELLM")
    print("    api_url=api_url,          # 'http://172.16.0.120:4000/v1'")
    print(") as cloud_model:")
    print("")
    print("在 CloudEmbedding.__init__ 中:")
    print("    self.api_key = api_key")
    print("    self.sanitized_api_key = api_key[:4] + '********' + api_key[-4:]")
    print("")
    print("📝 说明: API key 存储为明文，创建脱敏版本用于日志")
    
    # 步骤6：LiteLLM 请求
    print(f"\n步骤6: 发送 LiteLLM 请求")
    print("=" * 50)
    print("在 CloudEmbedding._embed_litellm_proxy 方法中:")
    print("headers = {}")
    print("if self.api_key:")
    print("    headers['Authorization'] = f'Bearer {self.api_key}'")
    print("")
    print("response = await self.http_client.post(")
    print("    self.api_url,  # 'http://172.16.0.120:4000/v1'")
    print("    json={")
    print("        'model': model_name,  # 'openai/qwen3-embedding-0.6b'")
    print("        'input': texts,")
    print("    },")
    print("    headers=headers  # {'Authorization': 'Bearer sk-Zd7gzQGylVwOyUUMvOBhow'}")
    print(")")
    print("")
    print("📝 说明: 最终发送给 LiteLLM 服务器的是明文 API key")
    
    # 步骤7：总结
    print(f"\n🎯 总结：API Key 处理流程")
    print("=" * 50)
    print("1. 数据库存储: 加密形式 (如果设置了 ENCRYPTION_KEY_SECRET)")
    print("2. 从数据库读取: 自动解密为明文")
    print("3. EmbeddingModel: 明文 API key")
    print("4. EmbedRequest: 明文 API key")
    print("5. CloudEmbedding: 明文 API key")
    print("6. HTTP 请求: Authorization: Bearer <明文_API_key>")
    print("")
    print("🔑 对于 qwen3-embedding-0.6b 模型:")
    print(f"   - 数据库中: {encrypted_api_key}")
    print("   - 实际请求: Authorization: Bearer sk-Zd7gzQGylVwOyUUMvOBhow")
    print("")
    print("⚠️  重要发现:")
    print("   - API key 在传输过程中是明文")
    print("   - 只有在数据库存储时才加密")
    print("   - 发送给外部服务时使用明文 Bearer token")

if __name__ == "__main__":
    # 初始化数据库引擎
    SqlEngine.init_engine(pool_size=5, max_overflow=10)
    trace_api_key_processing()