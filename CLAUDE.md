1. 如果你要运行代码，总是基于项目的.conda 环境下的 python运行。


# deepbridge-knowledge Project Guide

## Overview

deepbridge-knowledge (formerly Danswer) is an open-source Gen-AI + Enterprise Search platform that connects to company docs, apps, and people. It provides a feature-rich chat interface, supports 40+ connectors (Google Drive, Slack, Confluence, etc.), and can be deployed anywhere - from laptop to cloud.

## Project Structure

```
onyx/
├── backend/                    # FastAPI backend services
│   ├── onyx/                  # Core business logic
│   │   ├── agents/            # AI agent orchestration (智能搜索)
│   │   ├── connectors/        # Data source connectors (40+ types)
│   │   │   └── qiniu_cloud/   # Qiniu Cloud storage connector
│   │   ├── file_store/        # File storage abstractions
│   │   ├── llm/               # LLM provider management
│   │   ├── prompts/           # Prompt templates
│   │   └── server/            # FastAPI endpoints
│   ├── ee/                    # Enterprise edition features
│   ├── model_server/          # ML model serving
│   ├── scripts/               # Development & maintenance scripts
│   └── tests/                 # Backend tests
├── web/                       # Next.js frontend (admin interface)
│   ├── src/                   # React components and pages
│   └── public/                # Static assets
├── front-chat-demo/      # Standalone chat interface
│   ├── src/                   # React components and hooks
│   │   ├── components/        # UI components
│   │   │   ├── ChatInterface.tsx  # Main chat component
│   │   │   ├── LLMProviderManager.tsx  # LLM provider configuration
│   │   │   ├── StreamLogs.tsx      # Stream logging viewer
│   │   │   └── FileLibrary.tsx     # File management
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # API client & utilities
│   │   └── types/             # TypeScript type definitions
├── deployment/                # Deployment configurations
│   ├── docker_compose/        # Docker compose files
│   └── helm/                  # Kubernetes Helm charts
└── examples/                  # Example implementations
```

## Common Commands

### Backend Development

```bash
# Navigate to backend directory
cd backend/

# Install Python dependencies
pip install -r requirements/default.txt
pip install -r requirements/dev.txt  # For development

# Run database migrations
alembic upgrade head

# Start API server (development)
cd backend && AUTH_TYPE=disabled /Users/zhuxiaofeng/Github/onyx/.conda/bin/python -m uvicorn onyx.main:app --reload --port 8888 --host 0.0.0.0

# Start model server
cd backend && AUTH_TYPE=disabled /Users/zhuxiaofeng/Github/onyx/.conda/bin/python -m uvicorn model_server.main:app --reload --port 9000

# Run backend tests
pytest tests/

# Type checking
mypy onyx/

# Code formatting
ruff check --fix .
```

### Background Task Services (Celery)

```bash
# Navigate to backend directory
cd backend/

# Start all background tasks (recommended)
cd backend && python scripts/dev_run_background_jobs.py

# 如果出现 Broken pipe 错误，先清理旧进程：pkill -f celery
```

### Frontend Development

```bash
# Navigate to web directory
cd web/

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Lint code
npm run lint
npm run lint:fix-unused  # Fix unused imports

# Run tests
npm test
```

### Onyx Chat Standalone

```bash
# Navigate to standalone chat
cd onyx-chat-standalone/

# Install dependencies
npm install

# Start development server (recommended)
cd onyx-chat-standalone && npm run dev

# Build for production
npm run build

# Run production server
npm start

# Type checking
npm run type-check

# Lint code
npm run lint
```

### Docker Development

```bash
# Start all services (development)
docker compose -f deployment/docker_compose/docker-compose.dev.yml up

# Start production services
docker compose -f deployment/docker_compose/docker-compose.prod.yml up

# Start with GPU support
docker compose -f deployment/docker_compose/docker-compose.gpu-dev.yml up

# Stop all services
docker compose -f deployment/docker_compose/docker-compose.dev.yml down
```

## High-Level Architecture

### System Components

1. **Web Frontend (Next.js)**
   - Modern React-based UI with TypeScript
   - Real-time chat interface with streaming responses
   - Document management and search capabilities
   - Admin panel for connector and system configuration

2. **API Backend (FastAPI)**
   - RESTful API serving frontend requests
   - Authentication & authorization (OAuth2, OIDC, SAML)
   - Document processing and indexing orchestration
   - Chat session management

3. **Model Server**
   - Serves embedding models for document vectorization
   - Handles LLM inference requests
   - Supports multiple model providers (OpenAI, Anthropic, etc.)

4. **Search Engine (Vespa)**
   - Distributed search and ranking engine
   - Stores document embeddings and metadata
   - Handles hybrid search (vector + keyword)
   - Manages document permissions

5. **Task Queue (Celery + Redis)**
   - Asynchronous document indexing
   - Scheduled connector syncs
   - Background processing tasks

6. **Database (PostgreSQL)**
   - User management and authentication
   - Connector configurations
   - Chat history and sessions
   - System metadata

### Key Data Flows

#### Document Indexing Flow
```
Data Source → Connector → Content Parser → Chunker → Embedder → Vespa Index
```

#### Search/Chat Flow
```
User Query → Query Processing → Permission Check → Vespa Search → 
Context Building → LLM Prompt → Streaming Response → User
```

#### Authentication Flow
```
User Login → OAuth/SAML Provider → JWT Token → API Authorization → 
Resource Access
```

### Core Features

1. **Connectors System**
   - 40+ pre-built connectors (Slack, Google Drive, Confluence, etc.)
   - Incremental and full sync capabilities
   - Permission-aware document access
   - Custom connector framework

2. **Search Capabilities**
   - Semantic search using embeddings
   - Hybrid search combining vector and keyword matching
   - Real-time permission filtering
   - Search result re-ranking

3. **Chat System**
   - Context-aware conversations
   - Citation generation with source links
   - Streaming responses
   - Custom AI assistants/personas

4. **Security & Access Control**
   - Role-based access control (Admin, Curator, Basic)
   - Document-level permissions
   - SSO integration (OIDC, SAML, OAuth2)
   - API key management

5. **Enterprise Features (EE)**
   - Advanced analytics and usage reporting
   - Priority support
   - Enhanced security features
   - Multi-tenancy support

### Technology Stack

- **Backend**: Python, FastAPI, SQLAlchemy, Celery
- **Frontend**: TypeScript, React, Next.js, Tailwind CSS
- **Database**: PostgreSQL, Redis
- **Search**: Vespa
- **ML/AI**: Multiple LLM providers, Custom embedding models
- **Infrastructure**: Docker, Kubernetes, Nginx

### Environment Configuration

Key environment variables:
- `AUTH_TYPE`: Authentication method (disabled, basic, google_oauth, oidc, saml)
- `POSTGRES_*`: Database connection settings
- `VESPA_*`: Search engine configuration
- `REDIS_*`: Cache and queue settings
- `GEN_AI_*`: LLM configuration
- `WEB_DOMAIN`: Frontend URL for CORS

### Development Tips

1. **Adding a New Connector**
   - Implement in `backend/onyx/connectors/`
   - Follow the `LoadConnector` and `PollConnector` interfaces
   - Register in the connector factory

2. **Modifying the UI**
   - Frontend code in `web/src/`
   - Components use Tailwind CSS for styling
   - API calls go through `web/src/lib/`

3. **Database Changes**
   - Create Alembic migration: `alembic revision -m "description"`
   - Migrations in `backend/alembic/versions/`

4. **Testing**
   - Backend: pytest-based tests in `backend/tests/`
   - Frontend: Jest tests with `npm test`
   - Integration tests available for full system testing

### 已禁用的任务备忘
- `check_for_external_group_sync` 和 `check_for_doc_permissions_sync` 任务已在 beat_schedule.py 中注释禁用。
- 这两个任务分别负责外部用户组权限同步和文档级权限同步，如需重新启用权限控制功能需要取消注释。

### 新增功能和组件
- **LLM 提供商管理器**: 在 onyx-chat-standalone 中新增 LLMProviderManager 组件，支持多种 LLM 提供商配置
- **流式日志查看器**: StreamLogs 组件提供实时流式响应日志监控和分析
- **文件库管理**: FileLibrary 组件支持文件上传、管理和索引
- **现代化 UI**: 使用 Framer Motion 和 Tailwind CSS 构建的现代化用户界面
- **完整的 API 客户端**: 支持所有后端 API 端点的 TypeScript 客户端
- **七牛云集成**: 完整的七牛云存储连接器和文件存储后端

### 调试工具和配置
- **流式日志监控**: 设置环境变量 `ENABLE_STREAM_LOGGING=true` 启用 SSE 流式响应的详细日志记录
- **日志位置**: 默认存储在 `/Users/zhuxiaofeng/Github/onyx/backend/example/`，可通过 `STREAM_LOG_DIR` 环境变量自定义
- **监控工具**: 
  - `python backend/scripts/start_stream_monitoring.py` - 实时监控新的流式日志
  - `python backend/scripts/view_stream_logs.py --latest` - 查看最新的流式日志详情
  - `python backend/scripts/view_stream_logs.py --help` - 查看详细使用说明
- **Web界面监控**: 使用 onyx-chat-standalone 中的 StreamLogs 组件进行可视化监控
- **用途**: 用于调试子问题引用、文档搜索、流式响应等 SSE 相关问题

### LLM 调用日志配置
- **启用详细交互日志**: `export LOG_DANSWER_MODEL_INTERACTIONS=true`
- **启用开发环境文件日志**: `export DEV_LOGGING_ENABLED=true` 和 `export LOG_FILE_NAME=onyx`  
- **日志级别**: `export LOG_LEVEL=debug` (查看详细日志)
- **日志文件位置**: 
  - 开发环境: `./log/onyx_debug.log`, `./log/onyx_info.log`
  - 容器环境: `/var/log/onyx_debug.log`, `/var/log/onyx_info.log`
- **说明**: ContextRAG 的 LLM 调用日志会输出到主应用日志系统，不经过 model_server
- **注意**: 首次启用文件日志前需要创建日志目录：`mkdir -p backend/log`

### 文件存储配置
- **默认存储后端**: 七牛云存储（Qiniu Cloud）
- **环境变量配置**:
  - `QINIU_ACCESS_KEY`: 七牛云访问密钥
  - `QINIU_SECRET_KEY`: 七牛云密钥
  - `QINIU_DEFAULT_BUCKET`: 默认存储桶
  - `QINIU_BUCKET_DOMAIN`: 存储桶域名
  - `QINIU_REGION`: 区域（默认: cn-east-1）
- **上传 API**: `POST /manage/qiniu/upload`
- **支持功能**: 文件上传/下载、文件夹管理、批量操作、私有存储
- **连接器支持**: 完整的 Qiniu Cloud 连接器，支持文件发现、索引和同步

### TODO: 回答质量优化点
- **子问题回答LLM优化**: 考虑将 SUB_QUESTION_RAG_PROMPT 从 fast_llm 改为 primary_llm，可能提高子问题回答质量（文件：`backend/onyx/agents/agent_search/deep_search/initial/generate_individual_sub_answer/nodes/generate_sub_answer.py:107`）
- **问题分解LLM优化**: ✅ 已完成 - 将 INITIAL_QUESTION_DECOMPOSITION_PROMPT_ASSUMING_REFINEMENT 从 fast_llm 改为 primary_llm，提高问题分解质量（文件：`backend/onyx/agents/agent_search/deep_search/initial/generate_sub_answers/nodes/decompose_orig_question.py:83`）
- **评测**：加上 opik 的在线评测功能，以便评测不同模型效果。
- **Tokenizer 优化**: embedding 模型当前使用默认的 nomic-ai/nomic-embed-text-v1 tokenizer 作为 fallback，需要改成更有效的 tokenizer（文件：`backend/onyx/llm/utils.py:116`）
- **智能多语言扩展**: multilingual_expansion 的更新应该可以在 chat 的时候就处理，即根据用户的 chat 语言来判断是走中文、英文、或其他语言的多语言检索 expansion 模式，而不只是固定设置。
- **Prompt级别的EXTRA_BODY配置**: 实现为特定Prompt配置独立的EXTRA_BODY参数，特别是enable_think功能
- **本地文件系统自动监控**: 为LocalFileConnector添加文件系统监控和增量同步功能
- **流式响应监控优化**: 完善StreamLogs组件的实时监控和分析功能



完整调用链路图

  Frontend (onyx-chat-standalone)
  ├── useChat.sendMessage() [src/hooks/useChat.ts:178]
  ├── apiClient.sendMessage() [src/lib/api.ts:272]
  │
  HTTP POST /chat/send-message
  │
  Backend (FastAPI)
  ├── handle_new_chat_message() [chat_backend.py:403]
  ├── stream_chat_message() [process_message.py:1240]
  ├── stream_chat_message_objects() [process_message.py:528]
  │   ├── get_chat_session_by_id()
  │   ├── get_llms_for_persona() [factory.py:42]
  │   └── Answer() [answer.py:47]
  │       └── processed_streamed_output
  │           ├── run_agent_search_graph() [智能搜索模式]
  │           ├── run_basic_graph() [基础模式]  
  │           ├── run_kb_graph() [知识图谱模式]
  │           └── run_dc_graph() [分治模式]
  │
  LLM Layer
  ├── DefaultMultiLLM [chat_llm.py:270]
  ├── _stream_implementation() [chat_llm.py:526]
  ├── litellm.completion() [chat_llm.py:416]
  │   ├── OpenAI API
  │   ├── Anthropic API
  │   ├── Local Models
  │   └── Other Providers
  │
  Response Stream (SSE)
  ├── JSON packets (OnyxAnswerPiece, AgentAnswerPiece, etc.)
  ├── Document search results
  ├── Citations
  └── Final message details

  关键执行类详解

  1. CreateChatMessageRequest: 请求参数模型
  2. Answer: 核心协调器，管理整个对话流程
  3. DefaultMultiLLM: LLM 抽象层，统一各种 LLM 调用
  4. StreamingProcessor (前端): 处理流式响应解析
  5. GraphConfig: 配置不同的执行图策略

  分支链路

  - 智能搜索模式: 使用 agent 搜索图进行多轮搜索和推理
  - 基础模式: 直接 LLM 对话
  - 知识图谱模式: 结合 KG 的增强对话
  - 文件上传处理: 通过 /chat/file 端点上传并索引文件



  智能搜索模式 [run_agent_search_graph]
  │
  ├── 📋 prepare_tool_input [准备工具输入]
  │   └── 处理用户查询，准备工具调用参数
  │
  ├── 🔧 choose_tool [选择工具]
  │   └── 决定使用哪个工具或是否进入智能搜索
  │
  ├── 🌟 route_initial_tool_choice [路由决策] 
  │   ├── Branch A: call_tool → basic_use_tool_response → logging_node [常规工具调用]
  │   ├── Branch B: start_agent_search [进入智能搜索主流程] ⭐
  │   └── Branch C: logging_node [直接结束]
  │
  ├── 🚀 start_agent_search [启动智能搜索]
  │   ├── 并行执行：
  │   │   ├── generate_initial_answer_subgraph [生成初始答案子图] 📊
  │   │   └── extract_entity_term [提取实体和术语] 🏷️
  │   │
  │   └── ⬇️ 等待两个并行任务完成
  │
  ├── 🔍 generate_initial_answer_subgraph [初始答案生成子图]
  │   ├── 并行执行：
  │   │   ├── retrieve_orig_question_docs_subgraph [检索原问题文档]
  │   │   └── generate_sub_answers_subgraph [生成子答案子图]
  │   │       ├── decompose_orig_question [分解原问题] 🧩
  │   │       │   └── 使用 fast_llm 将原问题分解为子问题
  │   │       ├── answer_sub_question_subgraphs [并行回答子问题] 🔀
  │   │       │   ├── 为每个子问题并行执行搜索
  │   │       │   ├── 调用搜索工具获取相关文档
  │   │       │   └── 使用主 LLM 生成子答案
  │   │       └── format_initial_sub_answers [格式化初始子答案] 📝
  │   │
  │   ├── generate_initial_answer [生成初始答案] ✨
  │   │   └── 基于检索文档和子答案生成综合初始答案
  │   └── validate_initial_answer [验证初始答案] ✅
  │
  ├── 🤔 decide_refinement_need [决定是否需要精炼]
  │   └── continue_to_refined_answer_or_end [路由决策]
  │       ├── Branch 1: create_refined_sub_questions [需要精炼] 🔄
  │       └── Branch 2: logging_node [不需要精炼，直接结束] 🏁
  │
  ├── 📝 create_refined_sub_questions [创建精炼子问题]
  │   ├── 基于初始答案和提取的实体/术语
  │   ├── 生成更具体、更深入的子问题
  │   └── parallelize_refined_sub_question_answering [并行化精炼子问题回答]
  │
  ├── 🔀 answer_refined_question_subgraphs [回答精炼子问题子图]
  │   ├── 为每个精炼子问题并行执行
  │   ├── 更深入的搜索和分析
  │   └── 生成高质量的子答案
  │
  ├── 📥 ingest_refined_sub_answers [消化精炼子答案]
  │   └── 收集和整理所有精炼子答案
  │
  ├── ⚡ generate_validate_refined_answer [生成并验证精炼答案]
  │   └── 基于精炼子答案生成最终答案
  │
  ├── ⚖️ compare_answers [比较答案]
  │   ├── 比较初始答案和精炼答案
  │   ├── 决定使用哪个答案
  │   └── 评估精炼是否有改进
  │
  └── 📊 logging_node [日志记录] → END
      ├── 记录所有结果和统计信息
      ├── 持久化答案、子问题和子答案
      └── 完成整个智能搜索流程

### 待实现方案：Prompt 级别的 EXTRA_BODY 配置

#### 目标
实现为特定 Prompt 配置独立的 EXTRA_BODY 参数，特别是 `enable_think` 功能，当前 Prompt 未配置时自动使用全局 `LITELLM_EXTRA_BODY` 配置。

#### 实现方案
1. **扩展 PromptConfig 模型**
   ```python
   class PromptConfig:
       system_prompt: str
       description: str
       datetime_aware: bool
       litellm_extra_body: Optional[Dict[str, Any]] = None  # Prompt 专属配置
       enable_thinking: Optional[bool] = None  # 快捷配置 thinking 模式
   ```

2. **合并配置逻辑**
   ```python
   def get_effective_extra_body(prompt_config: Optional[PromptConfig] = None) -> Dict:
       base_extra_body = json.loads(os.getenv("LITELLM_EXTRA_BODY", "{}"))
       
       if prompt_config:
           if prompt_config.litellm_extra_body:
               base_extra_body.update(prompt_config.litellm_extra_body)
           
           if prompt_config.enable_thinking is not None:
               if "anthropic" not in base_extra_body:
                   base_extra_body["anthropic"] = {}
               base_extra_body["anthropic"]["enable_think"] = prompt_config.enable_thinking
       
       return base_extra_body
   ```

3. **使用示例**
   ```python
   # 启用 thinking 的 Prompt
   ASSISTANT_SYSTEM_PROMPT_PERSONA = PromptConfig(
       system_prompt="...",
       description="...",
       datetime_aware=True,
       enable_thinking=True
   )
   
   # 禁用 thinking 的 Prompt
   SUB_QUESTION_RAG_PROMPT = PromptConfig(
       system_prompt="...",
       description="...",
       datetime_aware=False,
       enable_thinking=False
   )
   ```

#### 改动范围
- 修改 PromptConfig 模型定义
- 修改 `chat_llm.py` 中的 `_stream_implementation` 方法
- 保持向后兼容，未配置的 Prompt 使用全局配置

### TODO: 本地文件系统自动监控改进

#### 现状分析
- **✅ 支持本地文件系统**: `LocalFileConnector` 提供基本的本地文件系统支持
- **❌ 缺少自动监控**: 无法自动检测文件变更，需要手动重新索引
- **⚠️ 有限增量**: 仅支持手动增量索引，无时间范围增量更新

#### 技术限制
- `LocalFileConnector` 仅实现 `LoadConnector` 接口，未实现 `PollConnector`
- 缺少文件系统监控机制（如 `watchdog` 或 `inotify`）
- 无法跟踪文件修改时间戳进行增量同步

#### 改进方案
1. **实现 `PollConnector` 接口**: 在 `LocalFileConnector` 中添加时间范围增量同步
2. **添加文件系统监控**: 使用 `watchdog` 库监控文件变更事件
3. **跟踪修改时间**: 记录文件最后修改时间戳，支持增量扫描
4. **配置监控目录**: 添加监控目录、文件模式和排除规则配置
5. **实现事件驱动**: 基于文件系统事件（创建、修改、删除）触发索引更新

#### 预期效果
- 实现真正的实时文件系统监控
- 支持大规模目录的增量同步
- 提供灵活的文件过滤和监控配置
- 减少手动维护成本

### 性能评测和监控

#### 1. 日志监控和性能评测
详细日志配置：
```bash
# 设置详细日志级别
LOG_LEVEL="debug"

# 记录所有LLM交互
LOG_ALL_MODEL_INTERACTIONS="true"

# 记录Vespa查询性能信息
LOG_VESPA_TIMING_INFORMATION="true"

# 记录端点延迟信息
LOG_ENDPOINT_LATENCY="true"
```

#### 2. 连接器状态监控
- 通过右上角的个人资料图标访问"连接器仪表板"
- 查看"状态"页面，显示哪些数据源已被索引以及索引作业的状态
- 监控连接器的运行状况和数据同步情况

#### 3. 遥测数据收集（可选）
默认情况下，Onyx会收集以下匿名遥测数据：
- 延迟信息：了解系统在不同部署环境下的响应时间
- 连接器故障：监控数据连接器的稳定性
- 随机部署UUID：用于区分不同部署实例
- 活跃用户数量：了解系统负载规模

禁用遥测数据：
```bash
DISABLE_TELEMETRY="true"
```

#### 4. API端点评测
使用内置API进行评测：
- `POST /query/answer-with-quote`：测试问答质量和引用准确性
- `POST /chat/send-message-simple-api`：测试基本聊天功能
- `POST /chat/send-message`：测试完整的聊天功能（包括智能搜索）

#### 5. 搜索和检索评测
查询处理配置：
```bash
# 控制文档时间衰减（影响搜索结果的时效性偏好）
DOC_TIME_DECAY=<value>

# 平衡关键词搜索和向量搜索（0-1之间，0为纯关键词，1为纯向量）
HYBRID_ALPHA=<value>

# 启用多语言查询扩展
MULTILINGUAL_QUERY_EXPANSION="English,Chinese"

# 设置问答超时时间
QA_TIMEOUT=<seconds>

# 设置每次聊天会话中输入的最大文档块数
MAX_CHUNKS_FED_TO_CHAT=<number>
```

#### 6. 模型性能评测
LLM配置优化：
```bash
# 设置主要生成AI模型
GEN_AI_MODEL_VERSION="gpt-4"

# 设置快速模型（用于简单任务）
FAST_GEN_AI_MODEL_VERSION="gpt-3.5-turbo"

# 设置最大生成token数
GEN_AI_MAX_TOKENS=<number>
```

#### 7. 嵌入模型评测
测试不同嵌入模型：
- 可以配置不同的嵌入模型提供商（OpenAI、Cohere、Voyage等）
- 通过以下参数调整嵌入性能：
```bash
INDEX_BATCH_SIZE=<size>
EMBEDDING_BATCH_SIZE=<size>
DOC_EMBEDDING_DIM=<dimension>
NORMALIZE_EMBEDDINGS="true"
```

#### 8. 流式响应监控
使用 StreamLogs 组件进行实时监控：
- 查看最新的流式响应日志
- 分析请求处理时间和响应质量
- 监控子问题分解和回答质量
- 检查文档搜索和引用准确性
