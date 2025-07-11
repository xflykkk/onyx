# 📁 文件夹上传功能说明

## ✨ 新增功能

DeepInsight Chat 现在支持**文件夹上传**功能，可以一次性上传整个文件夹及其子文件夹中的所有支持的文件。

## 🚀 使用方式

### 1. **拖拽文件夹**
- 直接将文件夹从文件管理器拖拽到上传区域
- 系统会自动遍历文件夹及所有子文件夹
- 筛选并上传所有支持的文件类型

### 2. **点击选择文件夹**
- 点击 "Select Folder" 按钮
- 在文件选择器中选择目标文件夹
- 系统会处理文件夹中的所有文件

### 3. **混合上传**
- 可以同时拖拽文件和文件夹
- 系统会智能处理不同类型的输入
- 支持批量操作

## 📋 支持的文件类型

所有在 APP_CONFIG 中定义的文件类型都支持：

### 📄 文档类型
- PDF: `.pdf`
- Word: `.doc`, `.docx`
- 文本: `.txt`, `.rtf`, `.odt`

### 📊 表格类型
- Excel: `.xls`, `.xlsx`
- CSV: `.csv`
- OpenOffice: `.ods`

### 🖼️ 图片类型
- 常见格式: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`, `.webp`

### 🎨 演示文稿
- PowerPoint: `.ppt`, `.pptx`
- OpenOffice: `.odp`

### 🌐 网页文件
- HTML: `.html`, `.htm`
- 数据: `.xml`, `.json`
- Markdown: `.md`, `.markdown`

### 📦 压缩文件
- 压缩包: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`

### 💻 代码文件
- JavaScript: `.js`, `.jsx`, `.ts`, `.tsx`
- Python: `.py`
- Java: `.java`
- C/C++: `.c`, `.cpp`

## 🔧 技术实现

### 文件夹遍历算法
```typescript
// 递归遍历文件夹结构
const traverseFileTree = async (item: any, files: File[]): Promise<void> => {
  if (item.isFile) {
    // 处理文件，检查类型是否支持
    item.file((file: File) => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      if (APP_CONFIG.allowedFileTypes.includes(extension)) {
        files.push(file);
      }
    });
  } else if (item.isDirectory) {
    // 递归处理子文件夹
    const dirReader = item.createReader();
    dirReader.readEntries(async (entries: any[]) => {
      const promises = entries.map(entry => traverseFileTree(entry, files));
      await Promise.all(promises);
    });
  }
};
```

### 浏览器 API 支持
- **File System Access API**: 现代浏览器支持
- **webkitdirectory**: 文件夹选择器
- **DataTransfer API**: 拖拽文件夹支持

## 📊 处理进度显示

### 实时反馈
- ✅ **Processing folder...**: 正在处理文件夹
- ✅ **文件计数**: 显示已处理/总文件数
- ✅ **旋转动画**: 视觉处理指示器
- ✅ **禁用交互**: 处理期间防止重复操作

### 状态管理
```typescript
const [processingFolder, setProcessingFolder] = useState(false);
const [folderStats, setFolderStats] = useState<{
  total: number; 
  processed: number;
} | null>(null);
```

## 🎯 用户体验优化

### 智能处理
- **自动过滤**: 只处理支持的文件类型
- **批量操作**: 一次上传大量文件
- **错误处理**: 优雅处理不支持的文件
- **进度反馈**: 实时显示处理状态

### 性能优化
- **异步处理**: 非阻塞文件夹遍历
- **内存管理**: 及时清理临时数据
- **取消机制**: 支持中断处理过程

## 🔒 安全考虑

### 文件验证
- **类型检查**: 基于文件扩展名过滤
- **大小限制**: 每个文件最大 10MB
- **数量限制**: 最多上传文件数限制

### 隐私保护
- **本地处理**: 文件夹遍历在客户端完成
- **选择性上传**: 只上传支持的文件类型
- **用户控制**: 完全由用户主导选择

## 🌐 浏览器兼容性

### 完全支持
- ✅ **Chrome 88+**
- ✅ **Firefox 87+**
- ✅ **Safari 14+**
- ✅ **Edge 88+**

### 降级处理
- 不支持的浏览器会隐藏文件夹上传选项
- 保持普通文件上传功能正常工作

## 📝 使用示例

### 典型使用场景

1. **文档项目上传**
   ```
   project-docs/
   ├── requirements/
   │   ├── spec.pdf
   │   └── user-stories.docx
   ├── design/
   │   ├── wireframes.png
   │   └── mockups.jpg
   └── implementation/
       ├── code-review.md
       └── test-plan.xlsx
   ```

2. **研究资料批量上传**
   ```
   research-papers/
   ├── 2023/
   │   ├── paper1.pdf
   │   └── paper2.pdf
   ├── 2024/
   │   ├── latest-research.pdf
   │   └── analysis.csv
   └── notes/
       ├── summary.md
       └── thoughts.txt
   ```

### 操作流程
1. **准备文件夹**: 组织好要上传的文档
2. **选择上传方式**: 拖拽或点击选择
3. **等待处理**: 系统遍历并过滤文件
4. **确认上传**: 查看文件列表并开始上传
5. **监控进度**: 实时查看索引状态

## 🚨 注意事项

### 性能考虑
- **大文件夹**: 包含大量文件的文件夹可能需要较长处理时间
- **网络限制**: 大量文件上传可能受网络速度影响
- **浏览器限制**: 某些浏览器对文件数量有限制

### 最佳实践
- **文件组织**: 提前整理好文档结构
- **格式统一**: 使用支持的文件格式
- **分批上传**: 超大文件夹考虑分批处理

## 🔮 未来增强

### 计划功能
- [ ] **进度条**: 显示具体的处理百分比
- [ ] **文件预览**: 上传前预览文件列表
- [ ] **选择性上传**: 允许用户取消选择特定文件
- [ ] **断点续传**: 大文件夹上传中断后继续
- [ ] **压缩上传**: 自动压缩小文件减少网络传输

---

🎉 **开始使用文件夹上传功能，让文档管理更加高效！**