# 阿里云 OSS 到七牛云存储迁移指南

本文档说明了 Onyx 从阿里云 OSS 迁移到七牛云存储的变更内容。

## 迁移概览

从 v1.x.x 版本开始，Onyx 将默认的云存储服务从阿里云 OSS 迁移到七牛云存储，以提供更好的性能和用户体验。

## 主要变更

### 1. 环境变量更新

#### 旧配置（阿里云 OSS）
```bash
OSS_ACCESS_KEY_ID=your-aliyun-access-key-id
OSS_ACCESS_KEY_SECRET=your-aliyun-access-key-secret
OSS_DEFAULT_REGION=cn-hangzhou
OSS_DEFAULT_BUCKET=your-oss-bucket
OSS_DEFAULT_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

#### 新配置（七牛云）
```bash
QINIU_ACCESS_KEY=your-qiniu-access-key
QINIU_SECRET_KEY=your-qiniu-secret-key
QINIU_DEFAULT_BUCKET=your-qiniu-bucket
QINIU_BUCKET_DOMAIN=your-bucket-domain.com
QINIU_REGION=cn-east-1  # 可选，默认值
```

### 2. API 端点更新

#### 旧端点（阿里云 OSS）
- `POST /manage/oss/upload`
- `GET /manage/oss/folders`
- `GET /manage/oss/folders/{folder_uuid}`
- `DELETE /manage/oss/folders/{folder_uuid}`

#### 新端点（七牛云）
- `POST /manage/qiniu/upload`
- `GET /manage/qiniu/folders`
- `GET /manage/qiniu/folders/{folder_uuid}`
- `DELETE /manage/qiniu/folders/{folder_uuid}`

### 3. 连接器类型更新

- 旧类型：`DocumentSource.ALIBABA_OSS`
- 新类型：`DocumentSource.QINIU_CLOUD`

### 4. 依赖更新

#### 移除的依赖
```bash
alibabacloud-oss-v2
```

#### 新增的依赖
```bash
qiniu==7.17.0
```

## 迁移步骤

### 1. 更新环境变量

更新您的 `.env` 文件或环境变量配置：

```bash
# 删除旧的阿里云 OSS 配置
unset OSS_ACCESS_KEY_ID
unset OSS_ACCESS_KEY_SECRET
unset OSS_DEFAULT_REGION
unset OSS_DEFAULT_BUCKET
unset OSS_DEFAULT_ENDPOINT

# 添加新的七牛云配置
export QINIU_ACCESS_KEY=your-qiniu-access-key
export QINIU_SECRET_KEY=your-qiniu-secret-key
export QINIU_DEFAULT_BUCKET=your-qiniu-bucket
export QINIU_BUCKET_DOMAIN=your-bucket-domain.com
export QINIU_REGION=cn-east-1
```

### 2. 安装新依赖

```bash
pip install qiniu
# 或使用 conda
conda install -c conda-forge qiniu
```

### 3. 创建七牛云存储空间

1. 登录 [七牛云控制台](https://portal.qiniu.com/)
2. 创建新的存储空间（存储桶）
3. 获取存储空间的域名
4. 在个人中心获取 AccessKey 和 SecretKey

### 4. 更新 API 调用

如果您的代码中有直接调用 OSS 上传 API，需要更新端点：

```python
# 旧代码
response = requests.post("/manage/oss/upload", ...)

# 新代码
response = requests.post("/manage/qiniu/upload", ...)
```

### 5. 数据迁移（如需要）

如果需要将已存储在阿里云 OSS 的文件迁移到七牛云：

1. 使用七牛云提供的迁移工具
2. 或编写脚本批量下载和上传文件

## 功能对比

| 功能 | 阿里云 OSS | 七牛云 |
|------|------------|--------|
| 文件上传 | ✅ | ✅ |
| 文件下载 | ✅ | ✅ |
| 文件夹管理 | ✅ | ✅ |
| 批量操作 | ✅ | ✅ |
| 私有存储 | ✅ | ✅ |
| CDN 加速 | ✅ | ✅ |
| 图片处理 | ✅ | ✅ |

## 注意事项

1. **域名配置**：七牛云需要配置存储桶域名（`QINIU_BUCKET_DOMAIN`），这是与阿里云 OSS 的主要区别
2. **区域设置**：七牛云的区域命名与阿里云不同，请参考七牛云文档
3. **API 兼容性**：虽然接口类似，但七牛云和阿里云的 API 响应格式可能有所不同

## 故障排除

### 问题 1：无法连接到七牛云

**解决方案**：
- 检查环境变量是否正确设置
- 验证 AccessKey 和 SecretKey 是否有效
- 确认存储桶名称和域名是否正确

### 问题 2：文件上传失败

**解决方案**：
- 检查存储桶权限设置
- 验证文件大小是否超过限制
- 查看详细错误日志

### 问题 3：文件下载链接无效

**解决方案**：
- 确认 `QINIU_BUCKET_DOMAIN` 配置正确
- 检查是否需要私有链接签名
- 验证文件是否存在

## 回滚方案

如果需要回滚到阿里云 OSS：

1. 恢复环境变量配置
2. 重新安装阿里云 OSS SDK
3. 修改 `DocumentSource` 常量
4. 恢复 API 端点

## 支持

如有问题，请联系：
- GitHub Issues: [提交问题](https://github.com/onyx-dot-app/onyx/issues)
- 七牛云文档: [官方文档](https://developer.qiniu.com/)
- Onyx 社区: [Slack](https://join.slack.com/t/onyx-dot-app/shared_invite/zt-34lu4m7xg-TsKGO6h8PDvR5W27zTdyhA)