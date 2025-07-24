# 后端 API 接口文档

## 概述

后端提供了一套完整的 RESTful API 接口，支持聊天、用户管理、文档管理、模型配置等功能。所有 API 路由都有一个可配置的全局前缀（通过 `APP_API_PREFIX` 环境变量设置）。

## API 分类

### 1. 聊天会话管理接口

#### 会话创建和管理

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 获取用户聊天会话列表 | GET | `/chat/get-user-chat-sessions` | 获取当前用户的所有聊天会话 | 无 | `ChatSessionsResponse` |
| 获取单个会话详情 | GET | `/chat/get-chat-session/{session_id}` | 获取指定会话的详细信息 | - `session_id`: UUID<br>- `is_shared`: bool<br>- `include_deleted`: bool | `ChatSessionDetailResponse` |
| 创建聊天会话 | POST | `/chat/create-chat-session` | 创建新的聊天会话 | `ChatSessionCreationRequest`:<br>- `description`: str (可选)<br>- `persona_id`: int | `CreateChatSessionID` |
| 重命名会话 | PUT | `/chat/rename-chat-session` | 重命名聊天会话 | `ChatRenameRequest`:<br>- `chat_session_id`: UUID<br>- `name`: str (可选，None时自动生成) | `RenameChatSessionResponse` |
| 更新会话设置 | PATCH | `/chat/chat-session/{session_id}` | 更新会话共享状态 | `ChatSessionUpdateRequest`:<br>- `sharing_status`: str | 无 |
| 删除单个会话 | DELETE | `/chat/delete-chat-session/{session_id}` | 删除指定会话 | - `session_id`: UUID<br>- `hard_delete`: bool (可选) | 无 |
| 删除所有会话 | DELETE | `/chat/delete-all-chat-sessions` | 删除用户所有会话 | 无 | 无 |

#### 会话参数配置

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 更新温度设置 | PUT | `/chat/update-chat-session-temperature` | 调整 LLM 回复创造性 | `UpdateChatSessionTemperatureRequest`:<br>- `chat_session_id`: UUID<br>- `temperature_override`: float (0-2) | 无 |
| 更新模型 | PUT | `/chat/update-chat-session-model` | 更换会话使用的模型 | `UpdateChatSessionThreadRequest`:<br>- `chat_session_id`: UUID<br>- `new_alternate_model`: str | 无 |

#### 聊天核心功能

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 发送消息 | POST | `/chat/send-message` | 发送聊天消息（支持流式） | `CreateChatMessageRequest`:<br>- `message`: str<br>- `chat_session_id`: UUID<br>- `persona_id`: int<br>- `files`: list[dict]<br>- 更多参数... | SSE 流式响应 |
| 设置最新消息 | PUT | `/chat/set-message-as-latest` | 将消息设为会话最新 | `ChatMessageIdentifier`:<br>- `message_id`: int | 无 |
| 搜索会话 | GET | `/chat/search` | 搜索聊天历史 | - `query`: str (可选)<br>- `page`: int<br>- `page_size`: int | `ChatSearchResponse` |
| 预设会话 | POST | `/chat/seed-chat-session` | 创建预设聊天会话 | `ChatSeedRequest` | `ChatSeedResponse` |

### 2. 文件和文档管理接口

#### 文件上传和管理

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 上传用户文件 | POST | `/user/file/upload` | 上传文件到用户空间 | - `files`: list[UploadFile]<br>- `folder_id`: int (表单) | list[`UserFileSnapshot`] |
| 从链接创建文件 | POST | `/user/file/create-from-link` | 从 URL 创建文件 | `CreateFileFromLinkRequest`:<br>- `url`: str<br>- `folder_id`: int | list[`UserFileSnapshot`] |
| 获取文件 | GET | `/chat/file/{file_id}` | 下载文件 | `file_id`: str | 文件流 |
| 删除文件 | DELETE | `/user/file/{file_id}` | 删除文件 | `file_id`: int | `MessageResponse` |
| 重命名文件 | PUT | `/user/file/{file_id}/rename` | 重命名文件 | - `file_id`: int<br>- `name`: str | `UserFileSnapshot` |
| 移动文件 | PUT | `/user/file/{file_id}/move` | 移动文件到其他文件夹 | `FileMoveRequest`:<br>- `new_folder_id`: int | `UserFileSnapshot` |
| 重新索引文件 | POST | `/user/file/reindex` | 触发文件重新索引 | `ReindexFileRequest`:<br>- `file_id`: int | `MessageResponse` |
| 批量清理文件 | POST | `/user/file/bulk-cleanup` | 批量删除旧文件 | `BulkCleanupRequest`:<br>- `folder_id`: int<br>- `days_older_than`: int | `MessageResponse` |

#### 文件状态和信息

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 获取索引状态 | GET | `/user/file/indexing-status` | 查询文件索引状态 | `file_ids`: list[int] | dict[int, bool] |
| 获取令牌估算 | GET | `/user/file/token-estimate` | 估算文件令牌数 | - `file_ids`: list[int]<br>- `folder_ids`: list[int] | `{"total_tokens": int}` |

### 3. 文件夹管理接口

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 获取文件夹列表 | GET | `/user/folder` | 获取用户所有文件夹 | 无 | list[`UserFolderSnapshot`] |
| 获取单个文件夹 | GET | `/user/folder/{folder_id}` | 获取文件夹详情 | `folder_id`: int | `UserFolderSnapshot` |
| 创建文件夹 | POST | `/user/folder` | 创建新文件夹 | `FolderCreationRequest`:<br>- `name`: str<br>- `description`: str | `UserFolderSnapshot` |
| 更新文件夹 | PUT | `/user/folder/{folder_id}` | 更新文件夹信息 | `FolderUpdateRequest`:<br>- `name`: str<br>- `description`: str | `UserFolderSnapshot` |
| 删除文件夹 | DELETE | `/user/folder/{folder_id}` | 删除文件夹 | `folder_id`: int | `MessageResponse` |
| 分享文件夹 | POST | `/user/folder/{folder_id}/share` | 与助手共享文件夹 | `ShareRequest`:<br>- `assistant_id`: int | `MessageResponse` |
| 取消分享文件夹 | POST | `/user/folder/{folder_id}/unshare` | 取消文件夹共享 | `ShareRequest`:<br>- `assistant_id`: int | `MessageResponse` |

### 4. OSS文件上传通知和索引管理接口

#### OSS文件上传通知

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| OSS上传通知 | POST | `/doc/file/upload-path` | 处理OSS文件上传完成通知，自动创建连接器、索引文档并关联DocumentSet | `DocFilePathUploadRequest` | `DocFilePathUploadResponse` |
| 查询索引状态 | GET | `/doc/file/status` | 查询OSS文件夹的索引状态和进度 | - `doc_folder_name`: str<br>- `crawl_url`: str (可选) | `DocFileInfoResponse` |

#### OSS文件Chat集成

OSS文件上传后，可通过以下方式在Agent Chat中使用：

**方式1：通过Persona使用OSS文档**
```json
// 1. 上传通知完成后，获取persona_id
POST /doc/file/upload-path
Response: {
  "persona_id": 123,
  "persona_name": "user@example.com"
}

// 2. 使用返回的persona_id创建聊天会话
POST /chat/create-chat-session
{
  "persona_id": 123,
  "description": "与OSS文档对话"
}

// 3. 正常发送消息，自动使用OSS文档
POST /chat/send-message
{
  "chat_session_id": "session-uuid",
  "message": "请总结刚上传的文档内容"
}
```

**方式2：通过DocumentSet过滤使用OSS文档**
```json
// 1. 使用document_set_name进行精确过滤
POST /chat/send-message
{
  "chat_session_id": "session-uuid", 
  "message": "请分析这些文档",
  "retrieval_options": {
    "run_search": "always",
    "filters": {
      "document_set": ["OSS-my-folder-name"]  // 使用上传返回的document_set_name
    }
  }
}
```

### 5. 用户管理接口

#### 用户信息

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 获取当前用户 | GET | `/me` | 获取当前用户详情 | 无 | `UserInfo` |
| 获取用户角色 | GET | `/get-user-role` | 获取当前用户角色 | 无 | `UserRoleResponse` |
| 获取所有用户 | GET | `/users` | 获取所有用户基本信息 | 无 | list[`UserBasicInfo`] |

#### 用户偏好设置

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 更新默认模型 | PATCH | `/user/default-model` | 设置默认 LLM 模型 | `ChosenDefaultModelRequest`:<br>- `default_model`: str | 无 |
| 更新固定助手 | PATCH | `/user/pinned-assistants` | 设置固定的助手列表 | `ReorderPinnedAssistantsRequest`:<br>- `ordered_assistant_ids`: list[int] | 无 |

#### 管理员功能

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 设置用户角色 | PATCH | `/manage/set-user-role` | 更改用户角色 | `UserRoleUpdateRequest`:<br>- `user_email`: str<br>- `new_role`: str | 无 |
| 创建单个用户 | POST | `/manage/admin/create-user` | 直接创建用户并生效 | `CreateUserRequest`:<br>- `email`: str<br>- `password`: str<br>- `role`: UserRole<br>- `is_verified`: bool | `CreateUserResponse` |
| 停用用户 | PATCH | `/manage/admin/deactivate-user` | 停用用户账号 | `UserByEmail`:<br>- `user_email`: str | 无 |
| 激活用户 | PATCH | `/manage/admin/activate-user` | 激活用户账号 | `UserByEmail`:<br>- `user_email`: str | 无 |
| 删除用户 | DELETE | `/manage/admin/delete-user` | 删除用户（需先停用） | `UserByEmail`:<br>- `user_email`: str | 无 |

### 5. LLM 模型管理接口

#### 模型配置（管理员）

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 测试 LLM 配置 | POST | `/admin/llm/test` | 测试 LLM 连接 | `TestLLMRequest`:<br>- `provider`: str<br>- `model`: str<br>- `api_key`: str 等 | 测试结果 |
| 获取提供商列表 | GET | `/admin/llm/provider` | 列出所有 LLM 提供商 | 无 | list[`LLMProviderDescriptor`] |
| 创建/更新提供商 | PUT | `/admin/llm/provider` | 创建或更新 LLM 提供商 | `LLMProviderUpsertRequest` | `LLMProviderUpsertResponse` |
| 删除提供商 | DELETE | `/admin/llm/provider/{provider_id}` | 删除 LLM 提供商 | `provider_id`: int | 无 |
| 设置默认提供商 | POST | `/admin/llm/provider/{provider_id}/default` | 设置默认 LLM 提供商 | `provider_id`: int | 无 |

#### 用户可用模型

| 接口 | 方法 | 路径 | 功能描述 | 请求参数 | 响应 |
|------|------|------|----------|----------|------|
| 获取可用提供商 | GET | `/llm/provider` | 获取用户可用的 LLM 提供商 | 无 | list[`LLMProviderDescriptor`] |



### 7. 其他重要接口

这些接口不在上述分类中，但在系统中扮演重要角色：

- **文档管理接口** (`/document/*`): 管理文档索引、连接器等
- **认证接口** (`/auth/*`): 用户登录、注册、OAuth 等
- **助手/角色接口** (`/persona/*`): 管理 AI 助手配置
- **工具接口** (`/tool/*`): 管理外部工具集成
- **设置接口** (`/settings/*`): 系统设置和配置
- **知识图谱接口** (`/kg/*`): 知识图谱相关功能

## 认证和权限

大多数接口需要用户认证，通过以下方式之一：
- Session Cookie
- API Key
- 外部鉴权Token（当启用外部鉴权时）

### 外部鉴权支持

当系统启用外部鉴权时（`EXTERNAL_AUTH_ENABLED=true`），支持以下认证方式：

**认证Header**：
- `Authorization: Bearer <token>` 
- `X-Auth-Token: <token>` （推荐，避免与API key冲突）
- `X-User-Token: <token>`

**外部鉴权流程**：
1. 客户端在请求头中携带有效的JWT token
2. 系统调用外部鉴权服务验证token
3. 根据返回的邮箱信息自动查找或创建内部用户
4. 如果外部鉴权失败，降级到原生鉴权方式

**配置要求**：
- `EXTERNAL_AUTH_SERVICE_URL`: 外部鉴权服务地址
- `EXTERNAL_AUTH_ENABLED`: 启用外部鉴权功能

权限级别：
- **ADMIN**: 系统管理员，可访问所有功能
- **CURATOR**: 策展人，可管理内容但不能管理用户
- **BASIC**: 普通用户，只能访问个人相关功能
- **SLACK_USER**: Slack 集成用户，权限受限

## 响应格式

所有接口返回 JSON 格式响应，成功响应通常包含数据对象，错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

流式响应（如聊天接口）使用 Server-Sent Events (SSE) 格式。

## 限制和配额

- 文件上传限制：图片最大 20MB，其他文件类型根据配置
- API 速率限制：根据用户角色和系统配置
- 令牌限制：根据模型和用户配额设置

## 附录：API 结构体字段详细说明

本节详细列出了 API 接口中使用的复合结构体及其字段定义。

### LLM 模型管理结构体

#### LLMProviderUpsertRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `name` | str | LLM 提供商名称 | 是 |
| `provider` | str | 提供商类型（openai、anthropic等） | 是 |
| `api_key` | str \| None | API 密钥 | 否 |
| `api_base` | str \| None | API 基础 URL | 否 |
| `api_version` | str \| None | API 版本号 | 否 |
| `custom_config` | dict[str, str] \| None | 自定义配置参数 | 否 |
| `default_model_name` | str | 默认模型名称 | 是 |
| `fast_default_model_name` | str \| None | 快速默认模型名称 | 否 |
| `is_public` | bool | 是否公开可用 | 否（默认 true） |
| `groups` | list[int] | 关联的用户组 ID 列表 | 否（默认空列表） |
| `deployment_name` | str \| None | 部署名称（Azure 等） | 否 |
| `default_vision_model` | str \| None | 默认视觉模型 | 否 |
| `api_key_changed` | bool | API 密钥是否已更改 | 否（默认 false） |
| `model_configurations` | list[ModelConfigurationUpsertRequest] | 模型配置列表 | 否（默认空列表） |

#### LLMProviderDescriptor

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `name` | str | 提供商名称 | 是 |
| `provider` | str | 提供商类型 | 是 |
| `default_model_name` | str | 默认模型名称 | 是 |
| `fast_default_model_name` | str \| None | 快速默认模型名称 | 否 |
| `is_default_provider` | bool \| None | 是否为默认提供商 | 否 |
| `is_default_vision_provider` | bool \| None | 是否为默认视觉提供商 | 否 |
| `default_vision_model` | str \| None | 默认视觉模型 | 否 |
| `model_configurations` | list[ModelConfigurationView] | 模型配置视图列表 | 是 |

#### TestLLMRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `name` | str \| None | 提供商名称 | 否 |
| `provider` | str | 提供商类型 | 是 |
| `api_key` | str \| None | API 密钥 | 否 |
| `api_base` | str \| None | API 基础 URL | 否 |
| `api_version` | str \| None | API 版本 | 否 |
| `custom_config` | dict[str, str] \| None | 自定义配置 | 否 |
| `default_model_name` | str | 默认模型名称 | 是 |
| `fast_default_model_name` | str \| None | 快速默认模型名称 | 否 |
| `deployment_name` | str \| None | 部署名称 | 否 |
| `model_configurations` | list[ModelConfigurationUpsertRequest] | 模型配置列表 | 是 |
| `api_key_changed` | bool | API 密钥是否已更改 | 是 |

### 聊天会话管理结构体

#### CreateChatMessageRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `chat_session_id` | UUID | 聊天会话 ID | 是 |
| `parent_message_id` | int \| None | 父消息 ID（树形结构） | 否 |
| `message` | str | 消息内容 | 是 |
| `file_descriptors` | list[FileDescriptor] | 附加文件描述符列表 | 是 |
| `user_file_ids` | list[int] | 用户文件 ID 列表 | 否（默认空列表） |
| `user_folder_ids` | list[int] | 用户文件夹 ID 列表 | 否（默认空列表） |
| `prompt_id` | int \| None | 提示模板 ID | 否 |
| `search_doc_ids` | list[int] \| None | 指定搜索文档 ID | 否 |
| `retrieval_options` | RetrievalDetails \| None | 检索选项配置 | 否 |
| `rerank_settings` | RerankingDetails \| None | 重排序设置 | 否 |
| `query_override` | str \| None | 查询重写覆盖 | 否 |
| `regenerate` | bool \| None | 是否重新生成 | 否 |
| `llm_override` | LLMOverride \| None | LLM 覆盖配置 | 否 |
| `prompt_override` | PromptOverride \| None | 提示覆盖配置 | 否 |
| `temperature_override` | float \| None | 温度覆盖值 | 否 |
| `alternate_assistant_id` | int \| None | 备用助手 ID | 否 |
| `persona_override_config` | PersonaOverrideConfig \| None | 角色覆盖配置 | 否 |
| `use_existing_user_message` | bool | 使用现有用户消息 | 否（默认 false） |
| `existing_assistant_message_id` | int \| None | 现有助手消息 ID | 否 |
| `structured_response_format` | dict \| None | 结构化响应格式 | 否 |
| `use_agentic_search` | bool | 使用智能搜索 | 否（默认 false） |
| `skip_gen_ai_answer_generation` | bool | 跳过 AI 答案生成 | 否（默认 false） |

#### ChatSessionCreationRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `persona_id` | int | 角色 ID | 否（默认 0） |
| `description` | str \| None | 会话描述 | 否 |

#### ChatRenameRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `chat_session_id` | UUID | 聊天会话 ID | 是 |
| `name` | str \| None | 新名称（None 时自动生成） | 否 |

#### ChatSessionUpdateRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `sharing_status` | ChatSessionSharedStatus | 共享状态枚举值 | 是 |

#### UpdateChatSessionTemperatureRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `chat_session_id` | UUID | 聊天会话 ID | 是 |
| `temperature_override` | float | 温度覆盖值（0-2） | 是 |

#### UpdateChatSessionThreadRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `chat_session_id` | UUID | 聊天会话 ID | 是 |
| `new_alternate_model` | str | 新的备用模型名称 | 是 |

#### ChatMessageIdentifier

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `message_id` | int | 消息 ID | 是 |

#### ChatSeedRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `persona_id` | int | 角色 ID | 是 |
| `prompt_id` | int \| None | 提示模板 ID | 否 |
| `llm_override` | LLMOverride \| None | LLM 覆盖配置 | 否 |
| `prompt_override` | PromptOverride \| None | 提示覆盖配置 | 否 |
| `description` | str \| None | 会话描述 | 否 |
| `message` | str \| None | 种子消息 | 否 |

### 文件管理结构体

#### UserFileSnapshot

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `id` | int | 文件 ID | 是 |
| `name` | str | 文件名 | 是 |
| `document_id` | str | 文档 ID | 是 |
| `folder_id` | int \| None | 所属文件夹 ID | 否 |
| `user_id` | UUID \| None | 用户 ID | 否 |
| `file_id` | str | 文件系统 ID | 是 |
| `created_at` | datetime | 创建时间 | 是 |
| `assistant_ids` | List[int] | 关联助手 ID 列表 | 否（默认空列表） |
| `token_count` | int \| None | 令牌数量 | 否 |
| `indexed` | bool | 是否已索引 | 是 |
| `link_url` | str \| None | 链接 URL | 否 |
| `status` | UserFileStatus | 文件状态枚举 | 是 |
| `chat_file_type` | ChatFileType | 聊天文件类型枚举 | 是 |

#### CreateFileFromLinkRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `url` | str | 文件链接 URL | 是 |
| `folder_id` | int \| None | 目标文件夹 ID | 否 |

#### FileMoveRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `new_folder_id` | int \| None | 新文件夹 ID | 否 |

#### ReindexFileRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `file_id` | int | 文件 ID | 是 |

#### BulkCleanupRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `folder_id` | int | 文件夹 ID | 是 |
| `days_older_than` | int \| None | 清理天数阈值 | 否 |

#### ShareRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `assistant_id` | int | 助手 ID | 是 |

### 文件夹管理结构体

#### UserFolderSnapshot

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `id` | int | 文件夹 ID | 是 |
| `name` | str | 文件夹名称 | 是 |
| `description` | str | 文件夹描述 | 是 |
| `files` | List[UserFileSnapshot] | 包含的文件列表 | 是 |
| `created_at` | datetime | 创建时间 | 是 |
| `user_id` | UUID \| None | 用户 ID | 否 |
| `assistant_ids` | List[int] | 关联助手 ID 列表 | 否（默认空列表） |
| `token_count` | int \| None | 总令牌数量 | 否 |

#### FolderCreationRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `folder_name` | str \| None | 文件夹名称 | 否 |

#### FolderUpdateRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `folder_name` | str \| None | 新文件夹名称 | 否 |

### 用户管理结构体

#### UserInfo

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `id` | str | 用户 ID | 是 |
| `email` | str | 邮箱地址 | 是 |
| `is_active` | bool | 是否激活 | 是 |
| `is_superuser` | bool | 是否超级用户 | 是 |
| `is_verified` | bool | 是否已验证 | 是 |
| `role` | UserRole | 用户角色枚举 | 是 |
| `preferences` | UserPreferences | 用户偏好设置 | 是 |
| `oidc_expiry` | datetime \| None | OIDC 过期时间 | 否 |
| `current_token_created_at` | datetime \| None | 当前令牌创建时间 | 否 |
| `current_token_expiry_length` | int \| None | 当前令牌过期时长 | 否 |
| `is_cloud_superuser` | bool | 是否云超级用户 | 否（默认 false） |
| `team_name` | str \| None | 团队名称 | 否 |
| `is_anonymous_user` | bool \| None | 是否匿名用户 | 否 |
| `password_configured` | bool \| None | 是否配置密码 | 否 |
| `tenant_info` | TenantInfo \| None | 租户信息 | 否 |

#### UserRoleResponse

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `role` | str | 用户角色字符串 | 是 |

#### UserByEmail

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `user_email` | str | 用户邮箱 | 是 |

#### ChosenDefaultModelRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `default_model` | str \| None | 默认模型名称 | 否 |

#### ReorderPinnedAssistantsRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `ordered_assistant_ids` | list[int] | 有序助手 ID 列表 | 是 |

#### UserRoleUpdateRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `user_email` | str | 用户邮箱 | 是 |
| `new_role` | UserRole | 新角色枚举值 | 是 |
| `explicit_override` | bool | 显式覆盖 | 否（默认 false） |

#### CreateUserRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `email` | str | 用户邮箱 | 是 |
| `password` | str | 用户密码 | 是 |
| `role` | UserRole | 用户角色 | 否（默认 BASIC） |
| `is_verified` | bool | 是否已验证 | 否（默认 true） |

#### CreateUserResponse

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `id` | str | 用户 ID | 是 |
| `email` | str | 用户邮箱 | 是 |
| `role` | UserRole | 用户角色 | 是 |
| `is_active` | bool | 是否激活 | 是 |
| `is_verified` | bool | 是否已验证 | 是 |

### 聊天会话响应结构体

#### ChatSessionsResponse

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `sessions` | list[ChatSession] | 聊天会话列表 | 是 |

#### ChatSession

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `id` | UUID | 会话 ID | 是 |
| `name` | str | 会话名称 | 是 |
| `persona_id` | int | 关联角色 ID | 是 |
| `time_created` | datetime | 创建时间 | 是 |
| `shared_status` | ChatSessionSharedStatus | 共享状态 | 是 |
| `folder_id` | int \| None | 所属文件夹 ID | 否 |
| `current_alternate_model` | str \| None | 当前备用模型 | 否 |

### OSS文件管理结构体

#### DocFilePathUploadRequest

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `user_id` | UUID \| None | 用户ID，用于关联个人Persona | 否 |
| `doc_folder_name` | str | 文档文件夹名称 | 是 |
| `crawl_url` | str \| None | 源爬取URL | 否 |
| `doc_folder_oss_url` | str | OSS文件夹URL | 是 |
| `file_count` | int | 文件夹中的文件数量 | 是 |
| `crawl_detail` | str \| None | 爬取详细信息 | 否 |

#### DocFilePathUploadResponse

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `doc_folder_name` | str | 文档文件夹名称 | 是 |
| `crawl_url` | str \| None | 源爬取URL | 否 |
| `success` | bool | 操作是否成功 | 是 |
| `message` | str \| None | 操作结果消息 | 否 |
| `connector_id` | int \| None | 创建的连接器ID | 否 |
| `cc_pair_id` | int \| None | 连接器凭证对ID | 否 |
| `indexed_files_count` | int \| None | 已索引文件数量 | 否 |
| `folder_id` | int \| None | 对应的UserFolder ID | 否 |
| `document_set_id` | int \| None | 创建的DocumentSet ID | 否 |
| `document_set_name` | str \| None | DocumentSet名称 | 否 |
| `persona_id` | int \| None | 关联的Persona ID | 否 |
| `persona_name` | str \| None | Persona名称 | 否 |

#### DocFileInfoResponse

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `doc_folder_name` | str | 文档文件夹名称 | 是 |
| `folder_id` | int \| None | UserFolder ID | 否 |
| `crawl_url` | str \| None | 源爬取URL | 否 |
| `file_ids` | dict[str, bool] | 文件路径到索引状态的映射 | 是 |
| `status` | str | 整体状态码："00"=等待, "10"=处理中, "60"=成功, "61"=失败 | 是 |
| `desc` | str | 状态描述 | 是 |
| `folder_stats` | dict[str, Any] \| None | 文件夹统计信息 | 否 |

### Chat中的DocumentSet过滤结构体

#### BaseFilters (扩展)

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `document_set` | list[str] \| None | DocumentSet名称列表（用于过滤特定DocumentSet） | 否 |
| `source_type` | list[DocumentSource] \| None | 文档源类型过滤 | 否 |
| `time_cutoff` | datetime \| None | 时间截止过滤 | 否 |
| `tags` | list[Tag] \| None | 标签过滤 | 否 |
| `kg_entities` | list[str] \| None | 知识图谱实体过滤 | 否 |

#### RetrievalDetails (扩展)

| 字段名 | 类型 | 描述 | 是否必需 |
|--------|------|------|----------|
| `run_search` | OptionalSearchSetting | 搜索模式："always", "never", "auto" | 否 |
| `real_time` | bool | 是否实时搜索 | 否 |
| `filters` | BaseFilters \| None | 文档过滤配置（包含DocumentSet过滤） | 否 |
| `enable_auto_detect_filters` | bool \| None | 启用自动检测过滤器 | 否 |
| `dedupe_docs` | bool | 去重文档 | 否 |
| `chunks_above` | int | 上文块数 | 否 |
| `chunks_below` | int | 下文块数 | 否 |
| `full_doc` | bool | 是否返回完整文档 | 否 |

## OSS文件使用完整示例

### 1. OSS文件上传通知
```bash
curl -X POST "http://api.example.com/doc/file/upload-path" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "doc_folder_name": "company-docs/Q4-reports", 
    "doc_folder_oss_url": "https://bucket.qiniu.com/company-docs/Q4-reports/",
    "file_count": 15,
    "crawl_url": "https://internal.company.com/reports/q4"
  }'
```

### 2. 检查索引状态
```bash
curl -X GET "http://api.example.com/doc/file/status?doc_folder_name=company-docs/Q4-reports&crawl_url=https://internal.company.com/reports/q4"
```

### 3. 使用OSS文档进行Chat对话
```bash
# 方式1：使用返回的Persona ID
curl -X POST "http://api.example.com/chat/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_session_id": "session-uuid-here",
    "message": "请总结Q4报告的关键指标",
    "persona_id": 123
  }'

# 方式2：使用DocumentSet过滤
curl -X POST "http://api.example.com/chat/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_session_id": "session-uuid-here",
    "message": "分析Q4财务数据的趋势",
    "retrieval_options": {
      "run_search": "always",
      "filters": {
        "document_set": ["OSS-company-docs-Q4-reports"]
      }
    }
  }'
```