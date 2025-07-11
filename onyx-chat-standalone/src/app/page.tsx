'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare,
  Settings,
  Palette,
  Bot,
  Sparkles,
  Eye,
  EyeOff,
  Moon,
  Sun,
  Zap,
  Shield,
  Globe,
  File as FileIcon,
} from 'lucide-react';
import ChatInterface from '@/components/ChatInterface';
import FileLibrary from '@/components/FileLibrary';
import { useChat } from '@/hooks/useChat';
import { useUserDocuments } from '@/hooks/useUserDocuments';
import { cn } from '@/lib/utils';
import { APP_CONFIG } from '@/lib/config';

type ViewMode = 'chat' | 'files' | 'both';
type DesignVariant = 'glassmorphism' | 'neumorphic';

export default function ChatPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('both');
  const [designVariant, setDesignVariant] = useState<DesignVariant>('glassmorphism');
  const [showSettings, setShowSettings] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  // Chat hook
  const {
    messages,
    sendMessage,
    isLoading: isChatLoading,
    searchProgress,
    error: chatError,
    clearChat,
    newSession,
    stopGeneration,
    clearError: clearChatError,
    regenerateLastMessage,
    exportChat,
  } = useChat();

  // User documents hook
  const {
    folders,
    selectedFolderId,
    selectFolder,
    createFolder,
    deleteFolder,
    currentFolderFiles,
    uploadFiles,
    deleteFile,
    reindexFile,
    getIndexedFilesCount,
    getTotalFilesCount,
    isLoading: isDocumentsLoading,
    isUploading: isDocumentsUploading,
    error: documentsError,
    clearError: clearDocumentsError,
    uploadProgress: documentsUploadProgress,
    state: documentsState,
  } = useUserDocuments();


  // Get indexed files from current folder
  const indexedFiles = currentFolderFiles.filter(file => {
    
    console.log(documentsState.indexingStatuses,111, file.file_id)
    return documentsState.indexingStatuses[file.file_id] === 'indexed'
  }
    //documentsState.indexingStatuses[file.file_id] === 'indexed'
  );

  // 监听 selectedFolderId 变化
  useEffect(() => {
    console.log('📄 page.tsx selectedFolderId 变化:', {
      selectedFolderId,
      folderName: documentsState.folders.find(f => f.id === selectedFolderId)?.name,
      timestamp: Date.now()
    });
  }, [selectedFolderId]);



  // Apply dark mode
  useEffect(() => {
    const root = document.documentElement;
    if (isDarkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDarkMode]);

  const handleSendMessage = async (message: string, fileIds?: number[], folderIds?: number[]) => {
    await sendMessage(message, fileIds, folderIds);
  };

  const getBackgroundClass = () => {
    if (designVariant === 'glassmorphism') {
      return 'gradient-bg-1 min-h-screen';
    }
    return 'bg-gray-100 min-h-screen';
  };

  const getHeaderClass = () => {
    return cn(
      'backdrop-blur-xl border-b sticky top-0 z-50 p-4',
      designVariant === 'glassmorphism'
        ? 'glass-effect border-white/20'
        : 'neuro-raised bg-white border-gray-200'
    );
  };

  const getMainContentClass = () => {
    return cn(
      'container mx-auto px-4 py-6 max-w-7xl',
      'grid gap-6',
      viewMode === 'both' ? 'lg:grid-cols-2' : 'lg:grid-cols-1'
    );
  };

  const getSidebarClass = () => {
    return cn(
      'fixed right-4 top-20 z-40 p-4 rounded-xl transition-all duration-300',
      'w-80 max-h-[calc(100vh-6rem)] overflow-y-auto',
      designVariant === 'glassmorphism'
        ? 'glass-strong border border-white/20'
        : 'neuro-raised bg-white border border-gray-200',
      showSettings ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0 pointer-events-none'
    );
  };

  return (
    <div className={getBackgroundClass()}>
      {/* Header */}
      <header className={getHeaderClass()}>
        <div className="container mx-auto max-w-7xl flex items-center justify-between">
          {/* Logo and Title */}
          <div className="flex items-center space-x-4">
            <motion.div
              whileHover={{ scale: 1.05 }}
              className={cn(
                'w-10 h-10 rounded-xl flex items-center justify-center',
                designVariant === 'glassmorphism'
                  ? 'glass-effect'
                  : 'neuro-raised bg-white'
              )}
            >
              <Bot className={cn(
                'w-6 h-6',
                designVariant === 'glassmorphism' ? 'text-white' : 'text-blue-600'
              )} />
            </motion.div>
            
            <div>
              <h1 className={cn(
                'text-xl font-bold',
                designVariant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
              )}>
                DeepInsight Chat
              </h1>
              <p className={cn(
                'text-sm opacity-70',
                designVariant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
              )}>
                AI-Powered Document Chat Assistant
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-4">
            {/* 文件状态显示 */}
            {selectedFolderId && getTotalFilesCount() > 0 && (
              <div className={cn(
                'px-3 py-1.5 rounded-full text-sm font-medium',
                designVariant === 'glassmorphism'
                  ? 'glass-light text-glass'
                  : 'neuro-flat bg-gray-100 text-gray-700'
              )}>
                <div className="flex items-center space-x-2">
                  <FileIcon className="w-4 h-4" />
                  <span>{getIndexedFilesCount()}/{getTotalFilesCount()} 已索引</span>
                  {getIndexedFilesCount() > 0 && (
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  )}
                </div>
              </div>
            )}
            {/* View Mode Toggle */}
            <div className={cn(
              'flex rounded-lg p-1 space-x-1',
              designVariant === 'glassmorphism'
                ? 'glass-light'
                : 'neuro-flat bg-gray-100'
            )}>
              {[
                { mode: 'files' as ViewMode, icon: Sparkles, label: 'Files' },
                { mode: 'chat' as ViewMode, icon: MessageSquare, label: 'Chat' },
                { mode: 'both' as ViewMode, icon: Sparkles, label: 'Both' },
              ].map(({ mode, icon: Icon, label }) => (
                <motion.button
                  key={mode}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setViewMode(mode)}
                  className={cn(
                    'flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                    viewMode === mode
                      ? designVariant === 'glassmorphism'
                        ? 'glass-effect text-white'
                        : 'neuro-pressed bg-blue-500 text-white'
                      : designVariant === 'glassmorphism'
                        ? 'text-glass hover:glass-light'
                        : 'text-gray-600 hover:neuro-flat'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{label}</span>
                </motion.button>
              ))}
            </div>

            {/* Theme Toggle */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={cn(
                'p-2 rounded-lg transition-all',
                designVariant === 'glassmorphism'
                  ? 'glass-light text-glass hover:glass-effect'
                  : 'neuro-flat text-gray-600 hover:neuro-raised'
              )}
            >
              {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </motion.button>

            {/* Settings Toggle */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowSettings(!showSettings)}
              className={cn(
                'p-2 rounded-lg transition-all',
                designVariant === 'glassmorphism'
                  ? 'glass-light text-glass hover:glass-effect'
                  : 'neuro-flat text-gray-600 hover:neuro-raised'
              )}
            >
              <Settings className="w-5 h-5" />
            </motion.button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className={getMainContentClass()}>
        {/* File Library Section */}
        <AnimatePresence mode="wait">
          {(viewMode === 'files' || viewMode === 'both') && (
            <motion.section
              key="files"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              <div className={cn(
                'p-6 rounded-xl border h-[calc(100vh-12rem)] flex flex-col',
                designVariant === 'glassmorphism'
                  ? 'glass-strong border-white/20'
                  : 'neuro-raised bg-white border-gray-200'
              )}>
                <div className="flex items-center justify-between mb-6 flex-shrink-0">
                  <div>
                    <h2 className={cn(
                      'text-xl font-semibold',
                      designVariant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
                    )}>
                      文件库管理
                    </h2>
                    {selectedFolderId && (
                      <p className={cn(
                        'text-sm opacity-70 mt-1',
                        designVariant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
                      )}>
                        当前选择: {folders.find(f => f.id === selectedFolderId)?.name || '未知文件夹'}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex-1 min-h-0">
                <FileLibrary 
                  variant={designVariant}
                  folders={folders}
                  selectedFolderId={selectedFolderId}
                  currentFolderFiles={currentFolderFiles}
                  isLoading={isDocumentsLoading}
                  isUploading={isDocumentsUploading}
                  error={documentsError}
                  uploadProgress={documentsUploadProgress}
                  indexingStatuses={documentsState.indexingStatuses}
                  selectFolder={selectFolder}
                  createFolder={createFolder}
                  deleteFolder={deleteFolder}
                  uploadFiles={uploadFiles}
                  deleteFile={deleteFile}
                  reindexFile={reindexFile}
                  clearError={clearDocumentsError}
                />
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Chat Section */}
        <AnimatePresence mode="wait">
          {(viewMode === 'chat' || viewMode === 'both') && (
            <motion.section
              key="chat"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-6"
            >
              <div className="h-[calc(100vh-12rem)]">
                <ChatInterface
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  isLoading={isChatLoading}
                  searchProgress={searchProgress}
                  error={chatError}
                  onStopGeneration={stopGeneration}
                  onClearChat={clearChat}
                  onRegenerateLastMessage={regenerateLastMessage}
                  onExportChat={exportChat}
                  onNewSession={newSession}
                  selectedFolderId={selectedFolderId}
                  selectedFolderName={folders.find(f => f.id === selectedFolderId)?.name || null}
                  selectedFiles={indexedFiles}
                  variant={designVariant}
                />
              </div>

              {chatError && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    'p-3 rounded-lg border',
                    designVariant === 'glassmorphism'
                      ? 'bg-red-500/20 border-red-400/40 text-red-200'
                      : 'bg-red-50 border-red-200 text-red-800'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{chatError}</span>
                    <button
                      onClick={clearChatError}
                      className="text-xs underline opacity-70 hover:opacity-100"
                    >
                      Dismiss
                    </button>
                  </div>
                </motion.div>
              )}
            </motion.section>
          )}
        </AnimatePresence>
      </main>

      {/* Settings Sidebar */}
      <div className={getSidebarClass()}>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className={cn(
              'text-lg font-semibold',
              designVariant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
            )}>
              Settings
            </h3>
            <button
              onClick={() => setShowSettings(false)}
              className={cn(
                'p-1 rounded-lg transition-colors',
                designVariant === 'glassmorphism'
                  ? 'hover:glass-effect text-glass'
                  : 'hover:neuro-flat text-gray-600'
              )}
            >
              <EyeOff className="w-5 h-5" />
            </button>
          </div>

          {/* Design Variant */}
          <div className="space-y-3">
            <h4 className={cn(
              'text-sm font-medium',
              designVariant === 'glassmorphism' ? 'text-glass' : 'text-gray-700'
            )}>
              Design Style
            </h4>
            
            <div className="grid grid-cols-1 gap-2">
              {[
                { 
                  variant: 'glassmorphism' as DesignVariant, 
                  label: 'Glassmorphism', 
                  icon: Sparkles,
                  description: 'Frosted glass effect'
                },
                { 
                  variant: 'neumorphic' as DesignVariant, 
                  label: 'Neumorphic', 
                  icon: Shield,
                  description: 'Soft, tactile design'
                },
              ].map(({ variant, label, icon: Icon, description }) => (
                <motion.button
                  key={variant}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setDesignVariant(variant)}
                  className={cn(
                    'flex items-center space-x-3 p-3 rounded-lg border text-left transition-all',
                    designVariant === variant
                      ? designVariant === 'glassmorphism'
                        ? 'glass-effect border-white/40 text-white'
                        : 'neuro-pressed border-blue-200 bg-blue-50 text-blue-800'
                      : designVariant === 'glassmorphism'
                        ? 'glass-light border-white/20 text-glass hover:glass-effect'
                        : 'neuro-flat border-gray-200 text-gray-600 hover:neuro-raised'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <div>
                    <div className="font-medium">{label}</div>
                    <div className="text-xs opacity-70">{description}</div>
                  </div>
                </motion.button>
              ))}
            </div>
          </div>

          {/* System Stats */}
          <div className="space-y-3">
            <h4 className={cn(
              'text-sm font-medium',
              designVariant === 'glassmorphism' ? 'text-glass' : 'text-gray-700'
            )}>
              System Info
            </h4>
            
            <div className={cn(
              'p-3 rounded-lg border text-sm',
              designVariant === 'glassmorphism'
                ? 'glass-light border-white/20 text-glass'
                : 'neuro-flat border-gray-200 text-gray-600'
            )}>
                             <div className="space-y-1">
                 <div className="flex justify-between">
                   <span>Version</span>
                   <span className="opacity-70">1.0.0</span>
                 </div>
                 <div className="flex justify-between">
                   <span>API Endpoint</span>
                   <span className="opacity-70">{APP_CONFIG.apiBaseUrl}</span>
                 </div>
               </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}