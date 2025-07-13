import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Folder,
  FolderPlus,
  Upload,
  File,
  Trash2,
  RefreshCw,
  CheckCircle,
  Clock,
  AlertCircle,
  Search,
  Filter,
  MoreHorizontal,
  Edit,
  Download,
  Eye,
  X,
} from 'lucide-react';
import { UserFolder, UserFile } from '@/lib/userDocuments';
import { cn } from '@/lib/utils';

interface FileLibraryProps {
  variant?: 'glassmorphism' | 'neumorphic';
  className?: string;
  // 从 useUserDocuments 传递的状态和方法
  folders: UserFolder[];
  selectedFolderId: number | null;
  currentFolderFiles: UserFile[];
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;
  uploadProgress: Record<string, number>;
  indexingStatuses: Record<string, 'indexed' | 'indexing' | 'failed'>;
  // 操作方法
  selectFolder: (folderId: number | null) => void;
  createFolder: () => Promise<UserFolder>;
  deleteFolder: (folderId: number) => Promise<void>;
  uploadFiles: (files: File[]) => Promise<void>;
  deleteFile: (fileId: number) => Promise<void>;
  reindexFile: (fileId: number) => Promise<void>;
  clearError: () => void;
}

interface FolderListProps {
  folders: UserFolder[];
  selectedFolderId: number | null;
  onSelectFolder: (folderId: number | null) => void;
  onCreateFolder: () => void;
  onDeleteFolder: (folderId: number) => void;
  variant: 'glassmorphism' | 'neumorphic';
  isLoading: boolean;
}

interface FileListProps {
  files: UserFile[];
  onUploadFiles: (files: File[]) => void;
  onDeleteFile: (fileId: number) => void;
  onReindexFile: (fileId: number) => void;
  selectedFolderId: number | null;
  folders: UserFolder[];
  variant: 'glassmorphism' | 'neumorphic';
  isLoading: boolean;
  isUploading: boolean;
  indexingStatuses: Record<string, 'indexed' | 'indexing' | 'failed'>;
  uploadProgress: Record<string, number>;
}

interface FileItemProps {
  file: UserFile;
  onDelete: (fileId: number) => void;
  onReindex: (fileId: number) => void;
  indexingStatus: 'indexed' | 'indexing' | 'failed' | undefined;
  variant: 'glassmorphism' | 'neumorphic';
}

// 文件夹列表组件
const FolderList: React.FC<FolderListProps> = ({
  folders,
  selectedFolderId,
  onSelectFolder,
  onCreateFolder,
  onDeleteFolder,
  variant,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredFolders = folders.filter(folder =>
    folder.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* 标题和操作 */}
      <div className="flex items-center justify-between flex-shrink-0">
        <h3 className={cn(
          'text-lg font-semibold',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
        )}>
          文件夹
        </h3>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            console.log('创建文件夹按钮被点击');
            onCreateFolder();
          }}
          disabled={isLoading}
          className={cn(
            'flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm font-medium',
            variant === 'glassmorphism'
              ? 'glass-light text-glass hover:glass-effect'
              : 'neuro-flat text-gray-600 hover:neuro-raised',
            isLoading && 'opacity-50 cursor-not-allowed'
          )}
          title="创建新文件夹"
        >
          <FolderPlus className="w-4 h-4" />
          <span className="hidden sm:inline">新建</span>
        </motion.button>
      </div>

      {/* 搜索框 */}
      <div className="relative flex-shrink-0">
        <Search className={cn(
          'absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-400'
        )} />
        <input
          type="text"
          placeholder="搜索文件夹..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={cn(
            'w-full pl-10 pr-4 py-2 rounded-lg border transition-all',
            variant === 'glassmorphism'
              ? 'glass-light border-white/20 text-glass placeholder-white/50'
              : 'neuro-flat border-gray-200 text-gray-700 placeholder-gray-400'
          )}
        />
      </div>

      {/* 文件夹列表 */}
      <div className="flex-1 space-y-2 overflow-y-auto min-h-0">
        {/* 全部文件选项 */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => {
            console.log('🖱️ 点击全部文件');
            onSelectFolder(null);
          }}
          className={cn(
            'w-full flex items-center space-x-3 p-3 rounded-lg border text-left transition-all',
            selectedFolderId === null
              ? variant === 'glassmorphism'
                ? 'glass-effect border-white/40 text-white'
                : 'neuro-pressed border-blue-200 bg-blue-50 text-blue-800'
              : variant === 'glassmorphism'
                ? 'glass-light border-white/20 text-glass hover:glass-effect'
                : 'neuro-flat border-gray-200 text-gray-600 hover:neuro-raised'
          )}
        >
          <Folder className="w-5 h-5" />
          <div className="flex-1">
            <div className="font-medium">全部文件</div>
            <div className="text-xs opacity-70">显示所有文件夹中的文件</div>
          </div>
        </motion.button>

        {/* 文件夹项目 */}
        <AnimatePresence>
          {filteredFolders.map((folder) => (
            <motion.div
              key={folder.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              layout
              className={cn(
                'flex items-center space-x-3 p-3 rounded-lg border text-left transition-all group cursor-pointer',
                selectedFolderId === folder.id
                  ? variant === 'glassmorphism'
                    ? 'glass-effect border-blue-400/60 text-white bg-blue-500/30 shadow-lg'
                    : 'neuro-pressed border-blue-200 bg-blue-50 text-blue-800'
                  : variant === 'glassmorphism'
                    ? 'glass-light border-white/20 text-glass hover:glass-effect'
                    : 'neuro-flat border-gray-200 text-gray-600 hover:neuro-raised'
              )}
              onClick={() => {
                console.log('🖱️ 点击文件夹容器:', folder.id, folder.name);
                onSelectFolder(folder.id);
              }}
            >
              <Folder className="w-5 h-5" />
              <div className="flex-1">
                <div className="font-medium">
                  {(() => {
                    // 检查是否包含时间戳格式 (M/d HH:mm)
                    const timestampMatch = folder.name.match(/^(.+?)\s*\((\d{1,2}\/\d{1,2}\s+\d{1,2}:\d{1,2})\)$/);
                    if (timestampMatch) {
                      const [, folderName, timestamp] = timestampMatch;
                      return (
                        <>
                          {folderName}
                          <span className="text-xs font-normal opacity-70 ml-1">({timestamp})</span>
                        </>
                      );
                    }
                    return folder.name;
                  })()}
                </div>
                {folder.description && (
                  <div className="text-xs opacity-70">{folder.description}</div>
                )}
              </div>
              
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={(e) => {
                  e.stopPropagation(); // 阻止事件冒泡到父级div
                  console.log('🗑️ 点击删除文件夹:', folder.id);
                  onDeleteFolder(folder.id);
                }}
                className={cn(
                  'p-1 rounded transition-colors opacity-0 group-hover:opacity-100',
                  variant === 'glassmorphism'
                    ? 'hover:bg-red-500/20 text-red-200'
                    : 'hover:bg-red-50 text-red-500'
                )}
                title="删除文件夹"
              >
                <Trash2 className="w-4 h-4" />
              </motion.button>
            </motion.div>
          ))}
        </AnimatePresence>

        {filteredFolders.length === 0 && searchTerm && (
          <div className={cn(
            'text-center py-8',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-500'
          )}>
            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>未找到匹配的文件夹</p>
          </div>
        )}
      </div>
    </div>
  );
};

// 文件项组件
const FileItem: React.FC<FileItemProps> = ({
  file,
  onDelete,
  onReindex,
  indexingStatus,
  variant,
}) => {
  const [showActions, setShowActions] = useState(false);

  const getStatusIcon = () => {
    switch (indexingStatus) {
      case 'indexed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'indexing':
        return <Clock className="w-4 h-4 text-yellow-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (indexingStatus) {
      case 'indexed':
        return '已索引';
      case 'indexing':
        return '索引中';
      case 'failed':
        return '索引失败';
      default:
        return '等待索引';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatFileDate = (dateStr: string) => {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '未知时间';
    
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hours = date.getHours();
    const minutes = date.getMinutes();
    
    const formattedHours = hours.toString().padStart(2, '0');
    const formattedMinutes = minutes.toString().padStart(2, '0');
    
    return `${month}/${day} ${formattedHours}:${formattedMinutes}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      layout
      className={cn(
        'flex items-center space-x-3 p-3 rounded-lg border transition-all group',
        variant === 'glassmorphism'
          ? 'glass-light border-white/20 hover:glass-effect'
          : 'neuro-flat border-gray-200 hover:neuro-raised'
      )}
    >
      <File className={cn(
        'w-5 h-5',
        variant === 'glassmorphism' ? 'text-glass' : 'text-gray-500'
      )} />
      
      <div className="flex-1 min-w-0">
        <div className={cn(
          'font-medium truncate',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
        )}>
          {file.display_name || file.name || '未知文件'}
        </div>
        <div className={cn(
          'text-xs opacity-70 flex items-center space-x-2',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-500'
        )}>
          <span>{formatFileSize(file.file_size_bytes || 0)}</span>
          <span>•</span>
          <span>{file.created_at ? formatFileDate(file.created_at) : '未知时间'}</span>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        {getStatusIcon()}
        <span className={cn(
          'text-xs',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-500'
        )}>
          {getStatusText()}
        </span>
      </div>

      <div className="relative">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowActions(!showActions)}
          className={cn(
            'p-1 rounded transition-colors opacity-0 group-hover:opacity-100',
            variant === 'glassmorphism'
              ? 'hover:glass-effect text-glass'
              : 'hover:neuro-flat text-gray-500'
          )}
        >
          <MoreHorizontal className="w-4 h-4" />
        </motion.button>

        <AnimatePresence>
          {showActions && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className={cn(
                'absolute right-0 top-8 z-10 min-w-32 p-2 rounded-lg border shadow-lg',
                variant === 'glassmorphism'
                  ? 'glass-strong border-white/20 backdrop-blur-xl'
                  : 'bg-white border-gray-200'
              )}
            >
              {indexingStatus === 'failed' && (
                <button
                  onClick={() => {
                    onReindex(file.id);
                    setShowActions(false);
                  }}
                  className={cn(
                    'w-full flex items-center space-x-2 px-3 py-2 rounded text-left text-sm transition-colors',
                    variant === 'glassmorphism'
                      ? 'hover:glass-effect text-glass'
                      : 'hover:bg-gray-50 text-gray-700'
                  )}
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>重新索引</span>
                </button>
              )}
              
              <button
                onClick={() => {
                  onDelete(file.id);
                  setShowActions(false);
                }}
                className={cn(
                  'w-full flex items-center space-x-2 px-3 py-2 rounded text-left text-sm transition-colors',
                  variant === 'glassmorphism'
                    ? 'hover:bg-red-500/20 text-red-200'
                    : 'hover:bg-red-50 text-red-600'
                )}
              >
                <Trash2 className="w-4 h-4" />
                <span>删除</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

// 文件列表组件
const FileList: React.FC<FileListProps> = ({
  files,
  onUploadFiles,
  onDeleteFile,
  onReindexFile,
  selectedFolderId,
  folders,
  variant,
  isLoading,
  isUploading,
  indexingStatuses,
  uploadProgress,
}) => {
  const [dragOver, setDragOver] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredFiles = files.filter(file => {
    if (!searchTerm.trim()) return true;
    
    const searchLower = searchTerm.toLowerCase();
    const displayName = file.display_name || file.name || '';
    const fileName = file.name || '';
    
    return displayName.toLowerCase().includes(searchLower) || 
           fileName.toLowerCase().includes(searchLower);
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    if (!selectedFolderId) {
      console.warn('请先选择一个文件夹');
      return;
    }
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      onUploadFiles(droppedFiles);
    }
  }, [onUploadFiles, selectedFolderId]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedFolderId) {
      console.warn('请先选择一个文件夹');
      e.target.value = '';
      return;
    }
    
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 0) {
      onUploadFiles(selectedFiles);
    }
    // 清除input值，允许重新选择同一文件
    e.target.value = '';
  }, [onUploadFiles, selectedFolderId]);

  return (
    <div className="space-y-4">
      {/* 标题和操作 */}
      <div className="flex items-center justify-between">
        <h3 className={cn(
          'text-lg font-semibold',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
        )}>
          文件 {selectedFolderId ? (() => {
            const folderName = folders.find(f => f.id === selectedFolderId)?.name || '未知文件夹';
            // 检查是否包含时间戳格式 (M/d HH:mm)
            const timestampMatch = folderName.match(/^(.+?)\s*\((\d{1,2}\/\d{1,2}\s+\d{1,2}:\d{1,2})\)$/);
            if (timestampMatch) {
              const [, name, timestamp] = timestampMatch;
              return (
                <>
                  ({name}
                  <span className="text-sm font-normal opacity-70 ml-1">({timestamp})</span>
                  )
                </>
              );
            }
            return `(${folderName})`;
          })() : '(全部)'}
        </h3>
        <div className="flex space-x-2">
          <label 
            className={cn(
              'flex flex-col items-center space-y-1 px-3 py-2 rounded-lg transition-all font-medium',
              selectedFolderId && !isLoading && !isUploading
                ? 'cursor-pointer' +
                  (variant === 'glassmorphism'
                    ? ' glass-light text-glass hover:glass-effect'
                    : ' neuro-flat text-gray-600 hover:neuro-raised')
                : 'opacity-50 cursor-not-allowed' +
                  (variant === 'glassmorphism'
                    ? ' glass-light text-glass'
                    : ' neuro-flat text-gray-600')
            )}
            title={!selectedFolderId ? '请先选择一个文件夹' : '上传文件'}
          >
            <Upload className="w-6 h-6" />
            <span className="text-xs hidden sm:inline">
              {!selectedFolderId ? '选择文件夹' : '上传'}
            </span>
            <input
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
              disabled={isLoading || isUploading || !selectedFolderId}
            />
          </label>
        </div>
      </div>

      {/* 搜索框 */}
      <div className="relative">
        <Search className={cn(
          'absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-400'
        )} />
        <input
          type="text"
          placeholder="搜索文件..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={cn(
            'w-full pl-10 pr-4 py-2 rounded-lg border transition-all',
            variant === 'glassmorphism'
              ? 'glass-light border-white/20 text-glass placeholder-white/50'
              : 'neuro-flat border-gray-200 text-gray-700 placeholder-gray-400'
          )}
        />
      </div>

      {/* 文件上传区域 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'border-2 border-dashed rounded-lg p-6 transition-all text-center',
          dragOver
            ? 'border-blue-400 bg-blue-50/50'
            : variant === 'glassmorphism'
              ? 'border-white/20 text-glass'
              : 'border-gray-300 text-gray-500',
          isUploading && 'opacity-50',
          !selectedFolderId && 'opacity-50'
        )}
      >
        {!selectedFolderId ? (
          <>
            <Folder className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="font-medium">请先选择或创建一个文件夹</p>
            <p className="text-sm opacity-70">选择文件夹后即可上传文件</p>
          </>
        ) : isUploading ? (
          <div className="space-y-2">
            <Upload className="w-8 h-8 mx-auto animate-bounce" />
            <p className="font-medium">上传中...</p>
            {Object.entries(uploadProgress).map(([key, progress]) => (
              <div key={key} className="space-y-1">
                <p className="text-sm">{key.split('_')[0]}</p>
                <div className={cn(
                  'w-full h-2 rounded-full overflow-hidden',
                  variant === 'glassmorphism' ? 'bg-white/20' : 'bg-gray-200'
                )}>
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <>
            <Upload className="w-8 h-8 mx-auto mb-2" />
            <p className="font-medium">拖拽文件到这里或点击上传</p>
            <p className="text-sm opacity-70">支持多文件上传</p>
          </>
        )}
      </div>

      {/* 文件列表 */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        <AnimatePresence>
          {filteredFiles.map((file) => {
            const status = indexingStatuses[file.file_id];
            console.log(`🎨 渲染文件 ${file.id}:`, {
              fileName: file.name,
              fileId: file.file_id,
              indexingStatus: status,
              allStatuses: indexingStatuses
            });
            return (
              <FileItem
                key={file.id}
                file={file}
                onDelete={onDeleteFile}
                onReindex={onReindexFile}
                indexingStatus={status}
                variant={variant}
              />
            );
          })}
        </AnimatePresence>

        {filteredFiles.length === 0 && !selectedFolderId && (
          <div className={cn(
            'text-center py-8',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-500'
          )}>
            <Folder className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>请选择一个文件夹查看文件</p>
          </div>
        )}

        {filteredFiles.length === 0 && selectedFolderId && !searchTerm && (
          <div className={cn(
            'text-center py-8',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-500'
          )}>
            <File className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>这个文件夹还没有文件</p>
            <p className="text-sm opacity-70">拖拽文件或点击上传按钮添加文件</p>
          </div>
        )}

        {filteredFiles.length === 0 && searchTerm && (
          <div className={cn(
            'text-center py-8',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-500'
          )}>
            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>未找到匹配的文件</p>
          </div>
        )}
      </div>
    </div>
  );
};

// 主组件
export const FileLibrary: React.FC<FileLibraryProps> = ({
  variant = 'glassmorphism',
  className,
  // 接收通过 props 传递的状态
  folders,
  selectedFolderId,
  currentFolderFiles,
  isLoading,
  isUploading,
  error,
  uploadProgress,
  indexingStatuses,
  // 接收通过 props 传递的方法
  selectFolder,
  createFolder,
  deleteFolder,
  uploadFiles,
  deleteFile,
  reindexFile,
  clearError,
}) => {
  const handleCreateFolder = useCallback(async () => {
    console.log('🆕 开始创建文件夹...');
    try {
      const newFolder = await createFolder();
      console.log('✅ 文件夹创建成功:', newFolder);
      console.log('📁 文件夹ID:', newFolder.id, '名称:', newFolder.name);
    } catch (error) {
      console.error('❌ 创建文件夹失败:', error);
    }
  }, [createFolder]);

  return (
    <div className={cn('h-full flex flex-col lg:grid lg:grid-cols-2 gap-6', className)}>
      {/* 文件夹列表 */}
      <div className={cn(
        'p-4 rounded-xl border flex flex-col min-h-0',
        variant === 'glassmorphism'
          ? 'glass-strong border-white/20'
          : 'neuro-raised bg-white border-gray-200'
      )}>
        <FolderList
          folders={folders}
          selectedFolderId={selectedFolderId}
          onSelectFolder={(folderId) => {
            console.log('📁 FileLibrary 调用 selectFolder:', folderId);
            selectFolder(folderId);
          }}
          onCreateFolder={handleCreateFolder}
          onDeleteFolder={deleteFolder}
          variant={variant}
          isLoading={isLoading}
        />
      </div>

      {/* 文件列表 */}
      <div className={cn(
        'p-4 rounded-xl border flex flex-col min-h-0',
        variant === 'glassmorphism'
          ? 'glass-strong border-white/20'
          : 'neuro-raised bg-white border-gray-200'
      )}>
        <FileList
          files={currentFolderFiles}
          onUploadFiles={uploadFiles}
          onDeleteFile={deleteFile}
          onReindexFile={reindexFile}
          selectedFolderId={selectedFolderId}
          folders={folders}
          variant={variant}
          isLoading={isLoading}
          isUploading={isUploading}
          indexingStatuses={indexingStatuses}
          uploadProgress={uploadProgress}
        />
      </div>

      {/* 错误提示 */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className={cn(
              'fixed bottom-4 right-4 z-50 max-w-md p-4 rounded-lg border shadow-lg',
              variant === 'glassmorphism'
                ? 'glass-strong border-red-400/40 text-red-200'
                : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="font-medium">错误</p>
                <p className="text-sm opacity-90">{error}</p>
              </div>
              <button
                onClick={clearError}
                className={cn(
                  'ml-3 p-1 rounded transition-colors',
                  variant === 'glassmorphism'
                    ? 'hover:glass-effect text-red-200'
                    : 'hover:bg-red-100 text-red-600'
                )}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FileLibrary; 