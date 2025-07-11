"""
LiteLLM Provider Configuration Manager
用于管理 Onyx 中的 LLM Provider 配置

测试文件路径：/Users/zhuxiaofeng/Github/onyx/backend/test/llm_provider_manager.py
"""

import requests
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ProviderType(str, Enum):
    """支持的 LLM 提供商类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    BEDROCK = "bedrock"
    VERTEX_AI = "vertex_ai"


@dataclass
class ModelConfiguration:
    """模型配置数据类"""
    name: str
    is_visible: bool = True
    max_input_tokens: Optional[int] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None


@dataclass
class LLMProviderConfig:
    """LLM Provider配置数据类"""
    name: str
    provider: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    custom_config: Optional[Dict[str, str]] = None
    default_model_name: str = "gpt-3.5-turbo"
    fast_default_model_name: Optional[str] = None
    deployment_name: Optional[str] = None
    is_public: bool = True
    groups: List[int] = None
    default_vision_model: Optional[str] = None
    model_configurations: List[ModelConfiguration] = None
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.model_configurations is None:
            self.model_configurations = []


class LLMProviderManager:
    """
    LLM Provider 配置管理器
    用于管理 litellm 模型的配置和测试
    """
    
    def __init__(self, base_url: str = "http://localhost:8080", admin_token: Optional[str] = None):
        """
        初始化LLM Provider管理器
        
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
    
    def create_provider(self, config: LLMProviderConfig) -> Dict[str, Any]:
        """
        创建新的LLM Provider
        
        Args:
            config: LLM Provider配置
            
        Returns:
            创建的Provider信息
        """
        url = f"{self.base_url}/admin/llm/provider"
        
        # 转换配置为请求数据
        payload = self._config_to_payload(config)
        
        # 发送创建请求
        response = requests.put(
            url,
            params={"is_creation": True},
            json=payload,
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"创建Provider失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def update_provider(self, config: LLMProviderConfig) -> Dict[str, Any]:
        """
        更新现有的LLM Provider
        
        Args:
            config: LLM Provider配置
            
        Returns:
            更新后的Provider信息
        """
        url = f"{self.base_url}/admin/llm/provider"
        
        # 转换配置为请求数据
        payload = self._config_to_payload(config)
        
        # 发送更新请求
        response = requests.put(
            url,
            params={"is_creation": False},
            json=payload,
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"更新Provider失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def test_provider(self, config: LLMProviderConfig) -> bool:
        """
        测试LLM Provider配置
        
        Args:
            config: LLM Provider配置
            
        Returns:
            测试是否成功
        """
        url = f"{self.base_url}/admin/llm/test"
        
        # 构造测试请求数据
        payload = {
            "name": config.name,
            "provider": config.provider,
            "api_key": config.api_key,
            "api_base": config.api_base,
            "api_version": config.api_version,
            "custom_config": config.custom_config,
            "default_model_name": config.default_model_name,
            "fast_default_model_name": config.fast_default_model_name,
            "deployment_name": config.deployment_name,
            "model_configurations": [asdict(mc) for mc in config.model_configurations],
            "api_key_changed": True
        }
        
        response = requests.post(
            url,
            json=payload,
            headers=self.headers
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"测试失败: {response.status_code} - {response.text}")
            return False
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """
        获取所有LLM Provider列表
        
        Returns:
            Provider列表
        """
        url = f"{self.base_url}/admin/llm/provider"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"获取Provider列表失败: {response.status_code} - {response.text}")
        
        return response.json()
    
    def delete_provider(self, provider_id: int) -> bool:
        """
        删除指定的LLM Provider
        
        Args:
            provider_id: Provider ID
            
        Returns:
            删除是否成功
        """
        url = f"{self.base_url}/admin/llm/provider/{provider_id}"
        
        response = requests.delete(url, headers=self.headers)
        
        if response.status_code == 200:
            return True
        else:
            print(f"删除Provider失败: {response.status_code} - {response.text}")
            return False
    
    def set_default_provider(self, provider_id: int, default_model: str = None, fast_model: str = None) -> bool:
        """
        设置指定Provider为默认Provider，并可选设置默认模型和快速模型
        
        Args:
            provider_id: Provider ID
            default_model: 默认模型名称（可选）
            fast_model: 快速模型名称（可选）
            
        Returns:
            设置是否成功
        """
        # 先设置为默认Provider
        url = f"{self.base_url}/admin/llm/provider/{provider_id}/default"
        response = requests.post(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"设置默认Provider失败: {response.status_code} - {response.text}")
            return False
        
        # 如果需要更新模型配置，调用更新API
        if default_model or fast_model:
            provider = self.get_provider_by_id(provider_id)
            if provider:
                config = self._provider_to_config(provider)
                if default_model: config.default_model_name = default_model
                if fast_model: config.fast_default_model_name = fast_model
                self.update_provider(config)
        
        return True
    
    def set_default_vision_provider(self, provider_id: int, vision_model: Optional[str] = None) -> bool:
        """
        设置指定Provider为默认视觉Provider
        
        Args:
            provider_id: Provider ID
            vision_model: 视觉模型名称
            
        Returns:
            设置是否成功
        """
        url = f"{self.base_url}/admin/llm/provider/{provider_id}/default-vision"
        params = {}
        if vision_model:
            params["vision_model"] = vision_model
        
        response = requests.post(url, params=params, headers=self.headers)
        
        if response.status_code == 200:
            return True
        else:
            print(f"设置默认视觉Provider失败: {response.status_code} - {response.text}")
            return False
    
    def get_provider_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取Provider信息
        
        Args:
            name: Provider名称
            
        Returns:
            Provider信息，如果不存在则返回None
        """
        providers = self.list_providers()
        for provider in providers:
            if provider.get("name") == name:
                return provider
        return None
    
    def get_provider_by_id(self, provider_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取Provider信息"""
        providers = self.list_providers()
        for provider in providers:
            if provider.get("id") == provider_id:
                return provider
        return None
    
    def _provider_to_config(self, provider: Dict[str, Any], original_api_key: str = None) -> LLMProviderConfig:
        """将Provider字典转换为配置对象"""
        return LLMProviderConfig(
            name=provider.get("name"),
            provider=provider.get("provider"),
            api_key=original_api_key or "sk-Zd7gzQGylVwOyUUMvOBhow",  # 🔑 使用原始API密钥
            api_base=provider.get("api_base"),
            api_version=provider.get("api_version"),
            custom_config=provider.get("custom_config"),
            default_model_name=provider.get("default_model_name"),
            fast_default_model_name=provider.get("fast_default_model_name"),
            deployment_name=provider.get("deployment_name"),
            is_public=provider.get("is_public", True),
            groups=provider.get("groups", [])
        )
    
    def create_or_update_provider(self, config: LLMProviderConfig) -> Dict[str, Any]:
        """
        创建或更新Provider（如果存在则更新，否则创建）
        
        Args:
            config: LLM Provider配置
            
        Returns:
            Provider信息
        """
        existing = self.get_provider_by_name(config.name)
        
        if existing:
            print(f"Provider '{config.name}' 已存在，执行更新操作")
            return self.update_provider(config)
        else:
            print(f"Provider '{config.name}' 不存在，执行创建操作")
            return self.create_provider(config)
    
    def _config_to_payload(self, config: LLMProviderConfig) -> Dict[str, Any]:
        """
        将配置对象转换为API请求数据
        
        Args:
            config: LLM Provider配置
            
        Returns:
            API请求数据
        """
        payload = {
            "name": config.name,
            "provider": config.provider,
            "api_key": config.api_key,
            "api_base": config.api_base,
            "api_version": config.api_version,
            "custom_config": config.custom_config,
            "default_model_name": config.default_model_name,
            "fast_default_model_name": config.fast_default_model_name,
            "deployment_name": config.deployment_name,
            "is_public": config.is_public,
            "groups": config.groups,
            "default_vision_model": config.default_vision_model,
            "model_configurations": [asdict(mc) for mc in config.model_configurations],
            "api_key_changed": True  # 🔑 关键修复：确保使用原始API密钥而不是加密后的密钥
        }
        
        # 移除None值
        return {k: v for k, v in payload.items() if v is not None}

    def configure_llm_models(self, provider_name: str, default_model: str, fast_model: str = None) -> bool:
        """
        专门配置指定 Provider 的 LLM 模型配置
        
        Args:
            provider_name: Provider 名称
            default_model: 默认模型名称
            fast_model: 快速模型名称（可选）
            
        Returns:
            配置是否成功
        """
        try:
            # 获取现有 Provider
            provider = self.get_provider_by_name(provider_name)
            if not provider:
                print(f"✗ 未找到名为 '{provider_name}' 的 Provider")
                return False
            
            print(f"🔧 配置 Provider '{provider_name}' 的 LLM 模型...")
            print(f"  默认模型: {default_model}")
            if fast_model:
                print(f"  快速模型: {fast_model}")
            
            # 转换为配置对象，确保使用原始API密钥
            config = self._provider_to_config(provider, "sk-Zd7gzQGylVwOyUUMvOBhow")
            config.default_model_name = default_model
            if fast_model:
                config.fast_default_model_name = fast_model
            
            # 确保模型配置包含这些模型
            model_names = {default_model}
            if fast_model:
                model_names.add(fast_model)
            
            # 更新或添加模型配置
            existing_models = {mc.name for mc in config.model_configurations}
            for model_name in model_names:
                if model_name not in existing_models:
                    config.model_configurations.append(
                        ModelConfiguration(name=model_name, is_visible=True, max_input_tokens=8192,api_key=config.api_key,api_base=config.api_base)
                    )
            
            # 更新 Provider
            result = self.update_provider(config)
            print(f"✓ LLM 模型配置成功")
            
            # 设置为默认 Provider（确保系统使用这个配置）
            provider_id = result.get('id')
            if self.set_default_provider(provider_id):
                print(f"✓ 已设置为默认 Provider")
            
            return True
            
        except Exception as e:
            print(f"✗ LLM 模型配置失败: {e}")
            return False

    def test_default_provider_config(self) -> bool:
        """
        测试当前默认 Provider 的配置是否正常
        
        Returns:
            测试是否成功
        """
        url = f"{self.base_url}/admin/llm/test/default"
        
        try:
            response = requests.post(url, headers=self.headers)
            
            if response.status_code == 200:
                print("✓ 默认 Provider 配置测试成功")
                return True
            else:
                print(f"✗ 默认 Provider 配置测试失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 测试默认 Provider 配置时出错: {e}")
            return False

    def test_fast_model_config(self) -> bool:
        """
        测试快速模型的配置是否正常
        
        Returns:
            测试是否成功
        """
        try:
            # 获取默认Provider信息
            providers = self.list_providers()
            default_provider = None
            for p in providers:
                if p.get('is_default_provider'):
                    default_provider = p
                    break
            
            if not default_provider:
                print("✗ 未找到默认 Provider")
                return False
            
            fast_model = default_provider.get('fast_default_model_name')
            if not fast_model:
                print("✗ 默认 Provider 没有配置快速模型")
                return False
            
            print(f"🚀 测试快速模型: {fast_model}")
            
            # 构造快速模型测试请求
            test_config = self._provider_to_config(default_provider, "sk-Zd7gzQGylVwOyUUMvOBhow")
            test_config.default_model_name = fast_model  # 临时将快速模型设为默认模型进行测试
            
            # 测试快速模型
            if self.test_provider(test_config):
                print("✓ 快速模型配置测试成功")
                return True
            else:
                print("✗ 快速模型配置测试失败")
                return False
                
        except Exception as e:
            print(f"✗ 测试快速模型配置时出错: {e}")
            return False


    def delete_llm_provider_by_name(self, provider_name: str) -> bool:
        """
        根据名称删除LLM Provider
        
        Args:
            provider_name: Provider名称
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 使用现有的方法获取provider
            target_provider = self.get_provider_by_name(provider_name)
            
            if target_provider:
                provider_id = target_provider.get("id")
                print(f"找到要删除的 Provider: {provider_name} (ID: {provider_id})")
                return self.delete_provider(provider_id)  # 使用现有的delete_provider方法
            else:
                print(f"✗ 未找到名为 '{provider_name}' 的 LLM Provider")
                return False
                
        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            return False


# 预定义的常用配置模板
class LLMProviderTemplates:
    """预定义的LLM Provider配置模板"""
    
    @staticmethod
    def create_custom_openai_config(
        name: str,
        api_key: str,
        api_base: str,
        model_name: str,
        fast_model_name: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        max_tokens: int = 4096
    ) -> LLMProviderConfig:
        """
        创建自定义OpenAI兼容的配置
        
        Args:
            name: Provider名称
            api_key: API密钥
            api_base: API基础URL
            model_name: 模型名称
            fast_model_name: 快速模型名称（可选）
            custom_headers: 自定义请求头
            max_tokens: 最大token数
            
        Returns:
            LLM Provider配置
        """
        model_configs = [
            ModelConfiguration(name=model_name, is_visible=True, max_input_tokens=max_tokens)
        ]
        
        if fast_model_name:
            model_configs.append(
                ModelConfiguration(name=fast_model_name, is_visible=True, max_input_tokens=max_tokens)
            )
        
        return LLMProviderConfig(
            name=name,
            provider="openai",
            api_key=api_key,
            api_base=api_base,
            custom_config=custom_headers,
            default_model_name=model_name,
            fast_default_model_name=fast_model_name,
            model_configurations=model_configs
        )

# 使用示例和测试脚本
if __name__ == "__main__":
    """
    LLM Provider 管理脚本使用示例
    """
    print("=== LLM Provider 管理工具 ===\n")
    
    # 创建管理器实例
    manager = LLMProviderManager()
    
    # 🔧 诊断 fast_llm 配置问题
    providers = manager.list_providers()
    for p in providers:
        if p.get('is_default_provider'): 
            print(f"默认Provider: {p.get('name')}, fast_model: {p.get('fast_default_model_name')}")
            print(f"默认Provider: {p.get('default_model_name')}")
    
    # 删除包含 qwen3-0-6b 的旧配置
    print("1. 清理旧的 qwen3-0-6b 配置...")
    providers = manager.list_providers()
    for p in providers:
        if p.get('fast_default_model_name') == 'qwen3-0-6b':
            manager.delete_provider(p.get('id'))
            print(f"✓ 删除旧配置: {p.get('name')} (ID: {p.get('id')})")
            break
    else:
        print("✓ 未找到需要清理的配置")
    
    # 第二步：创建基础 Provider
    print("\n2. 创建基础 OpenAI 兼容 Provider...")
    base_config = LLMProviderTemplates.create_custom_openai_config(
        name="openai",
        api_key="sk-Zd7gzQGylVwOyUUMvOBhow", 
        api_base="http://172.16.0.120:4000/v1",
        model_name="qwen/qwen3-30b",
    )
    
    try:
        result = manager.create_or_update_provider(base_config)
        print("✓ 基础 Provider 创建成功")
        
        # 第三步：专门配置 LLM 模型
        print("\n3. 专门配置 LLM 模型...")
        if manager.configure_llm_models(
            provider_name="openai",
            default_model="qwen/qwen3-30b", 
            fast_model="openai/qwen3-0-6b"
        ):
            print("✓ LLM 模型配置成功")
            
            # 第四步：测试默认配置
            print("\n4. 测试默认 Provider 配置...")
            default_test_success = manager.test_default_provider_config()
            
            # 第五步：测试快速模型配置
            print("\n5. 测试快速模型配置...")
            fast_test_success = manager.test_fast_model_config()
            
            if default_test_success and fast_test_success:
                print("\n🎉 所有模型测试通过！")
            else:
                print("\n⚠️ 部分测试失败，请检查配置")
        else:
            print("✗ LLM 模型配置失败")
            
    except Exception as e:
        print(f"✗ Provider 配置失败: {e}")
    
    # 列出所有providers
    print("\n6. 当前所有 LLM Providers:")
    try:
        providers = manager.list_providers()
        for provider in providers:
            is_default = provider.get('is_default_provider', False)
            default_mark = " [默认]" if is_default else ""
            print(f"  - ID: {provider.get('id')}, 名称: {provider.get('name')}{default_mark}, "
                  f"Provider: {provider.get('provider')}, "
                  f"默认模型: {provider.get('default_model_name')}")
    except Exception as e:
        print(f"✗ 获取Provider列表失败: {e}")
    
    print("\n=== 配置完成 ===")
    print("\n现在在测试中使用:")
    print("model_provider='openai'")
    print("model_version='lm_studio/qwen/qwen3-30b'")
    print("\n💡 提示：如果不使用 llm_override，系统将自动使用默认Provider")


def set_default_provider_by_name(provider_name: str = "openai"):
    """
    快速设置指定名称的Provider为默认Provider
    
    Args:
        provider_name: Provider名称，默认为"openai"
    """
    print(f"=== 设置 '{provider_name}' 为默认Provider ===")
    
    manager = LLMProviderManager()
    
    try:
        # 获取Provider信息
        provider = manager.get_provider_by_name(provider_name)
        if not provider:
            print(f"✗ 未找到名为 '{provider_name}' 的Provider")
            return False
        
        provider_id = provider.get('id')
        print(f"找到Provider: {provider_name} (ID: {provider_id})")
        
        # 设置为默认
        if manager.set_default_provider(provider_id):
            print(f"✓ 成功将 '{provider_name}' 设置为默认Provider")
            return True
        else:
            print(f"✗ 设置失败")
            return False
            
    except Exception as e:
        print(f"✗ 操作失败: {e}")
        return False


# 如果只想设置默认Provider，取消下面的注释：
# if __name__ == "__main__":
#     set_default_provider_by_name("openai") 