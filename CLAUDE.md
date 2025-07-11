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