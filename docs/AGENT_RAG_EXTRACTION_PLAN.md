# Agent RAG 组件独立剥离改造方案

## 一、现状分析

### 1.1 核心技术栈

| 组件 | 技术 | 位置 |
|-----|-----|------|
| **向量数据库** | Vespa | `backend/onyx/document_index/vespa/` |
| **Agent 循环** | 自定义实现（非 LangGraph） | `backend/onyx/chat/llm_loop.py` |
| **工具系统** | 抽象 Tool 基类 | `backend/onyx/tools/` |
| **MCP 服务器** | FastMCP | `backend/onyx/mcp_server/` |
| **LLM 集成** | LiteLLM | `backend/onyx/llm/` |
| **深度研究** | 编排层 + Think Tool | `backend/onyx/deep_research/` |

### 1.2 核心 RAG 亮点功能

#### 1.2.1 搜索工具 5 步流程 (`search_tool.py`)
1. **查询生成 (Query Generation)** - LLM 生成多个查询变体
2. **重组合 (Recombination)** - 使用加权 RRF 合并搜索结果
3. **选择 (Selection)** - LLM 选择最相关的文档片段
4. **扩展 (Expansion)** - LLM 决定需要读取的上下文范围
5. **提示构建 (Prompt Building)** - 构建响应字符串给 LLM

#### 1.2.2 混合搜索 (Hybrid Search)
- 语义搜索 (Embedding) + 关键词搜索 (BM25)
- 可配置的 hybrid_alpha 权重
- 支持多查询并行执行

#### 1.2.3 查询扩展
- 语义查询重述 (`semantic_query_rephrase`)
- 关键词查询扩展 (`keyword_query_expansion`)
- 原始查询权重保留

#### 1.2.4 Agent 循环特性
- 最多 6 个 LLM 循环 (`MAX_LLM_CYCLES`)
- 动态工具选择
- 引用处理器 (Citation Processor)
- 推理模型支持

#### 1.2.5 深度研究 Agent
- 编排层 (Orchestrator Layer)
- Think Tool 内部推理
- 最多 8 个编排循环
- 最终报告生成

#### 1.2.6 MCP 集成
- 标准 MCP 协议支持
- HTTP POST 传输
- 三个核心工具：search_indexed_documents, search_web, open_urls

### 1.3 需要移除的功能

| 功能 | 位置 | 移除原因 |
|-----|-----|---------|
| 用户权限控制 (ACL) | `context/search/preprocessing/access_filters.py` | 业务特定 |
| Persona (助手配置) | `db/models.py` | 业务特定 |
| Celery 后台任务 | `background/celery/` | 部署特定 |
| Slack 集成 | `onyxbot/slack/` | 业务特定 |
| 项目/租户隔离 | 多处 | 业务特定 |
| 联邦搜索 | `federated/` | 业务特定 |
| 企业版功能 | `ee/` | 商业特定 |

---

## 二、剥离后的架构设计

### 2.1 模块结构

```
agent_rag/
├── __init__.py
├── core/                          # 核心抽象和接口
│   ├── __init__.py
│   ├── config.py                  # 配置管理
│   ├── models.py                  # 核心数据模型
│   └── exceptions.py              # 异常定义
│
├── agent/                         # Agent 循环系统
│   ├── __init__.py
│   ├── loop.py                    # 主 Agent 循环
│   ├── step.py                    # 单个 LLM 步骤
│   ├── state.py                   # 状态管理
│   ├── emitter.py                 # 事件发射器
│   └── deep_research/             # 深度研究 Agent (可选)
│       ├── __init__.py
│       ├── orchestrator.py
│       └── report_generator.py
│
├── tools/                         # 工具系统
│   ├── __init__.py
│   ├── interface.py               # Tool 抽象基类
│   ├── runner.py                  # 工具执行器
│   ├── models.py                  # 工具数据模型
│   └── implementations/           # 工具实现
│       ├── __init__.py
│       ├── search/                # 搜索工具
│       │   ├── __init__.py
│       │   ├── search_tool.py     # 核心搜索工具
│       │   ├── utils.py           # 搜索工具函数
│       │   └── constants.py       # 搜索常量
│       ├── web_search/            # 网络搜索
│       │   └── web_search_tool.py
│       ├── open_url/              # URL 打开
│       │   └── open_url_tool.py
│       └── custom/                # 自定义工具支持
│           └── custom_tool.py
│
├── retrieval/                     # 检索系统
│   ├── __init__.py
│   ├── pipeline.py                # 搜索管道
│   ├── query_expansion.py         # 查询扩展
│   ├── document_filter.py         # 文档过滤
│   └── models.py                  # 检索数据模型
│
├── document_index/                # 文档索引抽象
│   ├── __init__.py
│   ├── interfaces.py              # 索引接口定义
│   ├── vespa/                     # Vespa 实现
│   │   ├── __init__.py
│   │   ├── vespa_index.py
│   │   ├── chunk_retrieval.py
│   │   └── utils.py
│   └── memory/                    # 内存实现 (用于测试)
│       └── memory_index.py
│
├── llm/                           # LLM 集成
│   ├── __init__.py
│   ├── interfaces.py              # LLM 接口
│   ├── factory.py                 # LLM 工厂
│   └── providers/                 # 提供商实现
│       ├── __init__.py
│       ├── litellm_provider.py
│       └── base.py
│
├── citation/                      # 引用系统
│   ├── __init__.py
│   ├── processor.py               # 引用处理器
│   └── utils.py                   # 引用工具函数
│
├── mcp/                           # MCP 服务器 (可选)
│   ├── __init__.py
│   ├── server.py                  # MCP 服务器
│   ├── tools/                     # MCP 工具
│   │   ├── __init__.py
│   │   └── search.py
│   └── resources/                 # MCP 资源
│       └── sources.py
│
├── prompts/                       # 提示词模板
│   ├── __init__.py
│   ├── system.py                  # 系统提示
│   ├── search.py                  # 搜索相关提示
│   └── deep_research.py           # 深度研究提示
│
└── utils/                         # 工具函数
    ├── __init__.py
    ├── concurrency.py             # 并发工具
    ├── timing.py                  # 计时工具
    └── logger.py                  # 日志工具
```

### 2.2 核心接口设计

#### 2.2.1 DocumentIndex 接口 (简化版)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SearchFilters:
    """通用搜索过滤器"""
    source_types: Optional[List[str]] = None
    time_cutoff: Optional[datetime] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None

@dataclass
class SearchChunk:
    """搜索结果块"""
    document_id: str
    chunk_id: int
    content: str
    title: Optional[str] = None
    source_type: Optional[str] = None
    link: Optional[str] = None
    score: float = 0.0
    metadata: dict = None

class DocumentIndex(ABC):
    """文档索引抽象接口"""

    @abstractmethod
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        filters: Optional[SearchFilters] = None,
        hybrid_alpha: float = 0.5,
        num_results: int = 10,
    ) -> List[SearchChunk]:
        """混合搜索"""
        pass

    @abstractmethod
    def index_documents(
        self,
        chunks: List[SearchChunk],
    ) -> List[str]:
        """索引文档"""
        pass

    @abstractmethod
    def get_chunks_by_id(
        self,
        document_id: str,
        chunk_range: Optional[tuple[int, int]] = None,
    ) -> List[SearchChunk]:
        """按 ID 获取文档块"""
        pass
```

#### 2.2.2 Tool 接口 (简化版)

```python
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic

@dataclass
class ToolResponse:
    """工具响应"""
    llm_facing_response: str  # 返回给 LLM 的文本
    rich_response: Any = None  # 富响应对象 (用于 UI 等)
    citation_mapping: Optional[dict] = None

TOverride = TypeVar("TOverride")

class Tool(ABC, Generic[TOverride]):
    """工具抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def tool_definition(self) -> dict:
        """返回 OpenAI 格式的工具定义"""
        pass

    @abstractmethod
    def run(
        self,
        override_kwargs: TOverride,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        pass
```

#### 2.2.3 Agent 接口

```python
from abc import ABC, abstractmethod
from typing import List, Generator, Optional

@dataclass
class AgentMessage:
    """Agent 消息"""
    role: str  # "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None

@dataclass
class AgentConfig:
    """Agent 配置"""
    max_cycles: int = 6
    system_prompt: Optional[str] = None
    tools: List[Tool] = None
    enable_citations: bool = True

class AgentRAG(ABC):
    """Agent RAG 主接口"""

    @abstractmethod
    def run(
        self,
        messages: List[AgentMessage],
        config: AgentConfig,
    ) -> Generator[AgentMessage, None, None]:
        """运行 Agent 循环，流式返回消息"""
        pass

    @abstractmethod
    def run_sync(
        self,
        messages: List[AgentMessage],
        config: AgentConfig,
    ) -> AgentMessage:
        """同步运行 Agent 循环"""
        pass
```

---

## 三、改造任务分解

### Phase 1: 基础抽象层 (Week 1)

| 任务 | 描述 | 优先级 |
|-----|------|-------|
| 1.1 | 创建项目结构和基础配置 | P0 |
| 1.2 | 定义核心数据模型 (models.py) | P0 |
| 1.3 | 提取 DocumentIndex 接口 | P0 |
| 1.4 | 提取 Tool 抽象基类 | P0 |
| 1.5 | 提取 LLM 接口抽象 | P0 |

### Phase 2: 检索系统 (Week 2)

| 任务 | 描述 | 优先级 |
|-----|------|-------|
| 2.1 | 提取搜索管道核心逻辑 | P0 |
| 2.2 | 提取查询扩展功能 | P0 |
| 2.3 | 提取文档选择和扩展逻辑 | P0 |
| 2.4 | 实现 Vespa 适配器 | P0 |
| 2.5 | 实现内存索引 (用于测试) | P1 |

### Phase 3: 工具系统 (Week 3)

| 任务 | 描述 | 优先级 |
|-----|------|-------|
| 3.1 | 提取 SearchTool 实现 | P0 |
| 3.2 | 提取 WebSearchTool 实现 | P1 |
| 3.3 | 提取 OpenURLTool 实现 | P1 |
| 3.4 | 提取 ToolRunner | P0 |
| 3.5 | 实现自定义工具扩展点 | P1 |

### Phase 4: Agent 循环 (Week 4)

| 任务 | 描述 | 优先级 |
|-----|------|-------|
| 4.1 | 提取 LLM 步骤执行逻辑 | P0 |
| 4.2 | 提取 Agent 主循环 | P0 |
| 4.3 | 提取引用处理系统 | P0 |
| 4.4 | 提取状态管理 | P0 |
| 4.5 | 实现事件发射器 | P1 |

### Phase 5: 高级功能 (Week 5)

| 任务 | 描述 | 优先级 |
|-----|------|-------|
| 5.1 | 提取深度研究 Agent | P1 |
| 5.2 | 实现 MCP 服务器集成 | P1 |
| 5.3 | 提取提示词模板 | P1 |
| 5.4 | 添加可观测性 (tracing) | P2 |

### Phase 6: 集成和测试 (Week 6)

| 任务 | 描述 | 优先级 |
|-----|------|-------|
| 6.1 | 编写单元测试 | P0 |
| 6.2 | 编写集成测试 | P0 |
| 6.3 | 编写文档和示例 | P0 |
| 6.4 | 性能基准测试 | P1 |
| 6.5 | 打包和发布准备 | P0 |

---

## 四、关键代码映射

### 4.1 需要提取的核心文件

| 原始文件 | 目标位置 | 改造说明 |
|---------|---------|---------|
| `onyx/chat/llm_loop.py` | `agent_rag/agent/loop.py` | 移除 Persona、Project 等依赖 |
| `onyx/chat/llm_step.py` | `agent_rag/agent/step.py` | 简化状态管理 |
| `onyx/tools/interface.py` | `agent_rag/tools/interface.py` | 移除 Emitter 依赖 |
| `onyx/tools/tool_runner.py` | `agent_rag/tools/runner.py` | 简化工具执行 |
| `onyx/tools/tool_implementations/search/search_tool.py` | `agent_rag/tools/implementations/search/` | 移除 ACL 和用户相关逻辑 |
| `onyx/context/search/pipeline.py` | `agent_rag/retrieval/pipeline.py` | 移除 ACL 过滤 |
| `onyx/document_index/interfaces.py` | `agent_rag/document_index/interfaces.py` | 简化接口 |
| `onyx/document_index/vespa/` | `agent_rag/document_index/vespa/` | 保留核心检索逻辑 |
| `onyx/secondary_llm_flows/query_expansion.py` | `agent_rag/retrieval/query_expansion.py` | 提取查询扩展 |
| `onyx/secondary_llm_flows/document_filter.py` | `agent_rag/retrieval/document_filter.py` | 提取文档过滤 |
| `onyx/chat/citation_processor.py` | `agent_rag/citation/processor.py` | 保持不变 |
| `onyx/deep_research/dr_loop.py` | `agent_rag/agent/deep_research/` | 可选功能 |
| `onyx/mcp_server/` | `agent_rag/mcp/` | 可选功能 |

### 4.2 需要创建的新抽象

| 新抽象 | 用途 |
|-------|-----|
| `SearchFilters` | 替代 `IndexFilters`，移除 ACL 字段 |
| `AgentConfig` | 替代 `Persona`，简化配置 |
| `EmbeddingProvider` | LLM 嵌入接口抽象 |
| `StreamingHandler` | 流式响应处理接口 |

---

## 五、配置化设计

### 5.1 核心配置项

```python
@dataclass
class AgentRAGConfig:
    """Agent RAG 组件配置"""

    # LLM 配置
    llm_provider: str = "litellm"
    llm_model: str = "gpt-4"
    llm_api_key: Optional[str] = None
    llm_max_tokens: int = 4096

    # 嵌入模型配置
    embedding_provider: str = "litellm"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # 向量数据库配置
    vector_db_type: str = "vespa"  # vespa, memory, etc.
    vespa_host: str = "localhost"
    vespa_port: int = 8080

    # Agent 配置
    max_agent_cycles: int = 6
    enable_deep_research: bool = False
    max_deep_research_cycles: int = 8

    # 搜索配置
    default_hybrid_alpha: float = 0.5
    num_search_results: int = 10
    max_chunks_per_response: int = 15
    enable_query_expansion: bool = True

    # MCP 配置
    enable_mcp_server: bool = False
    mcp_server_port: int = 8090
```

---

## 六、使用示例

### 6.1 基础使用

```python
from agent_rag import AgentRAG, AgentConfig
from agent_rag.document_index.vespa import VespaIndex
from agent_rag.llm.providers import LiteLLMProvider
from agent_rag.tools import SearchTool, WebSearchTool

# 初始化组件
llm = LiteLLMProvider(model="gpt-4")
document_index = VespaIndex(host="localhost", port=8080)

# 创建 Agent
agent = AgentRAG(
    llm=llm,
    document_index=document_index,
    tools=[
        SearchTool(document_index=document_index, llm=llm),
        WebSearchTool(),
    ],
)

# 运行查询
messages = [{"role": "user", "content": "What is our company's vacation policy?"}]
response = agent.run_sync(messages)
print(response.content)

# 流式响应
for chunk in agent.run(messages):
    print(chunk.content, end="", flush=True)
```

### 6.2 深度研究

```python
from agent_rag.agent.deep_research import DeepResearchAgent

agent = DeepResearchAgent(
    llm=llm,
    document_index=document_index,
    max_cycles=8,
)

# 运行深度研究
report = agent.research("Analyze our Q4 sales performance and identify trends")
print(report)
```

### 6.3 MCP 服务器

```python
from agent_rag.mcp import MCPServer

server = MCPServer(
    document_index=document_index,
    llm=llm,
    port=8090,
)
server.start()
```

---

## 七、风险和注意事项

### 7.1 技术风险

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| Vespa 依赖过重 | 部署复杂度高 | 提供内存索引替代方案 |
| LiteLLM 版本兼容 | API 变更风险 | 抽象 LLM 接口 |
| 性能下降 | 抽象层开销 | 性能基准测试 |
| 功能遗漏 | 用户体验下降 | 全面测试覆盖 |

### 7.2 设计决策

1. **保留 Vespa 作为默认向量数据库** - 成熟稳定，混合搜索能力强
2. **使用 LiteLLM 作为默认 LLM 提供商** - 支持多种模型
3. **保留 5 步搜索流程** - 这是核心 RAG 亮点
4. **可选 MCP 集成** - 作为扩展功能
5. **可选深度研究** - 作为高级功能

---

## 八、验收标准

### 8.1 功能验收

- [ ] 基础搜索功能正常工作
- [ ] 混合搜索 (语义 + 关键词) 正常
- [ ] Agent 循环正常执行
- [ ] 工具调用正常工作
- [ ] 引用系统正常工作
- [ ] 流式响应正常
- [ ] 深度研究功能正常 (可选)
- [ ] MCP 服务器正常 (可选)

### 8.2 性能验收

- [ ] 单次查询响应时间 < 5s
- [ ] 并发查询支持 > 10 QPS
- [ ] 内存使用合理

### 8.3 代码质量

- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] 文档完整
- [ ] 无硬编码依赖

---

## 九、后续扩展计划

1. **支持更多向量数据库** - Pinecone, Weaviate, Milvus
2. **支持更多 LLM 提供商** - 本地模型, Azure, AWS Bedrock
3. **添加更多工具** - 代码执行, 图表生成
4. **支持多模态** - 图像理解和生成
5. **添加评估框架** - RAG 质量评估
