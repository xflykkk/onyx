import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  UserFolder,
  UserFile,
  CreateFolderRequest,
  getUserFolders,
  createUserFolder,
  deleteUserFolder,
  getFolderFiles,
  uploadFilesToFolder,
  deleteUserFile,
  getFileIndexingStatus,
  reindexUserFile,
  generateRandomFolderName,
  UserDocumentAPIError,
} from '@/lib/userDocuments';

// Hook状态类型
export interface UserDocumentState {
  folders: UserFolder[];
  selectedFolderId: number | null;
  currentFolderFiles: UserFile[];
  isLoading: boolean;
  isUploading: boolean;
  uploadProgress: Record<string, number>;
  error: string | null;
  indexingStatuses: Record<string, 'indexed' | 'indexing' | 'failed'>;
}

// Hook返回类型
export interface UseUserDocumentsReturn {
  // 状态
  state: UserDocumentState;
  
  // 文件夹操作
  folders: UserFolder[];
  selectedFolderId: number | null;
  selectFolder: (folderId: number | null) => void;
  createFolder: (request?: CreateFolderRequest) => Promise<UserFolder>;
  deleteFolder: (folderId: number) => Promise<void>;
  refreshFolders: () => Promise<void>;
  
  // 文件操作
  currentFolderFiles: UserFile[];
  uploadFiles: (files: File[], folderId?: number) => Promise<void>;
  deleteFile: (fileId: number) => Promise<void>;
  reindexFile: (fileId: number) => Promise<void>;
  refreshFiles: () => Promise<void>;
  
  // 工具函数
  getSelectedFileIds: () => string[];
  getFileById: (fileId: number) => UserFile | undefined;
  getTotalFilesCount: () => number;
  getIndexedFilesCount: () => number;
  
  // 状态控制
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;
  clearError: () => void;
  uploadProgress: Record<string, number>;
  
}

// 本地存储键
const STORAGE_KEYS = {
  selectedFolderId: 'onyx-selected-folder-id',
  folders: 'onyx-user-folders',
  folderFiles: 'onyx-folder-files',
} as const;

export function useUserDocuments(): UseUserDocumentsReturn {
  // 状态管理
  const [state, setState] = useState<UserDocumentState>({
    folders: [],
    selectedFolderId: null,
    currentFolderFiles: [],
    isLoading: false,
    isUploading: false,
    uploadProgress: {},
    error: null,
    indexingStatuses: {},
  });

  // 索引状态轮询引用
  const indexingPollingRef = useRef<NodeJS.Timeout | null>(null);

  // 错误处理
  const handleError = useCallback((error: unknown, defaultMessage: string) => {
    const errorMessage = error instanceof UserDocumentAPIError 
      ? error.message 
      : error instanceof Error 
      ? error.message 
      : defaultMessage;
    
    setState(prev => ({ ...prev, error: errorMessage, isLoading: false, isUploading: false }));
    console.error(defaultMessage, error);
  }, []);

  // 清除错误
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // 从本地存储加载选中的文件夹ID
  const loadSelectedFolderFromStorage = useCallback(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.selectedFolderId);
      if (saved) {
        const folderId = parseInt(saved, 10);
        setState(prev => ({ ...prev, selectedFolderId: folderId }));
        return folderId;
      }
    } catch (error) {
      console.warn('Failed to load selected folder from storage:', error);
    }
    return null;
  }, []);

  // 保存选中的文件夹ID到本地存储
  const saveSelectedFolderToStorage = useCallback((folderId: number | null) => {
    try {
      if (folderId === null) {
        localStorage.removeItem(STORAGE_KEYS.selectedFolderId);
      } else {
        localStorage.setItem(STORAGE_KEYS.selectedFolderId, folderId.toString());
      }
    } catch (error) {
      console.warn('Failed to save selected folder to storage:', error);
    }
  }, []);

  // 获取文件夹列表
  const refreshFolders = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const folders = await getUserFolders();
      console.log('📂 刷新文件夹列表，从服务器获取到:', folders.length, '个文件夹');
      
      setState(prev => {
        console.log('📋 当前状态中的文件夹:', prev.folders.length, '个');
        
        // 合并服务器文件夹和本地文件夹，避免丢失新创建的文件夹
        const existingIds = new Set(folders.map(f => f.id));
        const localOnlyFolders = prev.folders.filter(f => !existingIds.has(f.id));
        
        // 如果有本地独有的文件夹（刚创建的），保留它们
        const mergedFolders = [...folders, ...localOnlyFolders];
        console.log('🔄 合并后的文件夹列表:', mergedFolders.length, '个文件夹');
        
        // 如果当前选中的文件夹不存在，清除选择
        const currentSelectedId = prev.selectedFolderId;
        if (currentSelectedId && !mergedFolders.find(f => f.id === currentSelectedId)) {
          console.log('⚠️ 当前选中的文件夹不存在，清除选择');
          saveSelectedFolderToStorage(null);
          return { ...prev, folders: mergedFolders, selectedFolderId: null, isLoading: false };
        }
        
        return { ...prev, folders: mergedFolders, isLoading: false };
      });
    } catch (error) {
      handleError(error, '获取文件夹列表失败');
    }
  }, [handleError, saveSelectedFolderToStorage]);

  // 创建文件夹
  const createFolder = useCallback(async (request?: CreateFolderRequest): Promise<UserFolder> => {
    console.log('🆕 开始创建文件夹');
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const folderRequest = request || {
        name: generateRandomFolderName(),
        description: '自动创建的文档库'
      };
      
      console.log('📤 发送创建文件夹请求:', folderRequest);
      const newFolder = await createUserFolder(folderRequest);
      console.log('✅ 文件夹创建成功:', newFolder);
      
      // 立即将新文件夹添加到当前列表中，并选择它
      
      setState(prev => {
        const updatedFolders = [...prev.folders, newFolder];
        console.log('📁 更新后的文件夹列表:', updatedFolders);
        saveSelectedFolderToStorage(newFolder.id);
        return { 
          ...prev, 
          folders: updatedFolders,
          selectedFolderId: newFolder.id,
          currentFolderFiles: [], // 新文件夹没有文件
          isLoading: false 
        };
      });
      
      console.log('🎯 文件夹创建并选择完成:', newFolder.id);
      
      // 延迟刷新文件夹列表以确保服务器数据同步
      setTimeout(() => {
        refreshFolders().catch(console.error);
      }, 2000); // 给服务器更多时间同步数据
      
      return newFolder;
    } catch (error) {
      console.error('❌ 创建文件夹时发生错误:', error);
      handleError(error, '创建文件夹失败');
      throw error;
    }
  }, [handleError, saveSelectedFolderToStorage, refreshFolders]);

  // 删除文件夹
  const deleteFolder = useCallback(async (folderId: number) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      await deleteUserFolder(folderId);
      
      // 如果删除的是当前选中的文件夹，清除选择
      setState(prev => {
        if (prev.selectedFolderId === folderId) {
          saveSelectedFolderToStorage(null);
          return { ...prev, selectedFolderId: null, currentFolderFiles: [] };
        }
        return prev;
      });
      
      // 刷新文件夹列表
      await refreshFolders();
      
      setState(prev => ({ ...prev, isLoading: false }));
    } catch (error) {
      handleError(error, '删除文件夹失败');
    }
  }, [refreshFolders, handleError, saveSelectedFolderToStorage]);

  // 选择文件夹
  const selectFolder = useCallback((folderId: number | null) => {
    console.log('📁 选择文件夹:', folderId);
    // 无论如何都保存到本地存储
    saveSelectedFolderToStorage(folderId);
    
    setState(prev => {
      console.log('📁 当前状态:', prev.selectedFolderId, '-> 新状态:', folderId);
      // 总是创建新的状态对象来触发重新渲染
      return { 
        ...prev, 
        selectedFolderId: folderId,
        currentFolderFiles: prev.selectedFolderId === folderId ? prev.currentFolderFiles : []
      };
    });
  }, [saveSelectedFolderToStorage]);

  // 获取文件夹中的文件
  const refreshFiles = useCallback(async () => {
    setState(prev => {
      const currentSelectedId = prev.selectedFolderId;
      if (!currentSelectedId) {
        return { ...prev, currentFolderFiles: [] };
      }
      
      return { ...prev, isLoading: true, error: null };
    });
    
    // 使用当前状态中的 selectedFolderId
    const currentSelectedId = state.selectedFolderId;
    if (!currentSelectedId) {
      return;
    }
    
    try {
      console.log('刷新文件列表，文件夹ID:', currentSelectedId);
      const files = await getFolderFiles(currentSelectedId);
      console.log('获取到文件列表:', files);
      
      setState(prev => ({ ...prev, currentFolderFiles: files, isLoading: false }));
      
      // 检查文件索引状态
      if (files.length > 0) {
        const fileIds = files.map(f => f.id).filter(Boolean);
        if (fileIds.length > 0) {
          try {
            const statusResponse = await getFileIndexingStatus(fileIds);
            console.log('索引状态响应:', statusResponse);
            console.log('当前文件列表:', files);
            
            // statusResponse 是 Record<number, boolean> 格式
            // 通过 UserFile ID 来映射到 file_id
            const needPollingFileIds: number[] = [];
            
            setState(prev => {
              const newIndexingStatuses = { ...prev.indexingStatuses };
              
              Object.entries(statusResponse || {}).forEach(([userFileIdStr, isIndexed]) => {
                const userFileId = parseInt(userFileIdStr);
                const file = files?.find(f => f.id === userFileId);
                console.log(`处理文件 ${userFileId}: isIndexed=${isIndexed}, 找到文件:`, file);
                if (file && file.file_id) {
                  const newStatus = isIndexed ? 'indexed' : 'indexing';
                  newIndexingStatuses[file.file_id] = newStatus;
                  console.log(`设置索引状态: ${file.file_id} -> ${newStatus}`);
                  
                  // 如果文件还在索引中，添加到需要轮询的列表
                  if (!isIndexed) {
                    needPollingFileIds.push(userFileId);
                  }
                }
              });
              
              return { ...prev, indexingStatuses: newIndexingStatuses };
            });
            
            // 如果有需要轮询的文件，启动轮询
            if (needPollingFileIds.length > 0) {
              console.log('🚀 refreshFiles中启动轮询，文件ID:', needPollingFileIds);
              // 使用setTimeout避免依赖问题
              setTimeout(() => {
                startIndexingPolling(needPollingFileIds);
              }, 0);
            }
          } catch (statusError) {
            console.warn('Failed to get indexing status:', statusError);
          }
        }
      }
    } catch (error) {
      handleError(error, '获取文件列表失败');
    }
  }, [state.selectedFolderId, handleError]);

  // 上传文件
  const uploadFiles = useCallback(async (files: File[], folderId?: number) => {
    const targetFolderId = folderId || state.selectedFolderId;
    
    console.log('上传文件请求:', { files: files.length, targetFolderId, selectedFolderId: state.selectedFolderId });
    
    if (!targetFolderId) {
      const errorMsg = '请先选择一个文件夹后再上传文件';
      console.warn(errorMsg);
      setState(prev => ({ ...prev, error: errorMsg }));
      return;
    }
    
    setState(prev => ({ ...prev, isUploading: true, error: null, uploadProgress: {} }));
    
    try {
      // 模拟上传进度
      const progressInterval = setInterval(() => {
        setState(prev => {
          const newProgress = { ...prev.uploadProgress };
          files.forEach((file, index) => {
            const currentProgress = newProgress[`${file.name}_${index}`] || 0;
            if (currentProgress < 90) {
              newProgress[`${file.name}_${index}`] = Math.min(currentProgress + Math.random() * 20, 90);
            }
          });
          return { ...prev, uploadProgress: newProgress };
        });
      }, 500);
      
      const uploadResults = await uploadFilesToFolder(files, targetFolderId);
      console.log('文件上传完成，结果:', uploadResults);
      
      clearInterval(progressInterval);
      
      // 设置上传完成进度
      setState(prev => {
        const newProgress = { ...prev.uploadProgress };
        files.forEach((file, index) => {
          newProgress[`${file.name}_${index}`] = 100;
        });
        return { ...prev, uploadProgress: newProgress };
      });
      
      // 刷新文件列表
      console.log('正在刷新文件列表...');
      await refreshFiles();
      console.log('文件列表刷新完成');
      
      // 为新上传的文件设置初始索引状态并启动轮询
      if (uploadResults.length > 0) {
        setState(prev => {
          const newIndexingStatuses = { ...prev.indexingStatuses };
          
          // 为新上传的文件设置初始状态为 'indexing'
          uploadResults.forEach(result => {
            if (result.file_id) {
              newIndexingStatuses[result.file_id] = 'indexing';
              console.log(`设置新文件初始索引状态: ${result.file_id} -> indexing`);
            }
          });
          
          return { ...prev, indexingStatuses: newIndexingStatuses };
        });
        
        // 使用上传结果的 id（UserFile ID）进行轮询
        startIndexingPolling(uploadResults.map(r => r.id));
      } else {
        // 如果 uploadResults 为空，尝试从刷新的文件列表中找到需要轮询的文件
        console.log('⚠️ uploadResults为空，尝试从文件列表中找到需要轮询的文件');
        
        // 从当前文件列表中查找状态为 INDEXING 的文件
        setState(prev => {
          const filesToPoll = prev.currentFolderFiles.filter(file => 
            file.status === 'INDEXING' && file.file_id
          );
          
          console.log('📋 发现需要轮询的文件:', filesToPoll.map(f => ({id: f.id, name: f.name, file_id: f.file_id})));
          
          if (filesToPoll.length > 0) {
            // 设置这些文件的初始索引状态
            const newIndexingStatuses = { ...prev.indexingStatuses };
            filesToPoll.forEach(file => {
              if (file.file_id) {
                newIndexingStatuses[file.file_id] = 'indexing';
                console.log(`设置文件初始索引状态: ${file.file_id} -> indexing`);
              }
            });
            
            // 启动轮询
            setTimeout(() => {
              startIndexingPolling(filesToPoll.map(f => f.id));
            }, 0);
            
            return { ...prev, indexingStatuses: newIndexingStatuses };
          }
          
          return prev;
        });
      }
      
      setState(prev => ({ ...prev, isUploading: false, uploadProgress: {} }));
    } catch (error) {
      handleError(error, '上传文件失败');
    }
  }, [state.selectedFolderId, refreshFiles, handleError]);

  // 删除文件
  const deleteFile = useCallback(async (fileId: number) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      await deleteUserFile(fileId);
      await refreshFiles();
      setState(prev => ({ ...prev, isLoading: false }));
    } catch (error) {
      handleError(error, '删除文件失败');
    }
  }, [refreshFiles, handleError]);

  // 重新索引文件
  const reindexFile = useCallback(async (fileId: number) => {
    setState(prev => ({ ...prev, error: null }));
    
    try {
      await reindexUserFile(fileId);
      await refreshFiles();
    } catch (error) {
      handleError(error, '重新索引文件失败');
    }
  }, [refreshFiles, handleError]);

  // 开始索引状态轮询
  const startIndexingPolling = useCallback((userFileIds: number[]) => {
    if (!userFileIds || userFileIds.length === 0) {
      console.log('⚠️ 没有需要轮询的文件ID');
      return;
    }
    
    console.log('🚀 开始轮询文件索引状态:', userFileIds);
    
    if (indexingPollingRef.current) {
      clearInterval(indexingPollingRef.current);
    }
    
    let pollAttempts = 0;
    const MAX_POLL_ATTEMPTS = 60; // 3分钟 (3秒 * 60 = 180秒)
    
    indexingPollingRef.current = setInterval(async () => {
      try {
        pollAttempts++;
        const statusResponse = await getFileIndexingStatus(userFileIds);
        console.log(`🔄 轮询索引状态响应 (第${pollAttempts}次):`, statusResponse);
        console.log('🔄 轮询的文件ID:', userFileIds);
        
        let allIndexed = true;
        let hasValidResponse = false;
        
        // statusResponse 是 Record<number, boolean> 格式
        // 需要通过 UserFile ID 映射到 file_id
        
        // 先处理状态逻辑，确定是否应该停止轮询
        Object.entries(statusResponse || {}).forEach(([userFileIdStr, isIndexed]) => {
          const userFileId = parseInt(userFileIdStr);
          hasValidResponse = true;
          if (!isIndexed) {
            allIndexed = false;
          }
        });
        
        // 然后更新 React 状态
        setState(prev => {
          const newIndexingStatuses = { ...prev.indexingStatuses };
          
          Object.entries(statusResponse || {}).forEach(([userFileIdStr, isIndexed]) => {
            const userFileId = parseInt(userFileIdStr);
            const file = prev.currentFolderFiles?.find(f => f.id === userFileId);
            console.log(`🔍 轮询处理文件 ${userFileId}: isIndexed=${isIndexed}, 找到文件:`, file);
            
            if (file && file.file_id) {
              const newStatus = isIndexed ? 'indexed' : 'indexing';
              const oldStatus = newIndexingStatuses[file.file_id];
              newIndexingStatuses[file.file_id] = newStatus;
              console.log(`🔄 轮询设置索引状态: ${file.file_id} -> ${newStatus} (从 ${oldStatus} 变为 ${newStatus})`);
              console.log(`📊 文件详细信息:`, {
                userFileId: file.id,
                fileId: file.file_id,
                fileName: file.name,
                isIndexed: isIndexed,
                oldStatus: oldStatus,
                newStatus: newStatus,
                allIndexingStatuses: newIndexingStatuses
              });
            } else {
              console.warn(`⚠️ 未找到文件 ${userFileId} 或 file_id 为空`);
            }
          });
          
          console.log('轮询最终索引状态:', newIndexingStatuses);
          console.log('轮询allIndexed:', allIndexed, 'hasValidResponse:', hasValidResponse);
          
          return { ...prev, indexingStatuses: newIndexingStatuses };
        });
        
        // 如果所有文件都已索引完成，或者达到最大轮询次数，停止轮询
        if ((allIndexed && hasValidResponse) || pollAttempts >= MAX_POLL_ATTEMPTS) {
          if (allIndexed && hasValidResponse) {
            console.log('✅ 所有文件索引完成，停止轮询');
          } else {
            console.log(`⏰ 达到最大轮询次数 (${MAX_POLL_ATTEMPTS})，停止轮询`);
          }
          
          if (indexingPollingRef.current) {
            clearInterval(indexingPollingRef.current);
            indexingPollingRef.current = null;
          }
        } else {
          console.log('🔄 继续轮询，原因:', {
            allIndexed: allIndexed,
            hasValidResponse: hasValidResponse,
            pollAttempts: pollAttempts,
            maxAttempts: MAX_POLL_ATTEMPTS,
            shouldStop: (allIndexed && hasValidResponse) || pollAttempts >= MAX_POLL_ATTEMPTS
          });
        }
      } catch (error) {
        console.warn('索引状态轮询失败:', error);
        pollAttempts++;
        
        // 如果轮询失败次数过多，停止轮询
        if (pollAttempts >= MAX_POLL_ATTEMPTS) {
          console.log('❌ 轮询失败次数过多，停止轮询');
          if (indexingPollingRef.current) {
            clearInterval(indexingPollingRef.current);
            indexingPollingRef.current = null;
          }
        }
      }
    }, 3000); // 每3秒检查一次
  }, []);

  // 停止索引状态轮询
  const stopIndexingPolling = useCallback(() => {
    if (indexingPollingRef.current) {
      clearInterval(indexingPollingRef.current);
      indexingPollingRef.current = null;
    }
  }, []);

  // 获取选中文件夹中已索引文件的ID列表
  const getSelectedFileIds = useCallback((): string[] => {
    return state.currentFolderFiles
      .filter(file => state.indexingStatuses[file.file_id] === 'indexed')
      .map(file => file.file_id);
  }, [state.currentFolderFiles, state.indexingStatuses]);

  // 根据ID获取文件
  const getFileById = useCallback((fileId: number): UserFile | undefined => {
    return state.currentFolderFiles.find(file => file.id === fileId);
  }, [state.currentFolderFiles]);

  // 获取总文件数
  const getTotalFilesCount = useCallback((): number => {
    return state.currentFolderFiles.length;
  }, [state.currentFolderFiles]);

  // 获取已索引文件数
  const getIndexedFilesCount = useCallback((): number => {
    return state.currentFolderFiles.filter(file => 
      state.indexingStatuses[file.file_id] === 'indexed'
    ).length;
  }, [state.currentFolderFiles, state.indexingStatuses]);

  // 初始化
  useEffect(() => {
    // 从本地存储加载选中的文件夹
    loadSelectedFolderFromStorage();
    
    // 加载文件夹列表
    refreshFolders();
    
    // 清理函数
    return () => {
      stopIndexingPolling();
    };
  }, [loadSelectedFolderFromStorage, refreshFolders, stopIndexingPolling]);

  // 当选中的文件夹变化时，加载该文件夹的文件
  useEffect(() => {
    refreshFiles();
  }, [refreshFiles]);


  return {
    state,
    
    // 文件夹操作
    folders: state.folders,
    selectedFolderId: state.selectedFolderId,
    selectFolder,
    createFolder,
    deleteFolder,
    refreshFolders,
    
    // 文件操作
    currentFolderFiles: state.currentFolderFiles,
    uploadFiles,
    deleteFile,
    reindexFile,
    refreshFiles,
    
    // 工具函数
    getSelectedFileIds,
    getFileById,
    getTotalFilesCount,
    getIndexedFilesCount,
    
    // 状态控制
    isLoading: state.isLoading,
    isUploading: state.isUploading,
    error: state.error,
    clearError,
    uploadProgress: state.uploadProgress,
  };
} 