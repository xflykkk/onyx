# Onyx 语言配置指南

## 问题描述
在 Agent Search 模式下，即使用户使用中文提问，系统回复中仍包含英文短语如 "No relevant information retrieved"。

## 配置方法

### 1. 环境变量配置（推荐）

在启动 Onyx 服务时设置以下环境变量：

```bash
# 设置响应语言提示
export LANGUAGE_HINT="重要：请始终使用中文回答！"

# 设置对话命名语言提示
export LANGUAGE_CHAT_NAMING_HINT="对话名称必须使用中文。"
```

### 2. 数据库配置

通过管理界面或 API 更新 SearchSettings 中的 `multilingual_expansion` 字段，添加支持的语言：

```python
# 示例：设置支持中文和英文
multilingual_expansion = ["Chinese", "English"]
```

### 3. 修改固定短语（需要修改代码）

如果需要完全本地化固定短语，需要修改以下文件：

**文件：`backend/onyx/prompts/agent_search.py`**

```python
# 原代码（第 9 行）
NO_RECOVERED_DOCS = "No relevant information recovered"

# 建议修改为根据用户语言动态选择：
def get_no_recovered_docs_message(language="en"):
    messages = {
        "en": "No relevant information retrieved",
        "zh": "未检索到相关信息",
        "zh-CN": "未检索到相关信息",
        "zh-TW": "未檢索到相關資訊"
    }
    return messages.get(language, messages["en"])
```

## 验证配置

1. 重启 Onyx 服务
2. 使用中文提问测试
3. 检查响应是否完全使用中文

## 注意事项

1. Agent Search 模式有专门的语言控制提示，理论上应该能够根据用户问题的语言来响应
2. 但某些硬编码的固定短语可能不会被翻译
3. 完整的本地化需要修改代码中的固定短语

## 相关文件

- `/backend/onyx/configs/chat_configs.py` - 语言提示配置
- `/backend/onyx/prompts/agent_search.py` - Agent Search 提示词
- `/backend/onyx/db/search_settings.py` - 多语言扩展设置