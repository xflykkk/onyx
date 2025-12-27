# Agent RAG 组件独立剥离改造方案 (v2)

> 统一剥离普通 Search + Deep Research 核心能力

## 一、链路分析

### 1.1 普通 Chat Search 链路

```
用户消息
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  llm_loop.py - Agent 主循环 (最多 6 轮)                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  LLM Step                                                   ││
│  │    ├── 工具选择 (AUTO/REQUIRED/NONE)                        ││
│  │    ├── 推理输出 (reasoning models)                          ││
│  │    └── 回答生成                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Tool Runner - 工具执行                                     ││
│  │    ├── SearchTool (内部搜索)                                ││
│  │    ├── WebSearchTool (网络搜索)                             ││
│  │    ├── OpenURLTool (打开 URL)                               ││
│  │    └── 其他工具...                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Citation Processor - 引用处理                              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
返回带引用的回答
```

### 1.2 Deep Research 链路

```
用户消息
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  dr_loop.py - Deep Research 主循环                                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Phase 1: CLARIFICATION (可选)                                          │ │
│  │   └── LLM 决定是否需要用户澄清                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                          │                                                   │
│                          ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Phase 2: RESEARCH PLAN                                                 │ │
│  │   └── LLM 生成研究计划                                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                          │                                                   │
│                          ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Phase 3: ORCHESTRATOR LOOP (最多 8 轮)                                 │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │   │  Orchestrator LLM                                                │ │ │
│  │   │    ├── think_tool (推理, 非推理模型用)                            │ │ │
│  │   │    ├── research_agent_tool (调用 Research Agent)                 │ │ │
│  │   │    └── generate_report_tool (生成报告)                           │ │ │
│  │   └──────────────────────────────────────────────────────────────────┘ │ │
│  │                       │                                                 │ │
│  │                       ▼                                                 │ │
│  │   ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │   │  Research Agents (并行执行, ThreadPool)                          │ │ │
│  │   │  ┌────────────┐ ┌────────────┐ ┌────────────┐                   │ │ │
│  │   │  │ Agent #1   │ │ Agent #2   │ │ Agent #3   │                   │ │ │
│  │   │  │ 最多3轮搜索 │ │ 最多3轮搜索 │ │ 最多3轮搜索 │                   │ │ │
│  │   │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                   │ │ │
│  │   │        │              │              │                           │ │ │
│  │   │        ▼              ▼              ▼                           │ │ │
│  │   │  ┌─────────────────────────────────────────────────────────────┐│ │ │
│  │   │  │  工具调用 (只允许 3 种)                                      ││ │ │
│  │   │  │  • SearchTool ──→ 5 步搜索流程                              ││ │ │
│  │   │  │  • WebSearchTool                                            ││ │ │
│  │   │  │  • OpenURLTool                                              ││ │ │
│  │   │  └─────────────────────────────────────────────────────────────┘│ │ │
│  │   │        │                                                         │ │ │
│  │   │        ▼                                                         │ │ │
│  │   │  生成中间报告 (Intermediate Report)                              │ │ │
│  │   └──────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                          │                                                   │
│                          ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Phase 4: FINAL REPORT                                                  │ │
│  │   └── 合并所有研究结果，生成最终报告 (带引用)                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
返回深度研究报告
```

### 1.3 共享核心组件分析

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              共享核心组件                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  LLM Step (llm_step.py)                                                 ││
│  │  • 单次 LLM 调用封装                                                     ││
│  │  • 工具定义传递                                                          ││
│  │  • 推理内容提取                                                          ││
│  │  • 流式响应处理                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Tool System (tools/)                                                   ││
│  │  • Tool 抽象基类                                                         ││
│  │  • ToolRunner 执行器                                                     ││
│  │  • SearchTool (5 步流程)                                                 ││
│  │  • WebSearchTool                                                         ││
│  │  • OpenURLTool                                                           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  SearchTool 5 步流程 (search_tool.py)                                   ││
│  │  1. Query Generation - 多查询生成                                        ││
│  │  2. Recombination - 加权 RRF 合并                                        ││
│  │  3. Selection - LLM 选择相关文档                                         ││
│  │  4. Expansion - LLM 决定上下文范围                                       ││
│  │  5. Prompt Building - 构建响应                                           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Retrieval Pipeline (context/search/)                                   ││
│  │  • 混合搜索 (语义 + BM25)                                                ││
│  │  • 查询扩展 (语义重述 + 关键词扩展)                                       ││
│  │  • 文档过滤和选择                                                        ││
│  │  • 相邻块合并                                                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Citation System (citation/)                                            ││
│  │  • DynamicCitationProcessor                                             ││
│  │  • 引用映射和折叠                                                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Document Index (document_index/)                                       ││
│  │  • DocumentIndex 接口                                                    ││
│  │  • Vespa 实现                                                            ││
│  │  • 混合检索能力                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  LLM Integration (llm/)                                                 ││
│  │  • LLM 接口抽象                                                          ││
│  │  • LiteLLM Provider                                                      ││
│  │  • Token 计数                                                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Concurrency (utils/threadpool_concurrency.py)                          ││
│  │  • 并行执行工具                                                          ││
│  │  • Research Agents 并行                                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Deep Research 专有组件                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Orchestrator Loop (编排层循环)                                            │
│  • Research Agent (研究代理)                                                 │
│  • Think Tool (思考工具, 用于非推理模型)                                      │
│  • Research Plan 生成                                                        │
│  • Intermediate Report 生成                                                  │
│  • Final Report 生成                                                         │
│  • Clarification 流程                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、需要移除的功能

| 功能 | 原始位置 | 移除原因 | 替代方案 |
|-----|---------|---------|---------|
| **用户权限控制 (ACL)** | `access_filters.py` | 业务特定 | 提供 Filter 接口，由使用方实现 |
| **联邦搜索** | `federated_connectors/` | 需要 OAuth + 外部集成 | 提供扩展点，使用方可自行添加 |
| **Persona 模型** | `db/models.py` | 业务特定配置 | 简化为 AgentConfig |
| **Celery 后台任务** | `background/celery/` | 部署特定 | 提供同步索引 API |
| **Slack 集成** | `onyxbot/slack/` | 业务特定 | 移除 |
| **Project/租户隔离** | 多处 | SaaS 特定 | 移除 |
| **企业版功能** | `ee/` | 商业特定 | 移除 |
| **数据库模型** | `db/models.py` | ORM 特定 | 简化为内存/配置模型 |
| **Emitter 流式** | `chat/emitter.py` | UI 特定 | 简化为回调接口 |

---

## 三、目标架构设计

### 3.1 模块结构

```
agent_rag/
├── __init__.py
├── version.py
│
├── core/                              # 核心抽象层
│   ├── __init__.py
│   ├── config.py                      # 全局配置
│   ├── models.py                      # 核心数据模型
│   ├── exceptions.py                  # 异常定义
│   └── callbacks.py                   # 回调接口 (替代 Emitter)
│
├── agent/                             # Agent 系统
│   ├── __init__.py
│   ├── base.py                        # Agent 基类
│   ├── chat_agent.py                  # 普通 Chat Agent (llm_loop)
│   ├── step.py                        # LLM Step 封装
│   ├── state.py                       # 状态管理
│   ├── history.py                     # 消息历史管理
│   │
│   └── deep_research/                 # Deep Research Agent
│       ├── __init__.py
│       ├── orchestrator.py            # 编排层
│       ├── research_agent.py          # 研究代理
│       ├── think_tool.py              # 思考工具
│       ├── report_generator.py        # 报告生成
│       └── prompts.py                 # 专用提示词
│
├── tools/                             # 工具系统
│   ├── __init__.py
│   ├── interface.py                   # Tool 抽象基类
│   ├── registry.py                    # 工具注册表
│   ├── runner.py                      # 工具执行器
│   ├── models.py                      # 工具数据模型
│   │
│   └── builtin/                       # 内置工具
│       ├── __init__.py
│       ├── search/                    # 内部搜索工具
│       │   ├── __init__.py
│       │   ├── search_tool.py         # 5 步搜索核心
│       │   ├── query_expansion.py     # 查询扩展
│       │   ├── document_selection.py  # 文档选择
│       │   ├── context_expansion.py   # 上下文扩展
│       │   └── constants.py
│       ├── web_search/                # 网络搜索
│       │   ├── __init__.py
│       │   ├── web_search_tool.py
│       │   └── providers/             # 搜索提供商
│       │       ├── __init__.py
│       │       ├── base.py
│       │       └── tavily.py
│       └── open_url/                  # URL 工具
│           ├── __init__.py
│           └── open_url_tool.py
│
├── retrieval/                         # 检索系统
│   ├── __init__.py
│   ├── pipeline.py                    # 搜索管道
│   ├── models.py                      # 检索数据模型
│   ├── filters.py                     # 过滤器 (可扩展)
│   ├── ranking.py                     # 排序算法 (RRF 等)
│   └── chunk_merger.py                # 块合并
│
├── document_index/                    # 文档索引抽象
│   ├── __init__.py
│   ├── interface.py                   # 索引接口
│   ├── models.py                      # 索引数据模型
│   │
│   ├── vespa/                         # Vespa 实现
│   │   ├── __init__.py
│   │   ├── vespa_index.py
│   │   ├── query_builder.py
│   │   └── schema/                    # Vespa Schema
│   │       └── onyx_chunk.sd
│   │
│   └── memory/                        # 内存实现 (测试用)
│       ├── __init__.py
│       └── memory_index.py
│
├── llm/                               # LLM 集成
│   ├── __init__.py
│   ├── interface.py                   # LLM 接口
│   ├── config.py                      # LLM 配置
│   ├── token_counter.py               # Token 计数
│   │
│   └── providers/                     # LLM 提供商
│       ├── __init__.py
│       ├── base.py
│       ├── litellm_provider.py        # LiteLLM (默认)
│       └── openai_provider.py         # OpenAI 直接
│
├── embedding/                         # 嵌入模型
│   ├── __init__.py
│   ├── interface.py
│   └── providers/
│       ├── __init__.py
│       ├── litellm_embedder.py
│       └── sentence_transformers.py
│
├── citation/                          # 引用系统
│   ├── __init__.py
│   ├── processor.py                   # 引用处理器
│   └── utils.py                       # 引用工具函数
│
├── prompts/                           # 提示词模板
│   ├── __init__.py
│   ├── system.py                      # 系统提示
│   ├── search.py                      # 搜索相关
│   ├── citation.py                    # 引用相关
│   └── deep_research/                 # 深度研究专用
│       ├── __init__.py
│       ├── orchestrator.py
│       ├── research_agent.py
│       └── report.py
│
├── utils/                             # 工具函数
│   ├── __init__.py
│   ├── concurrency.py                 # 并行执行
│   ├── timing.py                      # 计时
│   └── logger.py                      # 日志
│
└── integrations/                      # 可选集成
    ├── __init__.py
    ├── mcp/                           # MCP 服务器
    │   ├── __init__.py
    │   ├── server.py
    │   └── tools/
    └── api/                           # REST API
        ├── __init__.py
        └── server.py
```

### 3.2 核心接口设计

#### 3.2.1 Agent 接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Generator, Optional, Callable, Any
from enum import Enum

class AgentMode(Enum):
    CHAT = "chat"              # 普通对话
    DEEP_RESEARCH = "deep_research"  # 深度研究


@dataclass
class AgentConfig:
    """Agent 配置"""
    # 基础配置
    mode: AgentMode = AgentMode.CHAT
    system_prompt: Optional[str] = None

    # Chat 模式配置
    max_cycles: int = 6

    # Deep Research 模式配置
    max_orchestrator_cycles: int = 8
    max_research_cycles: int = 3
    skip_clarification: bool = False

    # 工具配置
    enabled_tools: List[str] = field(default_factory=lambda: [
        "internal_search", "web_search", "open_url"
    ])

    # 引用配置
    enable_citations: bool = True

    # 回调
    on_token: Optional[Callable[[str], None]] = None
    on_tool_start: Optional[Callable[[str, dict], None]] = None
    on_tool_end: Optional[Callable[[str, Any], None]] = None
    on_reasoning: Optional[Callable[[str], None]] = None


@dataclass
class Message:
    """消息"""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None
    citations: Optional[List[dict]] = None


@dataclass
class AgentResponse:
    """Agent 响应"""
    content: str
    citations: List[dict] = field(default_factory=list)
    tool_calls: List[dict] = field(default_factory=list)
    reasoning: Optional[str] = None

    # Deep Research 特有
    research_plan: Optional[str] = None
    intermediate_reports: Optional[List[str]] = None


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(
        self,
        llm: "LLM",
        document_index: "DocumentIndex",
        config: AgentConfig = None,
    ):
        self.llm = llm
        self.document_index = document_index
        self.config = config or AgentConfig()
        self._tools = self._initialize_tools()

    @abstractmethod
    def _initialize_tools(self) -> List["Tool"]:
        """初始化工具列表"""
        pass

    @abstractmethod
    def run(
        self,
        messages: List[Message],
    ) -> Generator[AgentResponse, None, None]:
        """流式运行 Agent"""
        pass

    def run_sync(
        self,
        messages: List[Message],
    ) -> AgentResponse:
        """同步运行 Agent"""
        final_response = None
        for response in self.run(messages):
            final_response = response
        return final_response
```

#### 3.2.2 Tool 接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Optional, List

TOverride = TypeVar("TOverride")


@dataclass
class ToolResponse:
    """工具响应"""
    llm_response: str              # 返回给 LLM 的文本
    rich_response: Any = None      # 富响应对象
    citation_mapping: Optional[dict] = None


@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str
    tool_call_id: str
    arguments: dict


class Tool(ABC, Generic[TOverride]):
    """工具抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @abstractmethod
    def tool_definition(self) -> dict:
        """OpenAI 格式的工具定义"""
        pass

    @abstractmethod
    def run(
        self,
        override_kwargs: TOverride,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """执行工具"""
        pass

    def on_start(self, callback: Optional[callable] = None) -> None:
        """工具开始回调"""
        if callback:
            callback(self.name, {})
```

#### 3.2.3 DocumentIndex 接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class SearchFilters:
    """搜索过滤器 (可扩展)"""
    source_types: Optional[List[str]] = None
    time_cutoff: Optional[datetime] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None
    custom_filters: Optional[dict] = None  # 扩展点


@dataclass
class Chunk:
    """文档块"""
    document_id: str
    chunk_id: int
    content: str
    embedding: Optional[List[float]] = None

    # 元数据
    title: Optional[str] = None
    source_type: Optional[str] = None
    link: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # 搜索结果
    score: float = 0.0
    match_highlights: List[str] = field(default_factory=list)


@dataclass
class Section:
    """文档段落 (多个连续块)"""
    center_chunk: Chunk
    chunks: List[Chunk]
    combined_content: str


class DocumentIndex(ABC):
    """文档索引接口"""

    @abstractmethod
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        filters: Optional[SearchFilters] = None,
        hybrid_alpha: float = 0.5,  # 0=纯关键词, 1=纯语义
        num_results: int = 10,
    ) -> List[Chunk]:
        """混合搜索"""
        pass

    @abstractmethod
    def get_chunks_by_document(
        self,
        document_id: str,
        chunk_range: Optional[tuple[int, int]] = None,
    ) -> List[Chunk]:
        """按文档 ID 获取块"""
        pass

    @abstractmethod
    def index_chunks(
        self,
        chunks: List[Chunk],
    ) -> List[str]:
        """索引文档块"""
        pass

    @abstractmethod
    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        """删除文档"""
        pass
```

#### 3.2.4 LLM 接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Generator, Any
from enum import Enum


class ToolChoice(Enum):
    AUTO = "auto"
    REQUIRED = "required"
    NONE = "none"


@dataclass
class LLMConfig:
    """LLM 配置"""
    model: str
    provider: str = "litellm"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4096
    max_input_tokens: int = 128000
    temperature: float = 0.0

    # 推理模型配置
    is_reasoning_model: bool = False
    reasoning_effort: str = "medium"  # low, medium, high


@dataclass
class LLMMessage:
    """LLM 消息"""
    role: str
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    tool_calls: Optional[List[dict]] = None
    reasoning: Optional[str] = None
    usage: Optional[dict] = None


class LLM(ABC):
    """LLM 接口"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[dict]] = None,
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """同步调用"""
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[dict]] = None,
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, LLMResponse]:
        """流式调用"""
        pass

    def count_tokens(self, text: str) -> int:
        """计算 token 数"""
        # 默认实现: 约 4 字符 = 1 token
        return len(text) // 4
```

---

## 四、代码映射表

### 4.1 直接迁移 (核心逻辑保留)

| 原始文件 | 目标文件 | 改造说明 |
|---------|---------|---------|
| `chat/llm_step.py` | `agent/step.py` | 移除 Emitter，使用回调 |
| `chat/llm_loop.py` | `agent/chat_agent.py` | 移除 Persona/Project 依赖 |
| `deep_research/dr_loop.py` | `agent/deep_research/orchestrator.py` | 简化状态管理 |
| `tools/fake_tools/research_agent.py` | `agent/deep_research/research_agent.py` | 移除 DB 依赖 |
| `tools/interface.py` | `tools/interface.py` | 移除 Emitter |
| `tools/tool_runner.py` | `tools/runner.py` | 简化执行逻辑 |
| `tools/tool_implementations/search/search_tool.py` | `tools/builtin/search/search_tool.py` | 移除 ACL |
| `secondary_llm_flows/query_expansion.py` | `tools/builtin/search/query_expansion.py` | 保持不变 |
| `secondary_llm_flows/document_filter.py` | `tools/builtin/search/document_selection.py` | 保持不变 |
| `context/search/pipeline.py` | `retrieval/pipeline.py` | 移除 ACL 过滤 |
| `document_index/interfaces.py` | `document_index/interface.py` | 简化接口 |
| `document_index/vespa/` | `document_index/vespa/` | 保留核心检索 |
| `chat/citation_processor.py` | `citation/processor.py` | 保持不变 |
| `llm/interfaces.py` | `llm/interface.py` | 简化 |
| `utils/threadpool_concurrency.py` | `utils/concurrency.py` | 保持不变 |

### 4.2 需要新建的抽象

| 新文件 | 用途 |
|-------|-----|
| `core/callbacks.py` | 替代 Emitter 的回调接口 |
| `core/config.py` | 统一配置管理 |
| `agent/base.py` | Agent 基类 |
| `tools/registry.py` | 工具注册和发现 |
| `embedding/interface.py` | 嵌入模型接口 |
| `document_index/memory/memory_index.py` | 内存索引实现 |

### 4.3 提示词迁移

| 原始位置 | 目标位置 |
|---------|---------|
| `prompts/chat_prompts.py` | `prompts/system.py` |
| `prompts/tool_prompts.py` | `prompts/search.py` |
| `prompts/deep_research/orchestration_layer.py` | `prompts/deep_research/orchestrator.py` |
| `prompts/deep_research/research_agent.py` | `prompts/deep_research/research_agent.py` |

---

## 五、任务分解

### Phase 1: 基础框架 (第 1 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 1.1 | 创建项目结构和 pyproject.toml | - | 项目骨架 |
| 1.2 | 实现 core/models.py 核心数据模型 | 1.1 | Message, Chunk, Section 等 |
| 1.3 | 实现 core/config.py 配置系统 | 1.1 | AgentConfig, LLMConfig 等 |
| 1.4 | 实现 core/callbacks.py 回调接口 | 1.1 | StreamCallback, ToolCallback |
| 1.5 | 实现 core/exceptions.py 异常 | 1.1 | 自定义异常类 |
| 1.6 | 实现 utils/ 工具函数 | 1.1 | concurrency, timing, logger |

### Phase 2: LLM 层 (第 1 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 2.1 | 实现 llm/interface.py | 1.2 | LLM 抽象接口 |
| 2.2 | 实现 llm/providers/litellm_provider.py | 2.1 | LiteLLM 提供商 |
| 2.3 | 实现 llm/token_counter.py | 2.1 | Token 计数工具 |
| 2.4 | 实现 embedding/interface.py | 1.2 | Embedding 接口 |
| 2.5 | 实现 embedding/providers/litellm_embedder.py | 2.4 | LiteLLM 嵌入 |

### Phase 3: 文档索引层 (第 2 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 3.1 | 实现 document_index/interface.py | 1.2 | DocumentIndex 接口 |
| 3.2 | 实现 document_index/models.py | 3.1 | 索引数据模型 |
| 3.3 | 迁移 document_index/vespa/ | 3.1, 3.2 | Vespa 实现 |
| 3.4 | 实现 document_index/memory/ | 3.1, 3.2 | 内存实现 |
| 3.5 | 编写索引层单元测试 | 3.3, 3.4 | 测试用例 |

### Phase 4: 检索系统 (第 2 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 4.1 | 实现 retrieval/models.py | 1.2 | 检索数据模型 |
| 4.2 | 实现 retrieval/filters.py | 4.1 | 可扩展过滤器 |
| 4.3 | 实现 retrieval/ranking.py | 4.1 | RRF 等排序算法 |
| 4.4 | 实现 retrieval/chunk_merger.py | 4.1 | 块合并逻辑 |
| 4.5 | 实现 retrieval/pipeline.py | 4.1-4.4, 3.1 | 搜索管道 |

### Phase 5: 工具系统 (第 3 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 5.1 | 实现 tools/interface.py | 1.2 | Tool 抽象基类 |
| 5.2 | 实现 tools/models.py | 5.1 | ToolResponse 等 |
| 5.3 | 实现 tools/registry.py | 5.1 | 工具注册表 |
| 5.4 | 实现 tools/runner.py | 5.1-5.3 | 工具执行器 |
| 5.5 | 迁移 tools/builtin/search/ | 5.1-5.4, 4.5 | SearchTool (5 步) |
| 5.6 | 迁移 tools/builtin/web_search/ | 5.1-5.4 | WebSearchTool |
| 5.7 | 迁移 tools/builtin/open_url/ | 5.1-5.4 | OpenURLTool |

### Phase 6: 引用系统 (第 3 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 6.1 | 迁移 citation/processor.py | 1.2 | 引用处理器 |
| 6.2 | 迁移 citation/utils.py | 6.1 | 引用工具函数 |

### Phase 7: Agent 系统 - Chat (第 4 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 7.1 | 实现 agent/base.py | 1.2, 5.1 | Agent 基类 |
| 7.2 | 实现 agent/state.py | 7.1 | 状态管理 |
| 7.3 | 实现 agent/history.py | 7.1 | 消息历史管理 |
| 7.4 | 迁移 agent/step.py | 7.1-7.3, 2.1, 5.4 | LLM Step |
| 7.5 | 迁移 agent/chat_agent.py | 7.1-7.4, 6.1 | Chat Agent |

### Phase 8: Agent 系统 - Deep Research (第 4-5 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 8.1 | 迁移 prompts/deep_research/ | - | DR 提示词 |
| 8.2 | 实现 agent/deep_research/think_tool.py | 5.1, 8.1 | Think Tool |
| 8.3 | 实现 agent/deep_research/report_generator.py | 7.4, 6.1, 8.1 | 报告生成 |
| 8.4 | 迁移 agent/deep_research/research_agent.py | 7.4, 5.4-5.7, 8.1-8.3 | Research Agent |
| 8.5 | 迁移 agent/deep_research/orchestrator.py | 7.1, 8.2-8.4 | Orchestrator |

### Phase 9: 集成和测试 (第 5-6 周)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 9.1 | 编写 Chat Agent 集成测试 | 7.5 | 测试用例 |
| 9.2 | 编写 Deep Research 集成测试 | 8.5 | 测试用例 |
| 9.3 | 编写端到端测试 | 9.1, 9.2 | E2E 测试 |
| 9.4 | 性能基准测试 | 9.1-9.3 | 性能报告 |
| 9.5 | 编写使用文档 | All | README, API 文档 |
| 9.6 | 打包发布准备 | All | PyPI 包 |

### Phase 10: 可选集成 (第 6 周+)

| ID | 任务 | 依赖 | 输出 |
|----|------|------|------|
| 10.1 | 实现 integrations/mcp/ | 7.5, 8.5 | MCP 服务器 |
| 10.2 | 实现 integrations/api/ | 7.5, 8.5 | REST API |

---

## 六、使用示例

### 6.1 普通 Chat 模式

```python
from agent_rag import ChatAgent, AgentConfig
from agent_rag.llm import LiteLLMProvider, LLMConfig
from agent_rag.document_index.vespa import VespaIndex
from agent_rag.embedding import LiteLLMEmbedder

# 初始化组件
llm = LiteLLMProvider(LLMConfig(model="gpt-4o"))
embedder = LiteLLMEmbedder(model="text-embedding-3-small")
index = VespaIndex(host="localhost", port=8080, embedder=embedder)

# 创建 Chat Agent
agent = ChatAgent(
    llm=llm,
    document_index=index,
    config=AgentConfig(
        max_cycles=6,
        enable_citations=True,
        on_token=lambda t: print(t, end="", flush=True),
    ),
)

# 运行
messages = [Message(role="user", content="我们公司的休假政策是什么？")]
response = agent.run_sync(messages)

print(f"\n\nAnswer: {response.content}")
print(f"Citations: {response.citations}")
```

### 6.2 Deep Research 模式

```python
from agent_rag import DeepResearchAgent, AgentConfig, AgentMode

# 创建 Deep Research Agent
agent = DeepResearchAgent(
    llm=llm,
    document_index=index,
    config=AgentConfig(
        mode=AgentMode.DEEP_RESEARCH,
        max_orchestrator_cycles=8,
        max_research_cycles=3,
        skip_clarification=False,
        on_token=lambda t: print(t, end="", flush=True),
        on_reasoning=lambda r: print(f"[Thinking] {r}"),
    ),
)

# 运行深度研究
messages = [Message(role="user", content="分析我们 Q4 的销售策略和改进建议")]

for response in agent.run(messages):
    if response.research_plan:
        print(f"\n=== Research Plan ===\n{response.research_plan}")
    if response.intermediate_reports:
        for i, report in enumerate(response.intermediate_reports):
            print(f"\n=== Intermediate Report {i+1} ===\n{report}")
    if response.content:
        print(f"\n=== Final Report ===\n{response.content}")
```

### 6.3 自定义工具扩展

```python
from agent_rag.tools import Tool, ToolResponse
from dataclasses import dataclass

@dataclass
class DatabaseQueryOverride:
    connection_string: str

class DatabaseQueryTool(Tool[DatabaseQueryOverride]):
    """自定义数据库查询工具"""

    @property
    def name(self) -> str:
        return "database_query"

    @property
    def description(self) -> str:
        return "Query the company database for structured data"

    def tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query"}
                    },
                    "required": ["query"]
                }
            }
        }

    def run(self, override_kwargs: DatabaseQueryOverride, **kwargs) -> ToolResponse:
        query = kwargs.get("query")
        # 执行查询...
        result = execute_query(override_kwargs.connection_string, query)
        return ToolResponse(
            llm_response=f"Query result: {result}",
            rich_response=result,
        )

# 注册并使用
from agent_rag.tools import ToolRegistry

registry = ToolRegistry()
registry.register(DatabaseQueryTool())

agent = ChatAgent(
    llm=llm,
    document_index=index,
    tools=registry.get_all_tools(),
)
```

---

## 七、配置参考

### 7.1 完整配置示例

```python
from agent_rag.core import AgentRAGConfig

config = AgentRAGConfig(
    # LLM 配置
    llm=LLMConfig(
        model="gpt-4o",
        provider="litellm",
        api_key="sk-xxx",
        max_tokens=4096,
        temperature=0.0,
    ),

    # 嵌入模型配置
    embedding=EmbeddingConfig(
        model="text-embedding-3-small",
        provider="litellm",
        dimension=1536,
    ),

    # 向量数据库配置
    document_index=DocumentIndexConfig(
        type="vespa",  # vespa, memory
        vespa_host="localhost",
        vespa_port=8080,
    ),

    # Agent 配置
    agent=AgentConfig(
        mode=AgentMode.CHAT,
        max_cycles=6,
        enable_citations=True,
    ),

    # Deep Research 配置
    deep_research=DeepResearchConfig(
        max_orchestrator_cycles=8,
        max_research_cycles=3,
        skip_clarification=False,
        enable_think_tool=True,  # 非推理模型
    ),

    # 搜索配置
    search=SearchConfig(
        default_hybrid_alpha=0.5,
        num_results=10,
        max_chunks_per_response=15,
        enable_query_expansion=True,
        enable_document_selection=True,
        enable_context_expansion=True,
    ),
)
```

---

## 八、验收标准

### 8.1 功能验收

#### Chat 模式
- [ ] 基础对话正常
- [ ] SearchTool 5 步流程正常
- [ ] WebSearchTool 正常
- [ ] OpenURLTool 正常
- [ ] 多轮工具调用正常 (最多 6 轮)
- [ ] 引用系统正常
- [ ] 流式输出正常

#### Deep Research 模式
- [ ] 研究计划生成正常
- [ ] 编排层循环正常 (最多 8 轮)
- [ ] Research Agent 并行执行正常
- [ ] Think Tool 正常 (非推理模型)
- [ ] 中间报告生成正常
- [ ] 最终报告生成正常
- [ ] 引用折叠和合并正常

### 8.2 性能验收

- [ ] Chat 单次响应 < 5s
- [ ] Deep Research 完整流程 < 5min
- [ ] 并发支持 > 10 QPS
- [ ] 内存使用合理

### 8.3 代码质量

- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] 文档完整
- [ ] 无业务硬编码

---

## 九、依赖关系图

```
                                    ┌─────────────┐
                                    │   core/     │
                                    │  models.py  │
                                    │  config.py  │
                                    │ callbacks.py│
                                    └──────┬──────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
       ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
       │    llm/     │              │  embedding/ │              │   utils/    │
       │ interface   │              │  interface  │              │ concurrency │
       │  providers  │              │  providers  │              │   timing    │
       └──────┬──────┘              └──────┬──────┘              └──────┬──────┘
              │                            │                            │
              │         ┌──────────────────┼──────────────────┐         │
              │         │                  │                  │         │
              ▼         ▼                  │                  ▼         │
       ┌────────────────────┐              │           ┌─────────────┐  │
       │  document_index/   │◄─────────────┘           │  citation/  │  │
       │    interface       │                          │  processor  │  │
       │    vespa/memory    │                          └──────┬──────┘  │
       └─────────┬──────────┘                                 │         │
                 │                                            │         │
                 ▼                                            │         │
       ┌─────────────────┐                                    │         │
       │   retrieval/    │                                    │         │
       │    pipeline     │                                    │         │
       │    ranking      │                                    │         │
       └─────────┬───────┘                                    │         │
                 │                                            │         │
                 ▼                                            │         │
       ┌─────────────────────────────────────────────────────────────────────┐
       │                           tools/                                    │
       │  ┌───────────┐  ┌───────────────┐  ┌─────────────┐  ┌────────────┐ │
       │  │ interface │  │    runner     │  │  registry   │  │  builtin/  │ │
       │  └───────────┘  └───────────────┘  └─────────────┘  │  search    │ │
       │                                                      │  web_search│ │
       │                                                      │  open_url  │ │
       │                                                      └────────────┘ │
       └──────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │                           agent/                                    │
       │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐ │
       │  │   base    │  │   step    │  │  history  │  │  chat_agent      │ │
       │  └───────────┘  └───────────┘  └───────────┘  └──────────────────┘ │
       │                                                                     │
       │  ┌─────────────────────────────────────────────────────────────────┐│
       │  │                    deep_research/                               ││
       │  │  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐││
       │  │  │ orchestrator │  │ research_agent │  │  report_generator   │││
       │  │  └──────────────┘  └────────────────┘  └──────────────────────┘││
       │  └─────────────────────────────────────────────────────────────────┘│
       └─────────────────────────────────────────────────────────────────────┘
```

---

## 十、风险与缓解

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| Vespa 部署复杂 | 用户入门难 | 提供 MemoryIndex + Docker Compose |
| LiteLLM 版本变更 | API 不兼容 | 抽象 LLM 接口，固定版本 |
| 搜索质量下降 | 用户体验差 | 保留完整 5 步流程，添加评估 |
| 性能开销 | 响应变慢 | 基准测试，优化热路径 |
| 提示词泄露 | 竞争风险 | 提示词可配置化 |
