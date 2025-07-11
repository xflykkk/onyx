"""
测试 send-message API 的测试用例
测试文件路径：/Users/zhuxiaofeng/Github/onyx/backend/test/test_send_message_api.py
"""

import pytest
import requests
import json
from uuid import uuid4
from typing import Dict, Any
from unittest.mock import Mock, patch
from test_document_upload_api import TestDocumentUploadAPI

class TestSendMessageAPI:
    """
    测试 send-message API 的测试类
    API 端点：POST /chat/send-message
    """
    
    def __init__(self):
        # 基础配置
        self.base_url = "http://localhost:8080"  # 根据实际服务器地址修改
        self.api_endpoint = "/chat/send-message"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 缓存创建的chat session ID
        self.chat_session_id = None
    
    def get_valid_persona_id(self) -> int:
        """
        获取有效的 persona ID
        """
        try:
            # 尝试获取可用的 persona 列表
            response = requests.get(
                f"{self.base_url}/persona",
                headers=self.headers
            )
            
            if response.status_code == 200:
                personas = response.json()
                if personas and len(personas) > 0:
                    # 返回第一个可用的 persona ID
                    return personas[0]["id"]
            
            # 如果获取失败，返回 None（后续处理）
            return None
        except Exception:
            return None
    
    def create_chat_session(self, persona_id: int = None, description: str = "Test chat session") -> str:
        """
        创建聊天会话并返回session ID
        
        Args:
            persona_id: 人格ID，如果为None则自动获取有效的
            description: 会话描述
            
        Returns:
            str: 聊天会话ID
        """
        # 如果没有提供 persona_id，尝试获取有效的
        if persona_id is None:
            persona_id = self.get_valid_persona_id()
            if persona_id is None:
                raise Exception("No valid persona available")
        
        payload = {
            "persona_id": persona_id,
            "description": description
        }
        
        response = requests.post(
            f"{self.base_url}/chat/create-chat-session",
            json=payload,
            headers=self.headers
        )
        
        if response.status_code == 200:
            result = response.json()
            chat_session_id = result.get("chat_session_id")
            self.chat_session_id = chat_session_id  # 缓存session ID
            return chat_session_id
        else:
            raise Exception(f"Failed to create chat session: {response.status_code}, {response.text}")
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        # 为每个测试创建新的chat session
        try:
            self.chat_session_id = self.create_chat_session()
        except Exception as e:
            print(f"Warning: Failed to create chat session: {e}")
            print("请确保:")
            print("1. 服务器已启动")
            print("2. AUTH_TYPE=disabled 环境变量已设置")
            print("3. 数据库中存在有效的 persona")
            self.chat_session_id = None
    
    def teardown_method(self):
        """每个测试方法执行后的清理"""
        # 重置chat session ID
        self.chat_session_id = None
    
    def get_or_create_test_doc_ids(self, count: int = 1) -> list[int]:
        """
        获取或创建测试文档 ID
        
        Args:
            count: 需要的文档数量
            
        Returns:
            文档 ID 列表
        """
        try:
            # 使用 TestDocumentUploadAPI 创建测试文档
            return TestDocumentUploadAPI.get_test_doc_ids(count)
        except Exception as e:
            print(f"警告：无法创建测试文档: {e}")
            print("这可能是因为:")
            print("1. 服务器未启动")
            print("2. 文件上传或索引服务不可用")
            print("3. 数据库连接问题")
            # 返回空列表，测试会因为验证错误而失败，这是预期的行为
            return []
    
    def construct_basic_request_payload(self) -> Dict[str, Any]:
        """
        构造基本的请求参数
        根据 CreateChatMessageRequest 类型定义构造
        """
        # 如果没有chat session ID，尝试创建一个
        if not self.chat_session_id:
            self.chat_session_id = self.create_chat_session()
            
        return {
            # 必需参数
            "chat_session_id": self.chat_session_id,  # 使用实际创建的chat session ID
            "parent_message_id": None,  # 可选，如果是回复消息则需要
            "message": "这是一条测试消息，用于测试 send-message API",
            "file_descriptors": [],  # 文件描述符列表，如果需要上传文件
            
            # 必需字段：search_doc_ids 或 retrieval_options 必须提供其一
            "search_doc_ids": self.get_or_create_test_doc_ids(3),  # 创建1个测试文档
            
            # 可选参数
            "user_file_ids": [],  # 用户文件 ID 列表
            "user_folder_ids": [],  # 用户文件夹 ID 列表
            "prompt_id": None,  # 提示词 ID
            "retrieval_options": None,  # 检索选项（与search_doc_ids互斥）
            "rerank_settings": None,  # 重排序设置
            "query_override": None,  # 查询覆盖
            "regenerate": False,  # 是否重新生成
            # "llm_override": {
            #     "model_provider": "openai",
            #     "model_version": "gpt-4o", 
            #     "temperature": 0.7
            # },  # LLM 覆盖设置
            "prompt_override": None,  # 提示词覆盖
            "temperature_override": None,  # 温度覆盖
            "alternate_assistant_id": None,  # 备用助手 ID
            "persona_override_config": None,  # 人格覆盖配置
            "use_existing_user_message": False,  # 是否使用现有用户消息
            "existing_assistant_message_id": None,  # 现有助手消息 ID
            "structured_response_format": None,  # 结构化响应格式
            "use_agentic_search": False,  # 是否使用代理搜索
            "skip_gen_ai_answer_generation": False,  # 是否跳过生成式 AI 答案生成
        }
    
    def construct_advanced_request_payload(self) -> Dict[str, Any]:
        """
        构造高级功能的请求参数
        包含更多复杂的参数设置
        """
        payload = self.construct_basic_request_payload()
        
        # 保持使用search_doc_ids，确保与基本测试一致
        # 移除retrieval_options，因为与search_doc_ids互斥
        payload.pop("retrieval_options", None)
        
        # 添加高级参数
        payload.update({
            # 注释掉 retrieval_options，因为与 search_doc_ids 互斥，但保留代码以备将来使用
            # "retrieval_options": {
            #     # 基于 RetrievalDetails 类型的完整字段定义
            #     "run_search": "always",  # OptionalSearchSetting: "always", "never", "auto"
            #     "real_time": True,  # 是否为实时/流式调用
            #     # "filters": {  # BaseFilters 类型
            #     #     "source_type": None,  # 文档源类型过滤
            #     #     "document_set": None,  # 文档集过滤
            #     #     "time_cutoff": None,  # 时间截止过滤
            #     #     "tags": None,  # 标签过滤
            #     # },
            #     "enable_auto_detect_filters": True,  # 是否启用自动检测过滤器
            #     # "offset": 0,  # 搜索结果偏移量
            #     # "limit": 10,  # 搜索结果限制数量
            #     "dedupe_docs": True,  # 是否对文档去重
            #     # 从 ChunkContext 继承的字段
            #     "chunks_above": 1,  # 要包含的上方chunk数量
            #     "chunks_below": 1,  # 要包含的下方chunk数量
            #     "full_doc": False,  # 是否返回完整文档
            # },
            # "rerank_settings": {
            #     # 基于 RerankingDetails 类型的完整字段定义
            #     # "rerank_model_name": "cohere-rerank-multilingual-v3.0",  # 重排序模型名称
            #     # "rerank_api_url": None,  # 重排序服务API URL
            #     # "rerank_provider_type": "cohere",  # 重排序服务提供商: "cohere", "litellm", "bedrock"
            #     # "rerank_api_key": None,  # 重排序服务API密钥
            #     "num_rerank": 10,  # 要重排序的文档数量
            #     # "disable_rerank_for_streaming": False,  # 是否在流式处理中禁用重排序
            # },
            # "llm_override": {
            #     # 基于 LLMOverride 类型的完整字段定义
            #     "model_provider": "openai",  # 模型提供商: "openai", "anthropic", "azure", "bedrock", "vertex_ai"
            #     "model_version": "gpt-4o",  # 模型版本: "gpt-4o", "claude-3-5-sonnet-20241022", etc.
            #     "temperature": 0.7,  # 温度参数 (0.0-1.0)，控制生成文本的随机性
            # },
            "temperature_override": 0.7,  # 温度设置
            "use_agentic_search": True,  # 启用代理搜索
        })
        
        return payload
    
    def construct_custom_llm_request_payload(self, 
                                           model_provider: str = "openai", 
                                           model_version: str = "gpt-4o",
                                           temperature: float = 0.7) -> Dict[str, Any]:
        """
        构造自定义LLM模型的请求参数
        
        Args:
            model_provider: 模型提供商名称（在LLM Provider中配置的name）
            model_version: 模型版本/名称
            temperature: 温度参数
            
        Returns:
            Dict[str, Any]: 请求参数
        """
        payload = self.construct_basic_request_payload()
        
        # 配置自定义LLM
        payload["llm_override"] = {
            "model_provider": model_provider,  # 这里使用配置的LLM Provider名称
            "model_version": model_version,    # 具体的模型名称
            "temperature": temperature
        }
        
        return payload
    
    def test_basic_send_message(self):
        """
        测试基本的发送消息功能
        """
        # 构造请求参数
        payload = self.construct_basic_request_payload()
        print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # 发送请求
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers,
            stream=True  # 因为返回的是 StreamingResponse
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        # 如果状态码不是200，打印错误信息
        if response.status_code != 200:
            error_text = response.text
            print(f"错误响应内容: {error_text}")
            raise Exception(f"API请求失败，状态码: {response.status_code}, 错误: {error_text}")
        
        # 断言响应状态码
        assert response.status_code == 200
        
        # 断言响应内容类型 (SSE 格式)
        content_type = response.headers.get("content-type", "")
        print(f"响应内容类型: {content_type}")
        assert "text/event-stream" in content_type
        
        # 验证 SSE 流式响应
        response_chunks = []
        sse_events = []
        
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                chunk_text = chunk.decode('utf-8')
                response_chunks.append(chunk_text)
                
                # 解析 SSE 事件
                lines = chunk_text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data_content = line[6:]  # 移除 'data: ' 前缀
                        sse_events.append(data_content)
                        print(f"收到 SSE 数据: {data_content[:100]}...")  # 打印前100字符
                    elif line.strip():
                        print(f"收到 SSE 行: {line[:100]}...")
        
        # 断言至少收到了一些响应数据
        assert len(response_chunks) > 0
        print(f"✓ 基本测试成功，共收到 {len(response_chunks)} 个响应块，{len(sse_events)} 个 SSE 事件")
    
    def test_advanced_send_message(self):
        """
        测试高级功能的发送消息
        """
        # 构造高级请求参数
        payload = self.construct_advanced_request_payload()
        print(f"高级测试请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # 发送请求
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers,
            stream=True
        )
        
        print(f"高级测试响应状态码: {response.status_code}")
        print(f"高级测试响应头: {dict(response.headers)}")
        
        # 如果状态码不是200，打印错误信息
        if response.status_code != 200:
            error_text = response.text
            print(f"高级测试错误响应内容: {error_text}")
            raise Exception(f"高级测试API请求失败，状态码: {response.status_code}, 错误: {error_text}")
        
        # 断言响应状态码
        assert response.status_code == 200
        
        # 验证 SSE 流式响应
        response_data = ""
        chunk_count = 0
        sse_events = []
        
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                chunk_text = chunk.decode('utf-8')
                response_data += chunk_text
                chunk_count += 1
                
                # 解析 SSE 事件
                lines = chunk_text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data_content = line[6:]  # 移除 'data: ' 前缀
                        sse_events.append(data_content)
                        print(f"高级测试收到 SSE 数据 {len(sse_events)}: {data_content[:100]}...")
                    elif line.strip():
                        print(f"高级测试收到 SSE 行 {chunk_count}: {line[:100]}...")
        
        # 断言响应不为空
        assert len(response_data) > 0
        
        print(f"✓ 高级测试成功，共收到 {chunk_count} 个响应块，{len(sse_events)} 个 SSE 事件，总长度: {len(response_data)} 字符")
    
    def test_custom_openai_model(self):
        """
        测试使用自定义OpenAI兼容模型
        """
        # 使用您配置的自定义模型
        payload = self.construct_custom_llm_request_payload(
            model_provider="openai",  # 在LLMProviderManager中配置的Provider名称
            model_version="lm_studio/qwen/qwen3-30b",  # 具体的模型名称
            temperature=0.8
        )
        
        # 设置测试消息
        payload["message"] = "请用中文回答：什么是人工智能？"
        
        # 发送请求
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers,
            stream=True
        )
        
        # 断言响应状态码
        assert response.status_code == 200
        
        # 验证流式响应
        response_data = ""
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                response_data += chunk.decode('utf-8')
        
        # 断言响应不为空
        assert len(response_data) > 0
        print(f"Custom model response: {response_data[:200]}...")  # 打印前200字符用于调试
    
    def test_multiple_models_comparison(self):
        """
        测试比较不同模型的响应
        """
        test_message = "用一句话解释量子计算的基本原理"
        
        # 测试模型配置列表
        model_configs = [
            {"provider": "openai", "version": "gpt-4o", "name": "GPT-4O"},
            {"provider": "openai", "version": "gpt-3.5-turbo", "name": "GPT-3.5-Turbo"},
            {"provider": "openai", "version": "lm_studio/qwen/qwen3-30b", "name": "Qwen3-30B-Custom"},  # 您的自定义模型
        ]
        
        results = {}
        
        for config in model_configs:
            try:
                # 构造请求参数
                payload = self.construct_custom_llm_request_payload(
                    model_provider=config["provider"],
                    model_version=config["version"],
                    temperature=0.7
                )
                payload["message"] = test_message
                
                # 发送请求
                response = requests.post(
                    f"{self.base_url}{self.api_endpoint}",
                    json=payload,
                    headers=self.headers,
                    stream=True
                )
                
                if response.status_code == 200:
                    response_data = ""
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            response_data += chunk.decode('utf-8')
                    
                    results[config["name"]] = {
                        "status": "success",
                        "response": response_data[:100],  # 保存前100字符
                        "length": len(response_data)
                    }
                else:
                    results[config["name"]] = {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
            except Exception as e:
                results[config["name"]] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # 打印测试结果
        print("\n=== 模型比较测试结果 ===")
        for model_name, result in results.items():
            print(f"\n{model_name}:")
            print(f"  状态: {result['status']}")
            if result['status'] == 'success':
                print(f"  响应长度: {result['length']} 字符")
                print(f"  响应预览: {result['response']}...")
            else:
                print(f"  错误: {result['error']}")
        
        # 断言至少有一个模型成功响应
        successful_models = [name for name, result in results.items() if result['status'] == 'success']
        assert len(successful_models) > 0, f"没有模型成功响应。结果: {results}"
        
        print(f"\n成功响应的模型: {successful_models}")
    
    def test_temperature_settings(self):
        """
        测试不同温度设置的效果
        """
        test_message = "创作一个关于未来城市的简短故事"
        temperatures = [0.1, 0.5, 0.9]  # 低、中、高温度
        
        results = {}
        
        for temp in temperatures:
            payload = self.construct_custom_llm_request_payload(
                model_provider="openai",
                model_version="gpt-4o",
                temperature=temp
            )
            payload["message"] = test_message
            
            response = requests.post(
                f"{self.base_url}{self.api_endpoint}",
                json=payload,
                headers=self.headers,
                stream=True
            )
            
            if response.status_code == 200:
                response_data = ""
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        response_data += chunk.decode('utf-8')
                
                results[f"temperature_{temp}"] = response_data[:150]  # 保存前150字符
        
        print("\n=== 温度设置测试结果 ===")
        for temp_setting, response in results.items():
            print(f"\n{temp_setting}:")
            print(f"  {response}...")
        
        # 断言所有温度设置都有响应
        assert len(results) == len(temperatures), "部分温度设置测试失败"
    
    def test_invalid_chat_session_id(self):
        """
        测试无效的聊天会话 ID
        """
        payload = self.construct_basic_request_payload()
        payload["chat_session_id"] = "invalid-session-id"
        
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers
        )
        
        # 断言返回错误状态码
        assert response.status_code in [400, 404, 422]
    
    def test_empty_message(self):
        """
        测试空消息
        """
        payload = self.construct_basic_request_payload()
        payload["message"] = ""
        
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers
        )
        
        # 断言返回错误状态码
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields(self):
        """
        测试缺少必需字段
        """
        # 测试缺少 chat_session_id
        payload = self.construct_basic_request_payload()
        del payload["chat_session_id"]
        
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers
        )
        
        assert response.status_code == 422  # Unprocessable Entity
        
        # 测试缺少 message
        payload = self.construct_basic_request_payload()
        del payload["message"]
        
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers
        )
        
        assert response.status_code == 422
    
    def test_with_file_upload(self):
        """
        测试带文件上传的消息发送
        """
        payload = self.construct_basic_request_payload()
        
        # 添加文件描述符
        payload["file_descriptors"] = [
            {
                # TODO: 根据 FileDescriptor 类型定义添加具体字段
                "filename": "test.txt",
                "content_type": "text/plain",
                "size": 100,
                # 其他必需字段...
            }
        ]
        
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers=self.headers,
            stream=True
        )
        
        # 断言响应状态码
        assert response.status_code == 200
        
        # TODO: 验证文件处理是否正确
    
    def test_rate_limiting(self):
        """
        测试速率限制
        """
        # 快速发送多个请求来测试速率限制
        payload = self.construct_basic_request_payload()
        
        responses = []
        for i in range(10):  # 发送 10 个请求
            response = requests.post(
                f"{self.base_url}{self.api_endpoint}",
                json=payload,
                headers=self.headers
            )
            responses.append(response)
        
        # 检查是否有被速率限制的响应
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        
        # TODO: 根据实际的速率限制策略验证
        # 可能需要调整测试逻辑
    
    def test_authentication_required(self):
        """
        测试未认证的请求
        """
        payload = self.construct_basic_request_payload()
        
        # 不带认证头的请求
        response = requests.post(
            f"{self.base_url}{self.api_endpoint}",
            json=payload,
            headers={"Content-Type": "application/json"}  # 不包含认证头
        )
        
        # 断言返回认证错误
        assert response.status_code in [401, 403]


# 测试运行示例
if __name__ == "__main__":
    """
    运行测试的示例代码
    
    需要先启动 Onyx 服务器：
    cd /Users/zhuxiaofeng/Github/onyx/backend
    AUTH_TYPE=disabled /Users/zhuxiaofeng/Github/onyx/.conda/bin/python -m uvicorn onyx.main:app --reload --port 8080
    
    然后运行测试：
    /Users/zhuxiaofeng/Github/onyx/.conda/bin/python -m pytest test/test_send_message_api.py -v
    """
    
    # 创建测试实例
    test_instance = TestSendMessageAPI()
    
    # 运行基本测试
    print("运行基本发送消息测试...")
    try:
        test_instance.setup_method()
        test_instance.test_basic_send_message()
        print("✓ 基本测试通过")
    except Exception as e:
        print(f"✗ 基本测试失败: {e}")
        import traceback
        print("详细错误信息:")
        traceback.print_exc()
    finally:
        test_instance.teardown_method()
    
    # 运行高级测试
    print("运行高级功能测试...")
    try:
        test_instance.setup_method()
        test_instance.test_advanced_send_message()
        print("✓ 高级测试通过")
    except Exception as e:
        print(f"✗ 高级测试失败: {e}")
        import traceback
        print("详细错误信息:")
        traceback.print_exc()
    finally:
        test_instance.teardown_method()


"""
重要说明：需要提供的上下文参数
==================================

1. 认证相关：
   - AUTH_TYPE=disabled 时可能不需要认证
   - 如果需要认证，需要提供有效的 token 或 API key
   - 用户管理逻辑（如何创建测试用户）

2. 聊天会话管理：
   - 如何创建有效的 chat_session_id
   - 聊天会话的生命周期管理
   - 是否需要预先创建聊天会话

3. 数据类型定义：
   - FileDescriptor 的具体字段定义
   - RetrievalDetails 的具体字段定义
   - RerankingDetails 的具体字段定义
   - LLMOverride 的具体字段定义
   - PromptOverride 的具体字段定义
   - PersonaOverrideConfig 的具体字段定义

4. 服务依赖：
   - 数据库连接配置
   - Redis 连接配置
   - Vespa 搜索引擎配置
   - MinIO 文件存储配置
   - 模型服务器配置

5. 测试数据：
   - 测试用的文档和知识库
   - 测试用的用户和权限
   - 测试用的模型配置

6. 响应格式：
   - StreamingResponse 的具体格式
   - 错误响应的格式
   - 成功响应的结构

7. 业务逻辑：
   - 消息处理的完整流程
   - 搜索和检索的逻辑
   - 文件处理的逻辑
   - 权限控制的逻辑

建议：
1. 先查看现有的集成测试代码（tests/integration/），了解测试框架的使用方式
2. 查看 ChatSessionManager 等测试工具类的使用方法
3. 根据实际的 API 文档和类型定义调整测试参数
4. 设置测试环境的数据库和依赖服务

=== 获取有效的 search_doc_ids ===

使用 TestDocumentUploadAPI 类来上传文档并获取有效的文档 ID：

from test_document_upload_api import TestDocumentUploadAPI, get_test_doc_ids

# 方法1：快速获取测试文档 ID
doc_ids = get_test_doc_ids(3)  # 创建3个测试文档
payload["search_doc_ids"] = doc_ids

# 方法2：使用 TestDocumentUploadAPI 类
uploader = TestDocumentUploadAPI()
file_id = uploader.upload_file_and_wait_for_indexing("测试内容", "test.txt")
doc_id = uploader.get_document_id_for_search(file_id)
payload["search_doc_ids"] = [doc_id]
"""