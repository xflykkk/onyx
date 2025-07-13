import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  ChatMessage,
  UseChatReturn,
  SearchProgress,
  ChatState,
  CreateChatMessageRequest,
  CreateChatSessionRequest,
  Persona,
  UploadedFile,
  FileDescriptor,
} from '@/types';
import {
  sendMessage as apiSendMessage,
  createChatSession,
  getPersonas,
  processSSEStream,
  apiClient,
} from '@/lib/api';
import {
  StreamingProcessor,
  StreamingPhaseManager,
  StreamingPhase,
  createMessageId,
  createSessionId,
} from '@/lib/streaming';
import { ERROR_MESSAGES, CHAT_CONFIG } from '@/lib/config';
import { storage } from '@/lib/utils';

// Get the last successful message ID as parent_id (following onyx/web logic)
function getLastSuccessfulMessageId(messageHistory: ChatMessage[]): number | null {
  const lastSuccessfulMessage = messageHistory
    .slice()
    .reverse()
    .find(
      (message) =>
        message.type === "assistant" &&
        message.messageId !== -1 &&
        message.messageId !== null &&
        message.messageId !== undefined
    );
  return lastSuccessfulMessage?.messageId || null;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchProgress, setSearchProgress] = useState<SearchProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chatState, setChatState] = useState<ChatState>('idle');
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);

  // Refs for managing streaming and processors
  const streamingProcessor = useRef<StreamingProcessor | null>(null);
  const phaseManager = useRef<StreamingPhaseManager | null>(null);
  const abortController = useRef<AbortController | null>(null);
  const lastProgressUpdateTime = useRef<number>(0);
  const PROGRESS_UPDATE_INTERVAL = 200; // 统一进度更新间隔为200ms

  // Initialize chat session and personas
  useEffect(() => {
    initializeChat();
  }, []);

  // Auto-save messages to localStorage
  useEffect(() => {
    if (messages.length > 0 && chatSessionId) {
      storage.set(`chat_messages_${chatSessionId}`, messages);
    }
  }, [messages, chatSessionId]);

  const initializeChat = useCallback(async () => {
    try {
      // Load personas
      const personaList = await getPersonas();
      setPersonas(personaList);

      // Try to restore previous session from localStorage
      const savedSessionId = storage.get('current_chat_session', null);
      if (savedSessionId) {
        const savedMessages = storage.get(`chat_messages_${savedSessionId}`, []);
        if (savedMessages.length > 0) {
          setMessages(savedMessages);
          setChatSessionId(savedSessionId);
          return;
        }
      }

      // Create new chat session
      const sessionRequest: CreateChatSessionRequest = {
        persona_id: personaList[0]?.id,
        description: `Chat session created at ${new Date().toISOString()}`,
      };

      const session = await createChatSession(sessionRequest);
      setChatSessionId(session.chat_session_id);
      storage.set('current_chat_session', session.chat_session_id);

    } catch (error) {
      console.error('Failed to initialize chat:', error);
      setError('Failed to initialize chat. Please refresh the page.');
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const stopGeneration = useCallback(() => {
    if (abortController.current) {
      abortController.current.abort();
      abortController.current = null;
    }

    // 无需处理打字机效果

    if (streamingProcessor.current) {
      const finalMessage = streamingProcessor.current.generateChatMessage();
      setMessages(prev => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        if (lastIndex >= 0 && updated[lastIndex].type === 'assistant') {
          updated[lastIndex] = { ...finalMessage, isStreaming: false };
        }
        return updated;
      });
      streamingProcessor.current = null;
    }

    if (phaseManager.current) {
      phaseManager.current.destroy();
      phaseManager.current = null;
    }

    setIsLoading(false);
    setChatState('idle');
    
    // 将进度标记为完成和折叠，确保所有子问题都完成
    setSearchProgress(prev => prev ? {
      ...prev,
      phase: 'complete',
      isCompleted: true,
      isCollapsed: true,
      // 确保所有子问题都标记为完成
      subQuestions: prev.subQuestions?.map(sq => ({
        ...sq,
        is_complete: true,
        answer_streaming: false
      })) || []
    } : null);
  }, []);

  const updateSearchProgress = useCallback((progress: SearchProgress) => {
    setSearchProgress(currentProgress => {
      // 避免无效更新：比较进度对象是否真正改变
      if (currentProgress && 
          currentProgress.phase === progress.phase &&
          currentProgress.subQueries === progress.subQueries &&
          currentProgress.documents === progress.documents &&
          currentProgress.currentAnswer === progress.currentAnswer) {
        return currentProgress;
      }
      return progress;
    });
  }, []);

  const updateCurrentMessage = useCallback((content: string) => {
    console.log('🔄 Updating current message with content:', content);
    setMessages(prev => {
      const updated = [...prev];
      const lastIndex = updated.length - 1;
      if (lastIndex >= 0 && updated[lastIndex].type === 'assistant') {
        // 避免无效更新：如果内容没有变化，不更新
        if (updated[lastIndex].content === content) {
          return prev;
        }
        console.log('✅ Found assistant message to update at index:', lastIndex);
        updated[lastIndex] = {
          ...updated[lastIndex],
          content,
          isStreaming: true,
        };
      } else {
        console.log('❌ No assistant message found to update');
      }
      return updated;
    });
  }, []);

  const sendMessage = useCallback(
    async (messageText: string, fileIds?: number[], folderIds?: number[], options: Partial<CreateChatMessageRequest> = {}) => {
      if (!messageText.trim()) {
        setError(ERROR_MESSAGES.chat.messageEmpty);
        return;
      }

      if (messageText.length > CHAT_CONFIG.maxMessageLength) {
        setError(ERROR_MESSAGES.chat.messageTooLong);
        return;
      }

      if (!chatSessionId) {
        console.error('❌ No chat session ID available');
        setError(ERROR_MESSAGES.chat.noSession);
        return;
      }

      console.log('💬 Sending message with session ID:', chatSessionId);

      // Clear any previous errors
      setError(null);
      setIsLoading(true);
      setChatState('sending');

      // Create user message
      const userMessageId = createMessageId();
      const userMessage: ChatMessage = {
        id: userMessageId,
        type: 'user',
        content: messageText,
        timestamp: new Date(),
      };

      // Add user message to chat
      setMessages(prev => [...prev, userMessage]);

      // Create assistant message placeholder
      const assistantMessageId = createMessageId();
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        type: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages(prev => [...prev, assistantMessage]);

      try {
        // For this standalone chat, we use user_file_ids to reference uploaded files
        // file_descriptors should be empty unless we have temporary chat files (like images)
        const fileDescriptors: FileDescriptor[] = []; // Empty for user files

        // Configure retrieval options following onyx/web logic
        // IMPORTANT: When files or folders are selected, retrieval_options should be null
        // This follows the logic: !documentsAreSelected ? options : null
        const documentsAreSelected = (fileIds && fileIds.length > 0) || (folderIds && folderIds.length > 0);
        const retrievalOptions = !documentsAreSelected ? {
          run_search: "auto" as const,
          real_time: false,
          enable_auto_detect_filters: true,
          dedupe_docs: true,
          chunks_above: 0,
          chunks_below: 0,
          full_doc: false,
        } : null;

        // Use the provided file and folder IDs directly
        const userFileIds = fileIds || [];
        const userFolderIds = folderIds || [];
        
        console.log('💬 Sending message with:', { 
          fileIds: userFileIds, 
          folderIds: userFolderIds,
          documentsAreSelected 
        });
        
        // Get the correct parent message ID from current messages (using functional update)
        let parentId: number | null = null;
        setMessages(currentMessages => {
          parentId = getLastSuccessfulMessageId(currentMessages);
          return currentMessages;
        });
        console.log('🆔 Using parent_message_id:', parentId);
        
        // Create request payload with all required fields
        const request: CreateChatMessageRequest = {
          chat_session_id: chatSessionId,
          parent_message_id: parentId, // Use last successful assistant message ID
          message: messageText,
          file_descriptors: fileDescriptors, // Empty array for user files
          search_doc_ids: userFileIds, // Use UserFile IDs for search scope
          user_file_ids: userFileIds, // Use UserFile IDs
          user_folder_ids: userFolderIds, // Use folder IDs if provided
          prompt_id: null, // Required field - null for default prompt
          retrieval_options: retrievalOptions, // null when files/folders selected, following onyx/web logic
          use_agentic_search: true, // Keep agent search enabled as in onyx/web
          temperature_override: CHAT_CONFIG.defaultTemperature,
          ...options,
        };

        // Start streaming
        setChatState('streaming');
        abortController.current = new AbortController();
        
        const { reader, abortController: responseAbortController } = await apiSendMessage(request);
        abortController.current = responseAbortController;

        // Initialize processors
        streamingProcessor.current = new StreamingProcessor(assistantMessageId);

        // 创建阶段管理器，但不在这里更新进度（避免重复更新）
        phaseManager.current = new StreamingPhaseManager(phase => {
          console.log('🎭 Phase changed to:', phase);
          // 阶段变化时不立即更新进度，统一在主循环中处理
        });

        // Process streaming response
        console.log('🚀 Starting to process streaming response...');
        for await (const chunk of processSSEStream(reader, abortController.current.signal)) {
          if (abortController.current.signal.aborted) {
            console.log('⏹️ Stream aborted');
            break;
          }

          console.log('📦 Received chunk:', chunk);
          console.log('🚀 About to process chunk:', chunk.substring(0, 100) + '...');
          const packet = streamingProcessor.current.processPacket(chunk);
          if (!packet) {
            console.log('⚠️ Packet processing returned null');
            continue;
          }

          console.log('✅ Processed packet:', packet);

          // Detect and transition to new phase based on packet content
          if (phaseManager.current) {
            const detectedPhase = phaseManager.current.detectPhaseFromPacket(packet);
            phaseManager.current.transitionTo(detectedPhase);
          }

          // 统一的进度更新逻辑（减少更新频率以避免进度被"挤走"）
          const now = Date.now();
          if (now - lastProgressUpdateTime.current > PROGRESS_UPDATE_INTERVAL) {
            const currentProgress = streamingProcessor.current.getSearchProgress();
            // 使用阶段管理器的当前阶段
            if (phaseManager.current) {
              currentProgress.phase = phaseManager.current.getCurrentPhase() as SearchProgress['phase'];
            }
            console.log('📊 Progress update:', currentProgress);
            updateSearchProgress(currentProgress);
            lastProgressUpdateTime.current = now;
          }

          // 直接更新消息内容（无打字机效果，参考 onyx/web 实现）
          const currentAnswer = streamingProcessor.current.getCurrentAnswer();
          console.log('💬 Current answer:', currentAnswer);
          if (currentAnswer) {
            console.log('📝 Directly updating message content');
            updateCurrentMessage(currentAnswer);
          }

          // Check for completion
          if (streamingProcessor.current.isStreamComplete()) {
            console.log('🎯 Stream complete detected');
            console.log('📄 Documents collected:', streamingProcessor.current.getDocuments());
            console.log('🔍 SubQueries collected:', streamingProcessor.current.getSubQueries().length);
            const finalMessage = streamingProcessor.current.generateChatMessage();
            const messageDetail = streamingProcessor.current.getMessageDetail();
            
            console.log('📝 Final message:', finalMessage);
            console.log('📋 Message detail:', messageDetail);
            
            // 无需完成打字机动画，内容已直接更新

            // Update final message
            setMessages(prev => {
              const updated = [...prev];
              const lastIndex = updated.length - 1;
              if (lastIndex >= 0 && updated[lastIndex].type === 'assistant') {
                console.log('📝 Updating final assistant message');
                updated[lastIndex] = { ...finalMessage, isStreaming: false };
              }
              return updated;
            });

            // Update message with real backend message ID
            if (messageDetail && messageDetail.message_id) {
              console.log('🆔 Updating message with backend message ID:', messageDetail.message_id);
              setMessages(prev => {
                const updated = [...prev];
                const lastIndex = updated.length - 1;
                if (lastIndex >= 0 && updated[lastIndex].type === 'assistant') {
                  updated[lastIndex] = { 
                    ...updated[lastIndex], 
                    messageId: messageDetail.message_id,
                    isStreaming: false 
                  };
                }
                return updated;
              });
            } else {
              console.warn('⚠️ No message_id received from backend');
            }

            break;
          }

          // Check for errors
          const streamError = streamingProcessor.current.getError();
          if (streamError) {
            console.log('❌ Stream error detected:', streamError);
            setError(streamError);
            break;
          }
        }
        
        console.log('🏁 Finished processing streaming response');
        
        // Handle final message completion when stream ends without explicit completion signal
        if (streamingProcessor.current && !streamingProcessor.current.isStreamComplete()) {
          console.log('🔄 Stream ended without completion signal, finalizing message');
          console.log('📄 Documents collected at stream end:', streamingProcessor.current.getDocuments());
          console.log('🔍 SubQueries collected at stream end:', streamingProcessor.current.getSubQueries().length);
          
          const finalMessage = streamingProcessor.current.generateChatMessage();
          console.log('📝 Final message from stream end:', finalMessage);
          
          // Update final message
          setMessages(prev => {
            const updated = [...prev];
            const lastIndex = updated.length - 1;
            if (lastIndex >= 0 && updated[lastIndex].type === 'assistant') {
              console.log('📝 Updating final assistant message from stream end');
              updated[lastIndex] = { ...finalMessage, isStreaming: false };
            }
            return updated;
          });
        }

      } catch (error: unknown) {
        console.error('Chat error:', error);
        
        // Remove the assistant message placeholder on error
        setMessages(prev => prev.slice(0, -1));
        
        if (error instanceof Error) {
          if (error.name === 'AbortError') {
            setError('Message generation was cancelled.');
          } else {
            const errorMessage = error.message || ERROR_MESSAGES.chat.sendFailed;
            setError(errorMessage);
          }
        } else {
          setError(ERROR_MESSAGES.chat.sendFailed);
        }
      } finally {
        setIsLoading(false);
        setChatState('idle');
        
        // 将进度标记为完成和折叠，确保所有子问题都完成
        setSearchProgress(prev => prev ? {
          ...prev,
          phase: 'complete',
          isCompleted: true,
          isCollapsed: true,
          // 确保所有子问题都标记为完成
          subQuestions: prev.subQuestions?.map(sq => ({
            ...sq,
            is_complete: true,
            answer_streaming: false
          })) || []
        } : null);
        
        // Cleanup processors
        if (phaseManager.current) {
          phaseManager.current.destroy();
          phaseManager.current = null;
        }
        streamingProcessor.current = null;
        abortController.current = null;
      }
    },
    [chatSessionId, updateCurrentMessage, updateSearchProgress]
  );

  const clearChat = useCallback(() => {
    // Stop any ongoing generation
    stopGeneration();
    
    // Clear messages
    setMessages([]);
    setError(null);
    setSearchProgress(null);
    setChatState('idle');
    // Parent message ID will be calculated from message history, no need to reset

    // Clear localStorage
    if (chatSessionId) {
      storage.remove(`chat_messages_${chatSessionId}`);
    }
  }, [chatSessionId, stopGeneration]);

  const newSession = useCallback(async () => {
    try {
      console.log('🔄 Creating new session...');
      
      // Stop any ongoing generation
      stopGeneration();
      
      // Clear current session data
      setMessages([]);
      setError(null);
      setSearchProgress(null);
      setChatState('idle');
      // Parent message ID will be calculated from message history, no need to reset

      // Clear localStorage for current session
      if (chatSessionId) {
        console.log('🗑️ Clearing old session:', chatSessionId);
        storage.remove(`chat_messages_${chatSessionId}`);
      }

      // Create new chat session
      const sessionRequest: CreateChatSessionRequest = {
        persona_id: personas[0]?.id,
        description: `New chat session created at ${new Date().toISOString()}`,
      };

      console.log('📤 Sending session request:', sessionRequest);
      const session = await createChatSession(sessionRequest);
      console.log('✅ New session created:', session);
      
      setChatSessionId(session.chat_session_id);
      storage.set('current_chat_session', session.chat_session_id);
      
      console.log('💾 Session saved to localStorage:', session.chat_session_id);

    } catch (error) {
      console.error('❌ Failed to create new session:', error);
      setError('Failed to create new session. Please refresh the page.');
    }
  }, [chatSessionId, personas, stopGeneration]);

  const regenerateLastMessage = useCallback(async () => {
    // 直接从当前 messages 状态中获取最后一条用户消息
    setMessages(currentMessages => {
      if (currentMessages.length < 2) return currentMessages;

      let lastUserMessage: ChatMessage | null = null;
      let userMessageIndex = -1;

      // 找到最后一条用户消息
      for (let i = currentMessages.length - 1; i >= 0; i--) {
        if (currentMessages[i].type === 'user') {
          lastUserMessage = currentMessages[i];
          userMessageIndex = i;
          break;
        }
      }

      if (!lastUserMessage) return currentMessages;

      // 异步重新发送消息（在状态更新后执行）
      setTimeout(() => {
        sendMessage(lastUserMessage!.content);
      }, 0);

      // 移除最后一条用户消息之后的所有消息
      return currentMessages.slice(0, userMessageIndex + 1);
    });
  }, [sendMessage]);

  const exportChat = useCallback(() => {
    setMessages(currentMessages => {
      const chatData = {
        sessionId: chatSessionId,
        messages: currentMessages.map(msg => ({
          type: msg.type,
          content: msg.content,
          timestamp: msg.timestamp.toISOString(),
          citations: msg.citations,
        })),
        exportedAt: new Date().toISOString(),
      };

      const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      return currentMessages;
    });
  }, [chatSessionId]);

  const getMessageById = useCallback((messageId: string): ChatMessage | undefined => {
    let foundMessage: ChatMessage | undefined;
    setMessages(currentMessages => {
      foundMessage = currentMessages.find(msg => msg.id === messageId);
      return currentMessages;
    });
    return foundMessage;
  }, []);

  const updateMessage = useCallback((messageId: string, updates: Partial<ChatMessage>) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === messageId ? { ...msg, ...updates } : msg
      )
    );
  }, []);

  const deleteMessage = useCallback((messageId: string) => {
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
  }, []);

  return {
    messages,
    sendMessage,
    isLoading,
    searchProgress,
    error,
    clearChat,
    newSession,
    stopGeneration,
    clearError,
    regenerateLastMessage,
    exportChat,
    getMessageById,
    updateMessage,
    deleteMessage,
    chatState,
    chatSessionId,
    personas,
  };
}

export default useChat;