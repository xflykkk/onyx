'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Bot,
  User,
  StopCircle,
  RotateCcw,
  Download,
  Trash2,
  Settings,
  FileText,
  Search,
  Loader2,
  Plus,
  Folder,
} from 'lucide-react';
import { ChatMessage, SearchProgress, UploadedFile, OnyxDocument, SubQuestionDetail, Citation } from '@/types';
import { cn } from '@/lib/utils';
import { CHAT_CONFIG } from '@/lib/config';
import { openDocument } from '@/lib/documentUtils';
import MessageBubble from './MessageBubble';
import EnhancedSearchProgress from './EnhancedSearchProgress';
import { useSmartScroll } from '@/hooks/useSmartScroll';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  onSendMessage: (message: string, fileIds?: number[], folderIds?: number[]) => Promise<void>;
  isLoading: boolean;
  searchProgress?: SearchProgress | null;
  error?: string | null;
  onStopGeneration?: () => void;
  onClearChat?: () => void;
  onRegenerateLastMessage?: () => void;
  onExportChat?: () => void;
  onNewSession?: () => void;
  selectedFolderId?: number | null;
  selectedFolderName?: string | null;
  selectedFiles?: Array<{ id: number; file_id: string; display_name?: string; name?: string }>;
  variant?: 'glassmorphism' | 'neumorphic';
  className?: string;
}

export default function ChatInterface({
  messages,
  onSendMessage,
  isLoading,
  searchProgress,
  error,
  onStopGeneration,
  onClearChat,
  onRegenerateLastMessage,
  onExportChat,
  onNewSession,
  selectedFolderId,
  selectedFolderName,
  selectedFiles = [],
  variant = 'glassmorphism',
  className,
}: ChatInterfaceProps) {
  const [inputMessage, setInputMessage] = useState('');
  const [selectedFileIds, setSelectedFileIds] = useState<number[]>([]);
  const [isComposing, setIsComposing] = useState(false);
  const [presentingDocument, setPresentingDocument] = useState<OnyxDocument | null>(null);
  const [selectedSubQuestion, setSelectedSubQuestion] = useState<SubQuestionDetail | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  
  // 牁定聊天状态以供智能滚动使用
  const chatState = isLoading ? 'streaming' : 'idle';

  // 使用智能滚动 hook替代原有的简单滚动逻辑
  const { scrollToBottom, resetUserScrollState, userHasScrolled } = useSmartScroll({
    chatState: chatState as 'idle' | 'sending' | 'streaming',
    scrollableDivRef: messagesContainerRef,
    endDivRef: messagesEndRef,
    enableAutoScroll: true,
    mobile: false, // 可以根据实际情况调整
  });
  
  // 只在消息内容变化时才进行智能滚动（不包括进度更新）
  useEffect(() => {
    // 只在有新消息且用户未主动滚动时才执行自动滚动
    if (messages.length > 0 && !userHasScrolled && isLoading) {
      // 使用节流调用滚动，避免过于频繁
      const timeoutId = setTimeout(() => {
        // 只有在流式输出时才自动滚动
        if (isLoading && messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100); // 100ms 节流
      
      return () => clearTimeout(timeoutId);
    }
  }, [messages.length, isLoading, userHasScrolled]); // 移除 searchProgress 依赖

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleSendMessage = useCallback(async () => {
    if (!inputMessage.trim() || isLoading || isComposing) return;

    const messageToSend = inputMessage.trim();
    
    // 如果有选中的文件，使用选中的文件ID
    // 如果没有选中文件但有选中文件夹，使用文件夹ID
    const filesToSend = selectedFileIds.length > 0 ? selectedFileIds : undefined;
    const foldersToSend = selectedFileIds.length === 0 && selectedFolderId ? [selectedFolderId] : undefined;
    
    setInputMessage('');
    setSelectedFileIds([]);
    
    // 重置用户滚动状态，启用新消息的自动滚动
    resetUserScrollState();
    
    try {
      await onSendMessage(messageToSend, filesToSend, foldersToSend);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [inputMessage, selectedFileIds, selectedFolderId, isLoading, isComposing, onSendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const handleFileToggle = useCallback((fileId: number) => {
    setSelectedFileIds(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  }, []);

  const handleDocumentClick = useCallback((document: OnyxDocument) => {
    openDocument(document, setPresentingDocument);
    console.log('Document clicked:', document);
  }, []);

  const handleSubQuestionClick = useCallback((question: SubQuestionDetail) => {
    setSelectedSubQuestion(question);
    console.log('Sub-question clicked:', question);
  }, []);

  const handleCitationClick = useCallback((citation: Citation) => {
    console.log('Citation clicked:', citation);
    
    // Open citation link if available
    if (citation.link) {
      window.open(citation.link, '_blank');
    }
  }, []);

  const hasSelectedFolder = selectedFolderId !== null && selectedFolderId !== undefined;
  const hasIndexedFiles = selectedFiles.length > 0;


  // 强制监听 selectedFolderId 变化
  useEffect(() => {
    console.log('💬 ChatInterface selectedFolderId 变化:', {
      selectedFolderId,
      selectedFolderName,
      hasSelectedFolder,
      timestamp: Date.now()
    });
  }, [selectedFolderId, selectedFolderName, hasSelectedFolder]);

  const containerClasses = cn(
    'flex flex-col h-full',
    variant === 'glassmorphism' 
      ? 'glass-effect rounded-xl border border-white/20'
      : 'neuro-raised rounded-xl bg-gray-100',
    className
  );

  const headerClasses = cn(
    'flex items-center justify-between p-4 border-b',
    variant === 'glassmorphism'
      ? 'border-white/20 text-glass'
      : 'border-gray-200 text-neuro'
  );

  const messagesClasses = cn(
    'flex-1 overflow-y-auto p-4 space-y-4',
    'scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent'
  );

  const inputAreaClasses = cn(
    'p-4 border-t',
    variant === 'glassmorphism'
      ? 'border-white/20'
      : 'border-gray-200'
  );

  return (
    <div className={containerClasses}>
      {/* Header */}
      <div className={headerClasses}>
        <div className="flex items-center space-x-3">
          <Bot className="w-6 h-6" />
          <div>
            <h2 className="text-lg font-semibold">Chat Assistant</h2>
            <p className="text-sm opacity-70">
              {messages.length === 0 
                ? 'Start a conversation'
                : `${messages.length} message${messages.length !== 1 ? 's' : ''}`
              }
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {onNewSession && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onNewSession}
              disabled={isLoading}
              className={cn(
                'p-2 rounded-lg transition-colors',
                variant === 'glassmorphism'
                  ? 'hover:bg-white/20 text-white/70 hover:text-white disabled:opacity-50'
                  : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800 disabled:opacity-50'
              )}
              title="New session"
            >
              <Plus className="w-5 h-5" />
            </motion.button>
          )}

          {onRegenerateLastMessage && messages.length > 0 && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onRegenerateLastMessage}
              disabled={isLoading}
              className={cn(
                'p-2 rounded-lg transition-colors',
                variant === 'glassmorphism'
                  ? 'hover:bg-white/20 text-white/70 hover:text-white disabled:opacity-50'
                  : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800 disabled:opacity-50'
              )}
              title="Regenerate last message"
            >
              <RotateCcw className="w-5 h-5" />
            </motion.button>
          )}
          
          {onExportChat && messages.length > 0 && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onExportChat}
              className={cn(
                'p-2 rounded-lg transition-colors',
                variant === 'glassmorphism'
                  ? 'hover:bg-white/20 text-white/70 hover:text-white'
                  : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800'
              )}
              title="Export chat"
            >
              <Download className="w-5 h-5" />
            </motion.button>
          )}
          
          {onClearChat && messages.length > 0 && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onClearChat}
              className={cn(
                'p-2 rounded-lg transition-colors',
                variant === 'glassmorphism'
                  ? 'hover:bg-red-500/20 text-white/70 hover:text-red-300'
                  : 'hover:bg-red-100 text-gray-600 hover:text-red-600'
              )}
              title="Clear chat"
            >
              <Trash2 className="w-5 h-5" />
            </motion.button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div ref={messagesContainerRef} className={messagesClasses}>
        {/* Empty State */}
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-full text-center space-y-4"
          >
            <Bot className={cn(
              'w-16 h-16',
              variant === 'glassmorphism' ? 'text-white/50' : 'text-gray-400'
            )} />
            <div>
              <h3 className={cn(
                'text-xl font-semibold mb-2',
                variant === 'glassmorphism' ? 'text-glass' : 'text-neuro'
              )}>
                Welcome to DeepInsight Chat
              </h3>
              <p className={cn(
                'text-sm opacity-70',
                variant === 'glassmorphism' ? 'text-glass' : 'text-neuro'
              )}>
                {hasSelectedFolder 
                  ? hasIndexedFiles
                    ? `已选择文件夹，包含 ${selectedFiles.length} 个已索引文档`
                    : '当前文件夹没有已索引的文件，请上传文档后重试'
                  : '请先选择一个文件夹开始对话'
                }
              </p>
            </div>
          </motion.div>
        )}

        {/* Messages */}
        <AnimatePresence mode="popLayout">
          {messages.map((message, index) => (
            <MessageBubble
              key={message.id}
              message={message}
              variant={variant}
              isLast={index === messages.length - 1}
              onCitationClick={handleCitationClick}
              onDocumentClick={handleDocumentClick}
              onSubQuestionClick={handleSubQuestionClick}
              searchProgress={message.type === 'assistant' && message.isStreaming && searchProgress ? searchProgress : undefined}
            />
          ))}
        </AnimatePresence>

        {/* Loading Indicator */}
        {isLoading && !searchProgress && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center space-x-2 text-sm"
          >
            <Loader2 className={cn(
              'w-4 h-4 animate-spin',
              variant === 'glassmorphism' ? 'text-white/70' : 'text-gray-600'
            )} />
            <span className={cn(
              variant === 'glassmorphism' ? 'text-glass' : 'text-neuro'
            )}>
              Thinking...
            </span>
          </motion.div>
        )}

        {/* Error Display */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              'p-3 rounded-lg border',
              variant === 'glassmorphism'
                ? 'bg-red-500/20 border-red-400/40 text-red-200'
                : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              <span className="text-sm">{error}</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Folder Status Display */}
      <div className={cn(
        'px-4 py-3 border-t',
        variant === 'glassmorphism'
          ? 'border-white/20'
          : 'border-gray-200'
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={cn(
              'p-2 rounded-lg',
              variant === 'glassmorphism'
                ? 'glass-light'
                : 'neuro-flat bg-gray-100'
            )}>
              <Folder className={cn(
                'w-4 h-4',
                variant === 'glassmorphism' ? 'text-white/80' : 'text-gray-600'
              )} />
            </div>
            <div>
              <div className={cn(
                'text-sm font-medium',
                variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
              )}>
                {hasSelectedFolder 
                  ? `当前文件夹: ${selectedFolderName || '未命名文件夹'}`
                  : '未选择文件夹'
                }
              </div>
              <div className={cn(
                'text-xs opacity-70',
                variant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
              )}>
                {hasSelectedFolder
                  ? hasIndexedFiles
                    ? `可用文档: ${selectedFiles.length} 个`
                    : '此文件夹暂无可用文档'
                  : '请在左侧选择一个文件夹开始聊天'
                }
              </div>
            </div>
          </div>
          
          {hasSelectedFolder && (
            <div className={cn(
              'flex items-center space-x-1 px-2 py-1 rounded-full text-xs',
              variant === 'glassmorphism'
                ? 'glass-light text-glass'
                : 'neuro-flat bg-gray-100 text-gray-600'
            )}>
              <div className={cn(
                'w-2 h-2 rounded-full',
                hasIndexedFiles ? 'bg-green-500' : 'bg-yellow-500'
              )} />
              <span>{hasIndexedFiles ? '就绪' : '准备中'}</span>
            </div>
          )}
        </div>
      </div>

      {/* File Selection Area */}
      {hasSelectedFolder && hasIndexedFiles && (
        <div className={cn(
          'px-4 py-2 border-t',
          variant === 'glassmorphism'
            ? 'border-white/20'
            : 'border-gray-200'
        )}>
          <div className="flex items-center space-x-2 mb-2">
            <FileText className={cn(
              'w-4 h-4',
              variant === 'glassmorphism' ? 'text-white/70' : 'text-gray-600'
            )} />
            <span className={cn(
              'text-sm font-medium',
              variant === 'glassmorphism' ? 'text-glass' : 'text-neuro'
            )}>
              选择要询问的文档:
            </span>
          </div>
          
          <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
            <button
              onClick={() => setSelectedFileIds(
                selectedFileIds.length === selectedFiles.length ? [] : selectedFiles.map(f => f.id)
              )}
              className={cn(
                'px-3 py-1 rounded-full text-xs font-medium transition-colors',
                selectedFileIds.length === selectedFiles.length
                  ? variant === 'glassmorphism'
                    ? 'bg-blue-500/40 text-blue-200 border border-blue-400/40'
                    : 'bg-blue-100 text-blue-800 border border-blue-200'
                  : variant === 'glassmorphism'
                    ? 'bg-white/10 text-white/70 border border-white/20 hover:bg-white/20'
                    : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'
              )}
            >
              {selectedFileIds.length === selectedFiles.length ? '取消全选' : '全选'}
            </button>
            
            {selectedFiles.map(file => (
              <button
                key={file.id}
                onClick={() => handleFileToggle(file.id)}
                className={cn(
                  'px-3 py-1 rounded-full text-xs font-medium transition-colors truncate max-w-32',
                  selectedFileIds.includes(file.id)
                    ? variant === 'glassmorphism'
                      ? 'bg-blue-500/40 text-blue-200 border border-blue-400/40'
                      : 'bg-blue-100 text-blue-800 border border-blue-200'
                    : variant === 'glassmorphism'
                      ? 'bg-white/10 text-white/70 border border-white/20 hover:bg-white/20'
                      : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'
                )}
                title={file.display_name || file.name || '未知文件'}
              >
                {file.display_name || file.name || '未知文件'}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className={inputAreaClasses}>
        <div className="flex items-end space-x-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => setIsComposing(true)}
              onCompositionEnd={() => setIsComposing(false)}
              placeholder={hasSelectedFolder 
                ? hasIndexedFiles
                  ? `询问关于 ${selectedFiles.length} 个文档的问题...`
                  : `当前文件夹暂无可用文档，可以问一般问题或上传文件后询问文档相关问题`
                : `请先在左侧选择或创建一个文件夹...`
              }
              disabled={isLoading || !hasSelectedFolder}
              className={cn(
                'w-full px-4 py-3 rounded-xl border resize-none transition-all',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                'min-h-[48px] max-h-32',
                variant === 'glassmorphism'
                  ? 'glass-light border-white/30 text-glass placeholder-white/50 focus:glass-effect'
                  : 'neuro-flat border-gray-300 text-gray-800 placeholder-gray-500 bg-white focus:neuro-pressed',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              rows={1}
              style={{
                height: 'auto',
                minHeight: '48px',
                maxHeight: '128px',
                overflowY: inputMessage.length > 100 ? 'scroll' : 'hidden',
              }}
            />
            
            {/* Character Count */}
            {inputMessage.length > CHAT_CONFIG.maxMessageLength * 0.8 && (
              <div className={cn(
                'absolute bottom-2 right-2 text-xs',
                inputMessage.length > CHAT_CONFIG.maxMessageLength
                  ? 'text-red-400'
                  : variant === 'glassmorphism'
                    ? 'text-white/50'
                    : 'text-gray-400'
              )}>
                {inputMessage.length}/{CHAT_CONFIG.maxMessageLength}
              </div>
            )}
          </div>
          
          {/* Send/Stop Button */}
          <div className="flex space-x-2">
            {isLoading && onStopGeneration ? (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onStopGeneration}
                className={cn(
                  'p-3 rounded-xl transition-colors',
                  variant === 'glassmorphism'
                    ? 'glass-effect hover:glass-strong text-red-300 hover:text-red-200'
                    : 'neuro-raised hover:neuro-flat text-red-600 hover:text-red-700 bg-white'
                )}
                title="Stop generation"
              >
                <StopCircle className="w-5 h-5" />
              </motion.button>
            ) : (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading || !hasSelectedFolder || inputMessage.length > CHAT_CONFIG.maxMessageLength}
                className={cn(
                  'p-3 rounded-xl transition-colors',
                  variant === 'glassmorphism'
                    ? 'glass-effect hover:glass-strong text-white/80 hover:text-white disabled:opacity-50'
                    : 'neuro-raised hover:neuro-flat text-blue-600 hover:text-blue-700 bg-white disabled:opacity-50',
                  'disabled:cursor-not-allowed disabled:hover:scale-100'
                )}
                title="Send message"
              >
                <Send className="w-5 h-5" />
              </motion.button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}