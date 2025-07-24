# 七牛云存储连接器

Onyx 七牛云存储连接器提供完整的七牛云对象存储集成，支持文件上传、下载、索引和同步功能。

## 功能特性

- ✅ 文件上传和下载
- ✅ 通过前缀模拟文件夹管理
- ✅ 文档索引和全文搜索
- ✅ 增量和全量数据同步
- ✅ 图像处理和分析
- ✅ 批量操作支持
- ✅ 私有存储空间支持

## 安装依赖

```bash
pip install qiniu
```

## 环境配置

### 必需环境变量

```bash
# 七牛云访问密钥
export QINIU_ACCESS_KEY=your-access-key

# 七牛云密钥
export QINIU_SECRET_KEY=your-secret-key

# 存储桶名称
export QINIU_DEFAULT_BUCKET=your-bucket-name

# 存储桶域名
export QINIU_BUCKET_DOMAIN=your-bucket-domain.com
```

### 可选环境变量

```bash
# 区域设置（默认: cn-east-1）
export QINIU_REGION=cn-east-1
```

## 快速开始

### 1. 创建存储桶

在七牛云控制台创建存储桶：

1. 登录 [七牛云控制台](https://portal.qiniu.com/)
2. 进入对象存储 → 空间管理
3. 创建新的存储空间
4. 获取存储桶域名

### 2. 获取访问密钥

在七牛云控制台获取密钥：

1. 进入个人中心 → 密钥管理
2. 创建或查看 AccessKey 和 SecretKey
3. 记录密钥信息

### 3. 配置连接器

在 Onyx 管理界面添加七牛云连接器：

1. 进入管理界面 → 连接器
2. 选择"七牛云存储"
3. 填写配置信息：
   - 存储桶名称
   - 存储桶域名
   - 区域（可选）
   - 前缀（可选）

### 4. 上传文件

使用 API 上传文件：

```python
import requests

# 上传文件到七牛云
files = [("files", open("document.pdf", "rb"))]
data = {
    "bucket_name": "your-bucket",
    "bucket_domain": "your-domain.com",
    "auto_index": True
}

response = requests.post(
    "http://localhost:8888/manage/qiniu/upload",
    files=files,
    data=data,
    headers={"Authorization": "Bearer your-token"}
)
```

## API 接口

### 上传文件

```
POST /manage/qiniu/upload
```

**请求参数:**
- `files`: 文件列表
- `bucket_name`: 存储桶名称
- `bucket_domain`: 存储桶域名
- `region`: 区域（可选）
- `prefix`: 前缀（可选）
- `folder_uuid`: 文件夹 UUID（可选）
- `auto_index`: 是否自动索引（默认: true）

**响应:**
```json
{
  "connector_id": 1,
  "credential_id": 1,
  "cc_pair_id": 1,
  "folder_uuid": "abc123",
  "uploaded_files": ["folder/file1.pdf", "folder/file2.docx"],
  "message": "Successfully uploaded 2 files"
}
```

### 列出文件夹

```
GET /manage/qiniu/folders?bucket_name=your-bucket&bucket_domain=your-domain
```

### 获取文件夹信息

```
GET /manage/qiniu/folders/{folder_uuid}?bucket_name=your-bucket&bucket_domain=your-domain
```

### 删除文件夹

```
DELETE /manage/qiniu/folders/{folder_uuid}?bucket_name=your-bucket&bucket_domain=your-domain&force=true
```

## 配置说明

### 连接器配置

```json
{
  "bucket_name": "your-bucket",
  "bucket_domain": "your-domain.com",
  "region": "cn-east-1",
  "prefix": "documents/",
  "folder_uuid": "abc123",
  "auto_create_folder": true,
  "folder_uuid_length": 10,
  "batch_size": 50
}
```

### 凭证配置

```json
{
  "access_key": "your-access-key",
  "secret_key": "your-secret-key",
  "bucket_domain": "your-domain.com"
}
```

## 文件组织结构

七牛云通过对象键前缀模拟文件夹结构：

```
prefix/
├── folder1/
│   ├── .folder_placeholder
│   ├── document1.pdf
│   └── document2.docx
├── folder2/
│   ├── .folder_placeholder
│   └── image1.jpg
└── folder3/
    ├── .folder_placeholder
    └── spreadsheet1.xlsx
```

## 支持的文件类型

- 📄 文档: PDF, DOC, DOCX, TXT, MD, RTF
- 📊 表格: XLS, XLSX, CSV, TSV
- 🖼️ 图像: JPG, JPEG, PNG, GIF, BMP, TIFF
- 📋 演示: PPT, PPTX
- 🔗 网页: HTML, HTM

## 故障排除

### 常见问题

1. **连接失败**
   - 检查访问密钥是否正确
   - 确认存储桶名称和域名
   - 验证网络连接

2. **上传失败**
   - 检查文件大小限制
   - 验证存储桶权限
   - 确认文件格式支持

3. **索引失败**
   - 检查文件内容是否可读
   - 验证文件编码格式
   - 确认文件权限设置

### 日志调试

启用详细日志：

```bash
export LOG_LEVEL=debug
export LOG_DANSWER_MODEL_INTERACTIONS=true
```

### 验证安装

运行验证脚本：

```bash
python -m onyx.connectors.qiniu_cloud.validate_installation
```

## 安全建议

1. **密钥管理**
   - 使用环境变量存储密钥
   - 定期轮换访问密钥
   - 限制密钥权限范围

2. **存储桶安全**
   - 设置合适的访问权限
   - 启用防盗链保护
   - 配置 HTTPS 访问

3. **网络安全**
   - 使用 HTTPS 协议
   - 配置防火墙规则
   - 启用访问日志

## 性能优化

1. **批量操作**
   - 使用批量上传减少请求次数
   - 合理设置批次大小

2. **并发控制**
   - 限制并发上传数量
   - 配置合适的超时时间

3. **缓存策略**
   - 启用 CDN 加速
   - 设置合适的缓存策略

## 版本历史

- v1.0.0 - 基础功能实现
- v1.1.0 - 增量同步支持
- v1.2.0 - 图像处理功能
- v1.3.0 - 批量操作优化

## 技术支持

- 📚 [七牛云文档](https://developer.qiniu.com/)
- 🐛 [问题报告](https://github.com/your-org/onyx/issues)
- 💬 [社区讨论](https://github.com/your-org/onyx/discussions)