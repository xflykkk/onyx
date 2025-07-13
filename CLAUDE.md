1. 如果你要运行代码，总是基于项目的.conda 环境运行。


# Onyx Project Guide

## Overview

Onyx (formerly Danswer) is an open-source Gen-AI + Enterprise Search platform that connects to company docs, apps, and people. It provides a feature-rich chat interface, supports 40+ connectors (Google Drive, Slack, Confluence, etc.), and can be deployed anywhere - from laptop to cloud.

## Project Structure

```
onyx/
├── backend/                    # FastAPI backend services
│   ├── onyx/                  # Core business logic
│   ├── ee/                    # Enterprise edition features
│   ├── model_server/          # ML model serving
│   └── tests/                 # Backend tests
├── web/                       # Next.js frontend
│   ├── src/                   # React components and pages
│   └── public/                # Static assets
├── onyx-chat-standalone/      # Standalone chat interface
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
cd backend && AUTH_TYPE=disabled /Users/zhuxiaofeng/Github/onyx/.conda/bin/python -m uvicorn onyx.main:app --reload --port 8080

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

### 调试工具和配置
- **流式日志监控**: 设置环境变量 `ENABLE_STREAM_LOGGING=true` 启用 SSE 流式响应的详细日志记录
- **日志位置**: 默认存储在 `/tmp/onyx_stream_logs/`，可通过 `STREAM_LOG_DIR` 环境变量自定义
- **监控工具**: 
  - `python backend/scripts/start_stream_monitoring.py` - 实时监控新的流式日志
  - `python backend/scripts/view_stream_logs.py --latest` - 查看最新的流式日志详情
  - `python backend/scripts/view_stream_logs.py --help` - 查看详细使用说明
- **用途**: 用于调试子问题引用、文档搜索、流式响应等 SSE 相关问题


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
