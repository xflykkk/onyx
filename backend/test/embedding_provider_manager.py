#!/usr/bin/env python3
"""
Embedding Provider Configuration Manager
用于管理 Onyx 中的 Embedding Provider 配置

测试文件路径：/Users/zhuxiaofeng/Github/onyx/backend/test/embedding_provider_manager.py
"""

import requests
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class EmbeddingProviderType(str, Enum):
    """支持的 Embedding 提供商类型"""
    OPENAI = "openai"
    COHERE = "cohere"
    VOYAGE = "voyage"
    GOOGLE = "google"
    LITELLM = "litellm"
    AZURE = "azure"


@dataclass
class EmbeddingProviderConfig:
    """Embedding Provider配置数据类"""
    provider_type: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    api_version: Optional[str] = None
    deployment_name: Optional[str] = None


@dataclass
class TestEmbeddingConfig:
    """测试 Embedding 配置数据类"""
    provider_type: str
    model_name: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    api_version: Optional[str] = None
    deployment_name: Optional[str] = None


class EmbeddingProviderManager:
    """
    Embedding Provider 配置管理器
    用于管理 embedding 模型的配置和测试
    """
    
    def __init__(self, base_url: str = "http://localhost:8080", admin_token: Optional[str] = None):
        """
        初始化 Embedding Provider 管理器
        
        Args:
            base_url: 后端服务的基础URL
            admin_token: 管理员认证token（如果需要）
        """
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 如果提供了认证token，添加到headers中
        if self.admin_token:
            self.headers["Authorization"] = f"Bearer {self.admin_token}"
    
    def list_embedding_providers(self) -> List[Dict[str, Any]]:
        """
        获取所有 Embedding Provider 列表
        
        Returns:
            Embedding Provider列表
        """
        url = f"{self.base_url}/admin/embedding/embedding-provider"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"获取 Embedding Provider 列表失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def create_or_update_embedding_provider(self, config: EmbeddingProviderConfig) -> Dict[str, Any]:
        """
        创建或更新 Embedding Provider
        
        Args:
            config: Embedding Provider 配置
            
        Returns:
            Provider信息
        """
        url = f"{self.base_url}/admin/embedding/embedding-provider"
        
        # 转换配置为请求数据
        payload = {
            "provider_type": config.provider_type,
            "api_key": config.api_key,
            "api_url": config.api_url,
            "api_version": config.api_version,
            "deployment_name": config.deployment_name,
        }
        
        # 移除None值
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # 发送创建/更新请求
        response = requests.put(
            url,
            json=payload,
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"创建/更新 Embedding Provider 失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def delete_embedding_provider(self, provider_type: str) -> bool:
        """
        删除指定的 Embedding Provider
        
        Args:
            provider_type: Provider 类型（如 "openai", "cohere" 等）
            
        Returns:
            删除是否成功
        """
        url = f"{self.base_url}/admin/embedding/embedding-provider/{provider_type}"
        
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code == 200:
            return True
        else:
            print(f"删除 Embedding Provider 失败: {response.status_code} - {response.text}")
            return False
    
    def test_embedding_provider(self, config: TestEmbeddingConfig) -> bool:
        """
        测试 Embedding Provider 配置
        
        Args:
            config: 测试配置
            
        Returns:
            测试是否成功
        """
        url = f"{self.base_url}/admin/embedding/test-embedding"
        
        # 构造测试请求数据
        payload = {
            "provider_type": config.provider_type,
            "model_name": config.model_name,
            "api_key": config.api_key,
            "api_url": config.api_url,
            "api_version": config.api_version,
            "deployment_name": config.deployment_name,
        }
        
        # 移除None值
        payload = {k: v for k, v in payload.items() if v is not None}
        
        print(f"   请求参数: {payload}")
        
        response = requests.post(
            url,
            json=payload,
            headers=self.headers
        )
        
        if response.status_code == 200:
            print(f"   ✓ 模型 '{config.model_name}' 测试成功")
            return True
        else:
            print(f"   ✗ 模型 '{config.model_name}' 测试失败: {response.status_code} - {response.text}")
            return False
    
    def list_embedding_models(self) -> List[Dict[str, Any]]:
        """
        获取所有 Embedding 模型列表
        
        Returns:
            Embedding 模型列表
        """
        url = f"{self.base_url}/admin/embedding"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"获取 Embedding 模型列表失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def delete_embedding_model(self, search_settings_id: int) -> bool:
        """
        删除指定的 Embedding 模型（通过 search_settings_id）
        
        Args:
            search_settings_id: 搜索设置ID
            
        Returns:
            删除是否成功
        """
        url = f"{self.base_url}/search-settings/delete-search-settings"
        
        payload = {
            "search_settings_id": search_settings_id
        }
        
        response = requests.delete(url, json=payload, headers=self.headers)
        
        if response.status_code == 200:
            return True
        else:
            print(f"删除 Embedding 模型失败: {response.status_code} - {response.text}")
            return False
    
    def get_current_active_embedding_model(self) -> Optional[Dict[str, Any]]:
        """
        获取当前活跃的 embedding 模型
        
        Returns:
            当前活跃的模型信息，如果没有则返回None
        """
        try:
            models = self.list_embedding_models()
            for model in models:
                if model.get('status') == 'PRESENT':
                    return model
            return None
        except Exception as e:
            print(f"✗ 获取活跃模型失败: {e}")
            return None
    
    def create_new_embedding_model(self, model_name: str, provider_type: str = "litellm") -> bool:
        """
        创建新的 embedding 模型配置
        
        Args:
            model_name: 模型名称
            provider_type: Provider 类型
            
        Returns:
            创建是否成功
        """
        url = f"{self.base_url}/search-settings/set-new-search-settings"
        
        payload = {
            "model_name": model_name,
            "model_dim": 1024,  # qwen3-embedding-0.6b 的维度是1024
            "normalize": True,
            "query_prefix": "",
            "passage_prefix": "",
            "provider_type": provider_type,
            "embedding_precision": "bfloat16",
            "multipass_indexing": True,
            "num_rerank": 5,
            "enable_contextual_rag": True,
            "index_name": None,  # 让系统自动生成索引名称
            "rerank_model_name": None,
            "rerank_api_url": None,
            "rerank_provider_type": None,
            "multilingual_expansion": []
        }
        
        print(f"   创建模型请求参数: {payload}")
        print(f"   请求URL: {url}")
        
        response = requests.post(url, json=payload, headers=self.headers)
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应内容: {response.text}")
        
        if response.status_code == 200:
            print(f"   ✓ 模型 '{model_name}' 创建成功")
            return True
        else:
            print(f"   ✗ 模型 '{model_name}' 创建失败: {response.status_code} - {response.text}")
            return False
    
    def cleanup_old_qwen_models(self, skip_active: bool = True) -> bool:
        """
        清理所有 qwen 相关的模型（包括 4b 和 0.6b）
        
        Args:
            skip_active: 是否跳过活跃状态的模型
            
        Returns:
            清理是否成功
        """
        try:
            models = self.list_embedding_models()
            old_models = []
            active_model = None
            
            # 找到所有包含 qwen 的模型
            for model in models:
                model_name = model.get('model_name', '')
                if 'qwen' in model_name.lower():
                    if model.get('status') == 'PRESENT':
                        active_model = model
                        if skip_active:
                            print(f"跳过活跃模型: {model_name} (ID: {model.get('id')})")
                            continue
                    old_models.append(model)
            
            if not old_models:
                print("✓ 没有找到需要清理的 qwen 模型")
                return True
            
            print(f"找到 {len(old_models)} 个需要清理的 qwen 模型:")
            for model in old_models:
                status_text = model.get('status') or 'None'
                is_active = " [活跃]" if model.get('status') == 'PRESENT' else ""
                print(f"  - 模型: {model.get('model_name')}, ID: {model.get('id')}, 状态: {status_text}{is_active}")
            
            if active_model and skip_active:
                print(f"\n⚠️ 检测到活跃模型: {active_model.get('model_name')} (ID: {active_model.get('id')})")
                print("   需要先设置新的默认模型，然后再清理旧模型")
                return False
            
            # 删除这些模型
            success_count = 0
            for model in old_models:
                model_id = model.get('id')
                model_name = model.get('model_name')
                
                if self.delete_embedding_model(model_id):
                    print(f"✓ 删除模型成功: {model_name} (ID: {model_id})")
                    success_count += 1
                else:
                    print(f"✗ 删除模型失败: {model_name} (ID: {model_id})")
            
            print(f"清理完成: 成功删除 {success_count}/{len(old_models)} 个模型")
            return success_count == len(old_models)
            
        except Exception as e:
            print(f"✗ 清理旧模型失败: {e}")
            return False
    
    def get_embedding_provider_by_type(self, provider_type: str) -> Optional[Dict[str, Any]]:
        """
        根据类型获取 Embedding Provider 信息
        
        Args:
            provider_type: Provider类型
            
        Returns:
            Provider信息，如果不存在则返回None
        """
        providers = self.list_embedding_providers()
        for provider in providers:
            if provider.get("provider_type") == provider_type:
                return provider
        return None
    
    def set_active_embedding_model(self, model_name: str) -> bool:
        """
        设置指定的 embedding 模型为当前活跃模型
        通过创建新的搜索设置来切换模型
        
        Args:
            model_name: 要激活的模型名称
            
        Returns:
            设置是否成功
        """
        try:
            # 1. 获取所有模型列表
            models = self.list_embedding_models()
            target_model = None
            
            # 2. 找到目标模型
            for model in models:
                if model.get('model_name') == model_name:
                    target_model = model
                    break
            
            if not target_model:
                print(f"✗ 未找到模型: {model_name}")
                return False
            
            # 3. 检查模型状态
            if target_model.get('status') == 'PRESENT':
                print(f"✓ 模型 '{model_name}' 已经是活跃状态")
                return True
            
            # 4. 使用 set-new-search-settings API 来创建新的活跃模型
            url = f"{self.base_url}/search-settings/set-new-search-settings"
            
            # 构造请求数据，使用目标模型的配置
            payload = {
                "model_name": target_model.get('model_name'),
                "model_dim": target_model.get('model_dim') or 1024,  # qwen3-embedding-0.6b 默认维度是1024
                "normalize": target_model.get('normalize', True),
                "query_prefix": target_model.get('query_prefix'),
                "passage_prefix": target_model.get('passage_prefix'),
                "provider_type": target_model.get('provider_type'),
                "embedding_precision": target_model.get('embedding_precision') or "bfloat16",
                "multipass_indexing": target_model.get('multipass_indexing', True),
                "num_rerank": target_model.get('num_rerank', 5),
                "enable_contextual_rag": target_model.get('enable_contextual_rag', True),
                "index_name": target_model.get('index_name'),  # 使用现有的索引名称
                "rerank_model_name": target_model.get('rerank_model_name'),
                "rerank_api_url": target_model.get('rerank_api_url'),
                "rerank_provider_type": target_model.get('rerank_provider_type'),
                "multilingual_expansion": target_model.get('multilingual_expansion', []),
                "background_reindex_enabled": False  # 不需要重新索引，立即切换
            }
            
            print(f"   激活模型请求参数: {payload}")
            print(f"   请求URL: {url}")
            
            response = requests.post(url, json=payload, headers=self.headers)
            
            print(f"   响应状态码: {response.status_code}")
            print(f"   响应内容: {response.text}")
            
            if response.status_code == 200:
                print(f"✓ 模型 '{model_name}' 激活成功")
                return True
            else:
                print(f"✗ 模型 '{model_name}' 激活失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 激活模型失败: {e}")
            return False


# 预定义的常用配置模板
class EmbeddingProviderTemplates:
    """预定义的 Embedding Provider 配置模板"""
    
    @staticmethod
    def create_openai_config(
        api_key: str,
        api_url: str = "http://172.16.0.120:4000/v1",
        api_version: Optional[str] = None
    ) -> EmbeddingProviderConfig:
        """
        创建 OpenAI 兼容的 Embedding Provider 配置
        
        Args:
            api_key: API密钥
            api_url: API基础URL
            api_version: API版本（可选）
            
        Returns:
            Embedding Provider配置
        """
        return EmbeddingProviderConfig(
            provider_type="openai",
            api_key=api_key,
            api_url=api_url,
            api_version=api_version
        )
    
    @staticmethod
    def create_test_config(
        provider_type: str,
        model_name: str,
        api_key: str,
        api_url: str = "http://172.16.0.120:4000/v1"
    ) -> TestEmbeddingConfig:
        """
        创建测试配置
        
        Args:
            provider_type: Provider类型
            model_name: 模型名称
            api_key: API密钥
            api_url: API基础URL
            
        Returns:
            测试配置
        """
        return TestEmbeddingConfig(
            provider_type=provider_type,
            model_name=model_name,
            api_key=api_key,
            api_url=api_url
        )


# 使用示例和测试脚本
if __name__ == "__main__":
    """
    Embedding Provider 管理脚本使用示例
    """
    print("=== Embedding Provider 管理工具 ===\n")
    
    # 创建管理器实例
    manager = EmbeddingProviderManager()
    
    try:
        # 第一步：列出当前所有 Embedding Providers
        print("1. 当前所有 Embedding Providers:")
        providers = manager.list_embedding_providers()
        for provider in providers:
            print(f"  - 类型: {provider.get('provider_type')}, API URL: {provider.get('api_url')}")
        
        # 第二步：列出当前所有 Embedding 模型及其详细信息
        print("\n2. 当前所有 Embedding 模型:")
        models = manager.list_embedding_models()
        for model in models:
            status_map = {
                'PRESENT': '活跃',
                'FUTURE': '待激活',
                'PAST': '已停用',
                None: '未就绪'
            }
            status = status_map.get(model.get('status'), '未知')
            
            print(f"  - 模型: {model.get('model_name', 'N/A')}, "
                  f"Provider: {model.get('provider_type', 'N/A')}, "
                  f"状态: {status}")
            
            # 打印详细配置信息
            print(f"    详细信息:")
            print(f"      ID: {model.get('id', 'N/A')}")
            print(f"      模型维度: {model.get('model_dim', 'N/A')}")
            print(f"      规范化: {model.get('normalize', 'N/A')}")
            print(f"      查询前缀: '{model.get('query_prefix', '')}'")
            print(f"      段落前缀: '{model.get('passage_prefix', '')}'")
            print(f"      索引名称: {model.get('index_name', 'N/A')}")
            if model.get('api_key'):
                print(f"      API密钥: {model.get('api_key')[:10]}...")
            if model.get('api_url'):
                print(f"      API URL: {model.get('api_url')}")
            if model.get('api_version'):
                print(f"      API版本: {model.get('api_version')}")
            print()
        
        # 第三步：检查是否有活跃的旧模型（先不清理，留到后面处理）
        print("\n3. 检查旧的 qwen3-embedding-4b 模型...")
        active_model = manager.get_current_active_embedding_model()
        if active_model and 'qwen3-embedding-4b' in active_model.get('model_name', ''):
            print(f"⚠️ 发现活跃的旧模型: {active_model.get('model_name')} (ID: {active_model.get('id')})")
            print("   将在设置新模型后清理")
        
        # 第四步：创建新的 OpenAI Embedding Provider 配置
        print("\n4. 创建新的 OpenAI Embedding Provider...")
        new_config = EmbeddingProviderTemplates.create_openai_config(
            api_key="sk-Zd7gzQGylVwOyUUMvOBhow",
            api_url="http://172.16.0.120:4000/v1/embeddings"
        )
        
        result = manager.create_or_update_embedding_provider(new_config)
        print("✓ OpenAI Embedding Provider 创建/更新成功")
        
        # 第五步：测试新的 embedding 模型配置
        print("\n5. 测试新的 embedding 模型: qwen3-embedding-0.6b")
        test_config = EmbeddingProviderTemplates.create_test_config(
            provider_type="litellm",
            model_name="openai/qwen3-embedding-0.6b",
            api_key="sk-Zd7gzQGylVwOyUUMvOBhow",
            api_url="http://172.16.0.120:4000/v1/embeddings"
        )
        
        test_success = manager.test_embedding_provider(test_config)
        if test_success:
            print("✓ Embedding 模型测试成功")
        else:
            print("✗ Embedding 模型测试失败")
        
        # 第六步：显示更新后的配置
        print("\n6. 更新后的 Embedding Providers:")
        providers = manager.list_embedding_providers()
        for provider in providers:
            print(f"  - 类型: {provider.get('provider_type')}, API URL: {provider.get('api_url')}")
        
        print("\n=== 配置完成 ===")
        print("\n💡 现在 embedding 模型应该使用 openai/qwen3-embedding-0.6b 而不是 qwen3-embedding-4b")
        
    except Exception as e:
        print(f"✗ 操作失败: {e}")


def delete_embedding_provider_by_type(provider_type: str = "openai"):
    """
    快速删除指定类型的 Embedding Provider
    
    Args:
        provider_type: Provider类型，默认为"openai"
    """
    print(f"=== 删除 '{provider_type}' Embedding Provider ===")
    
    manager = EmbeddingProviderManager()
    
    try:
        # 检查Provider是否存在
        provider = manager.get_embedding_provider_by_type(provider_type)
        if not provider:
            print(f"✗ 未找到类型为 '{provider_type}' 的 Embedding Provider")
            return False
        
        print(f"找到 Embedding Provider: {provider_type}")
        
        # 删除Provider
        if manager.delete_embedding_provider(provider_type):
            print(f"✓ 成功删除 '{provider_type}' Embedding Provider")
            return True
        else:
            print(f"✗ 删除失败")
            return False
            
    except Exception as e:
        print(f"✗ 操作失败: {e}")
        return False


def list_all_embedding_models():
    """
    列出所有 embedding 模型和当前活跃模型
    """
    print("=== 所有 Embedding 模型列表 ===")
    
    manager = EmbeddingProviderManager()
    
    try:
        # 1. 获取当前活跃模型
        print("1. 当前活跃的 embedding 模型:")
        active_model = manager.get_current_active_embedding_model()
        if active_model:
            print(f"   🟢 活跃模型: {active_model.get('model_name')} (ID: {active_model.get('id')})")
            print(f"      Provider: {active_model.get('provider_type')}")
            print(f"      维度: {active_model.get('model_dim')}")
            print(f"      索引: {active_model.get('index_name')}")
        else:
            print("   ❌ 没有找到活跃模型")
        
        # 2. 列出所有模型
        print("\n2. 所有 Embedding 模型:")
        models = manager.list_embedding_models()
        
        if not models:
            print("   没有找到任何 embedding 模型")
            return
        
        status_map = {
            'PRESENT': '🟢 活跃',
            'FUTURE': '🟡 待激活',
            'PAST': '🔴 已停用',
            None: '⚪ 未就绪'
        }
        
        for i, model in enumerate(models, 1):
            status = status_map.get(model.get('status'), '❓ 未知')
            print(f"   [{i}] {model.get('model_name', 'N/A')}")
            print(f"       状态: {status}")
            print(f"       Provider: {model.get('provider_type', 'N/A')}")
            print(f"       ID: {model.get('id', 'N/A')}")
            print(f"       维度: {model.get('model_dim', 'N/A')}")
            print(f"       索引: {model.get('index_name', 'N/A')}")
            if model.get('api_url'):
                print(f"       API URL: {model.get('api_url')}")
            print()
        
        # 3. 统计信息
        total_models = len(models)
        active_count = len([m for m in models if m.get('status') == 'PRESENT'])
        future_count = len([m for m in models if m.get('status') == 'FUTURE'])
        past_count = len([m for m in models if m.get('status') == 'PAST'])
        
        print(f"3. 统计信息:")
        print(f"   总模型数: {total_models}")
        print(f"   活跃模型: {active_count}")
        print(f"   待激活模型: {future_count}")
        print(f"   已停用模型: {past_count}")
        
    except Exception as e:
        print(f"✗ 获取模型列表失败: {e}")


def delete_all_qwen_models():
    """
    删除所有 qwen 相关的模型（包括活跃模型）
    """
    print("=== 删除所有 Qwen 模型 ===")
    
    manager = EmbeddingProviderManager()
    
    try:
        # 先显示当前状态
        print("1. 当前 Qwen 模型状态:")
        models = manager.list_embedding_models()
        qwen_models = [m for m in models if 'qwen' in m.get('model_name', '').lower()]
        
        if not qwen_models:
            print("   没有找到任何 qwen 模型")
            return True
        
        for model in qwen_models:
            status_text = model.get('status') or 'None'
            is_active = " [活跃]" if model.get('status') == 'PRESENT' else ""
            print(f"   - 模型: {model.get('model_name')}, ID: {model.get('id')}, 状态: {status_text}{is_active}")
        
        # 确认删除
        print(f"\n2. 将删除 {len(qwen_models)} 个 qwen 模型")
        response = input("确认删除所有 qwen 模型吗？(y/N): ")
        if response.lower() != 'y':
            print("取消删除操作")
            return False
        
        # 执行删除
        print("\n3. 正在删除 qwen 模型...")
        success = manager.cleanup_old_qwen_models(skip_active=False)
        
        if success:
            print("✓ 所有 qwen 模型删除成功")
        else:
            print("⚠️ 部分 qwen 模型删除失败")
        
        return success
        
    except Exception as e:
        print(f"✗ 删除失败: {e}")
        return False


def setup_qwen_embedding():
    """
    设置 qwen embedding 模型配置
    将 qwen3-embedding-4b 替换为 openai/qwen3-embedding-0.6b
    """
    print("=== 设置 Qwen Embedding 模型 ===")
    
    manager = EmbeddingProviderManager()
    
    try:
        # 1. 检查当前活跃模型
        print("1. 检查当前活跃的 embedding 模型...")
        active_model = manager.get_current_active_embedding_model()
        if active_model:
            print(f"当前活跃模型: {active_model.get('model_name')} (ID: {active_model.get('id')})")
        
        # 2. 创建新的 LiteLLM Provider 配置
        print("2. 创建新的 LiteLLM Embedding Provider 配置...")
        config = EmbeddingProviderConfig(
            provider_type="litellm",
            api_key="sk-Zd7gzQGylVwOyUUMvOBhow",
            api_url="http://172.16.0.120:4000/v1/embeddings"  # 使用完整的嵌入端点
        )
        
        result = manager.create_or_update_embedding_provider(config)
        print("✓ LiteLLM Embedding Provider 配置成功")
        
        # 3. 测试新模型
        print("3. 测试 qwen3-embedding-0.6b 模型...")
        test_config = EmbeddingProviderTemplates.create_test_config(
            provider_type="litellm",
            model_name="openai/qwen3-embedding-0.6b",
            api_key="sk-Zd7gzQGylVwOyUUMvOBhow",
            api_url="http://172.16.0.120:4000/v1/embeddings"
        )
        
        if not manager.test_embedding_provider(test_config):
            print("✗ 新的 embedding 模型测试失败")
            return False
        
        print("✓ 新的 embedding 模型测试成功")
        
        # 4. 创建新的默认 embedding 模型
        print("4. 创建新的默认 embedding 模型...")
        if manager.create_new_embedding_model("openai/qwen3-embedding-0.6b", "litellm"):
            print("✓ 新的默认 embedding 模型创建成功")
        else:
            print("✗ 新的默认 embedding 模型创建失败")
            return False
        
        # 5. 激活新的 embedding 模型
        print("5. 激活新的 qwen3-embedding-0.6b 模型...")
        if manager.set_active_embedding_model("openai/qwen3-embedding-0.6b"):
            print("✓ 新模型激活成功")
        else:
            print("✗ 新模型激活失败")
            return False
        
        # 6. 等待新模型成为活跃状态，然后清理旧模型
        print("6. 清理旧的 qwen3-embedding-4b 模型...")
        cleanup_success = manager.cleanup_old_qwen_models(skip_active=False)
        
        if cleanup_success:
            print("✓ 旧模型清理成功")
        else:
            print("⚠️ 部分旧模型清理失败，但不影响新模型使用")
        
        print("🎉 Qwen Embedding 模型配置完成！")
        return True
            
    except Exception as e:
        print(f"✗ 配置失败: {e}")
        return False


# 如果只想设置 qwen embedding，取消下面的注释：
if __name__ == "__main__":
    # 重新设置 qwen embedding 模型
    setup_qwen_embedding()
    
    # 显示最终结果
    print("\n" + "="*50)

    print("最终的模型列表:")
    list_all_embedding_models()