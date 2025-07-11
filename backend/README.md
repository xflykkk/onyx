# Onyx Backend 模块说明

## 目录结构

```
backend/
├── onyx/                       # 核心业务逻辑
│   ├── main.py                 # FastAPI应用入口
│   ├── auth/                   # 认证授权模块
│   ├── chat/                   # 聊天对话功能
│   ├── connectors/             # 数据连接器(40+种)
│   ├── db/                     # 数据库模型和操作
│   ├── document_index/         # 文档索引引擎
│   ├── indexing/               # 文档索引处理
│   ├── context/search/         # 搜索和检索
│   ├── server/                 # API路由和控制器
│   ├── llm/                    # 大语言模型集成
│   ├── file_store/             # 文件存储服务
│   ├── background/             # 后台任务处理
│   ├── configs/                # 配置管理
│   └── utils/                  # 工具函数
├── ee/                         # 企业版功能
│   ├── onyx/                   # 企业版业务逻辑
│   └── LICENSE                 # 企业版许可证
├── model_server/               # 模型服务器
│   ├── main.py                 # 模型服务入口
│   ├── encoders/               # 编码器模块
│   └── custom_models/          # 自定义模型
├── alembic/                    # 数据库迁移
├── tests/                      # 测试代码
├── scripts/                    # 工具脚本
└── requirements/               # 依赖管理
```

## 核心模块职责

### 1. 认证授权 (onyx/auth)
- 用户认证：OAuth2、OIDC、SAML
- 角色权限管理：Admin、Curator、Basic等
- API密钥管理

### 2. 文档索引 (onyx/indexing)
- 文档分块处理 (Chunking)
- 向量化嵌入 (Embedding)
- 搜索索引构建
- 多通道索引支持

### 3. 数据连接器 (onyx/connectors)
- 40+种数据源连接器
- 增量同步和全量同步
- 文档权限管理
- 连接器状态监控

### 4. 搜索检索 (onyx/context/search)
- 语义搜索
- 混合搜索 (向量+关键词)
- 权限过滤
- 搜索结果重排序

### 5. 聊天对话 (onyx/chat)
- 对话会话管理
- 消息流处理
- 引文生成
- 工具调用支持

### 6. 数据库层 (onyx/db)
- SQLAlchemy ORM模型
- 多租户支持
- 数据库连接池管理
- 异步数据库操作

### 7. 后台任务 (onyx/background)
- Celery分布式任务队列
- 文档索引任务
- 数据同步任务
- 定时任务调度

## 技术架构

### 核心技术栈
- **Web框架**: FastAPI
- **数据库**: PostgreSQL
- **搜索引擎**: Vespa
- **任务队列**: Celery + Redis
- **向量化**: 多种Embedding模型
- **LLM集成**: 多种大语言模型

### 架构特点
- 微服务架构设计
- 异步非阻塞处理
- 水平扩展支持
- 多租户隔离
- 企业级安全

## 核心链路说明

### 1. 文档索引链路
```
文档输入 → 连接器拉取 → 内容解析 → 文档分块 → 向量化 → 索引存储 → 权限同步
```

**关键组件**:
- `onyx/connectors/`: 数据源连接
- `onyx/indexing/chunker.py`: 文档分块
- `onyx/indexing/embedder.py`: 向量化处理
- `onyx/document_index/`: 索引管理

### 2. 搜索检索链路
```
用户查询 → 查询理解 → 权限过滤 → 向量检索 → 结果重排 → 内容返回
```

**关键组件**:
- `onyx/context/search/`: 搜索管道
- `onyx/context/search/preprocessing/`: 查询预处理
- `onyx/context/search/postprocessing/`: 结果后处理

### 3. 聊天对话链路
```
用户消息 → 上下文构建 → 文档检索 → Prompt构建 → LLM调用 → 流式响应
```

**关键组件**:
- `onyx/chat/chat_utils.py`: 对话工具
- `onyx/chat/prompt_builder/`: Prompt构建
- `onyx/chat/process_message.py`: 消息处理
- `onyx/llm/`: LLM集成

### 4. 后台任务链路
```
任务触发 → 队列调度 → 任务执行 → 状态更新 → 结果通知
```

**关键组件**:
- `onyx/background/celery/`: Celery配置
- `onyx/background/indexing/`: 索引任务
- `onyx/background/task_utils.py`: 任务工具

## 部署配置

### 环境变量
- `POSTGRES_*`: 数据库配置
- `VESPA_*`: 搜索引擎配置
- `REDIS_*`: 缓存配置
- `AUTH_*`: 认证配置
- `LLM_*`: 模型配置

### 服务组件
- **API服务**: FastAPI应用
- **模型服务**: 独立的模型推理服务
- **Worker服务**: Celery后台任务
- **数据库**: PostgreSQL + Redis

## 扩展开发

### 添加新连接器
1. 在 `onyx/connectors/` 创建新连接器
2. 实现 `LoadConnector` 和 `PollConnector` 接口
3. 注册到连接器工厂

### 添加新LLM
1. 在 `onyx/llm/` 实现LLM接口
2. 配置模型参数
3. 注册到LLM工厂

### 自定义搜索
1. 扩展 `onyx/context/search/` 模块
2. 实现自定义检索策略
3. 配置搜索管道 