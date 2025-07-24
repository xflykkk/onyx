'use client';

import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  User,
  Bot,
  Copy,
  Check,
  ExternalLink,
  FileText,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { ChatMessage, Citation, OnyxDocument, SubQuestionDetail, SubQueryDetail, SearchProgress } from '@/types';
import { cn, formatRelativeTime, copyToClipboard } from '@/lib/utils';
import { MemoizedAnchor, MemoizedParagraph } from './MemoizedTextComponents';
import { SourcesDisplay } from './SourcesDisplay';
import CitationRenderer from './CitationRenderer';
import SubQuestionsDisplay from './SubQuestionsDisplay';
import EnhancedSearchProgress from './EnhancedSearchProgress';

interface MessageBubbleProps {
  message: ChatMessage;
  variant?: 'glassmorphism' | 'neumorphic';
  isLast?: boolean;
  onCitationClick?: (citation: Citation) => void;
  onDocumentClick?: (document: OnyxDocument) => void;
  onSubQuestionClick?: (question: SubQuestionDetail) => void;
  className?: string;
  searchProgress?: SearchProgress;
}

export default function MessageBubble({
  message,
  variant = 'glassmorphism',
  isLast = false,
  onCitationClick,
  onDocumentClick,
  onSubQuestionClick,
  className,
  searchProgress,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [showThinking, setShowThinking] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [presentingDocument, setPresentingDocument] = useState<OnyxDocument | null>(null);

  const handleCopy = useCallback(async () => {
    const success = await copyToClipboard(message.content);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [message.content]);

  const handleDocumentClick = useCallback((document: OnyxDocument) => {
    setPresentingDocument(document);
    onDocumentClick?.(document);
  }, [onDocumentClick]);

  const handleSubQuestionClick = useCallback((question: SubQuestionDetail) => {
    onSubQuestionClick?.(question);
  }, [onSubQuestionClick]);

  const isUser = message.type === 'user';
  const hasContent = message.content && message.content.trim().length > 0;
  const hasThinking = message.thinkingContent && message.thinkingContent.trim().length > 0;
  const hasDocuments = message.documents && message.documents.length > 0;
  
  // Convert DocumentInfoPacket to OnyxDocument for compatibility
  const onyxDocuments: OnyxDocument[] = message.documents?.map(doc => ({
    document_id: doc.document_id,
    semantic_identifier: doc.semantic_identifier,
    link: doc.link,
    source_type: doc.source_type,
    blurb: doc.blurb,
    boost: doc.boost,
    score: doc.score,
    chunk_ind: doc.chunk_ind,
    match_highlights: doc.match_highlights,
    metadata: doc.metadata,
    updated_at: doc.updated_at,
    is_internet: doc.is_internet,
  })) || [];

  const bubbleClasses = cn(
    'flex space-x-3 max-w-4xl mx-auto w-full min-w-0',
    isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row',
    className
  );

  const avatarClasses = cn(
    'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
    isUser
      ? variant === 'glassmorphism'
        ? 'glass-effect text-white/80'
        : 'neuro-raised bg-blue-100 text-blue-600'
      : variant === 'glassmorphism'
        ? 'glass-effect text-white/80'
        : 'neuro-raised bg-gray-100 text-gray-600'
  );

  const contentClasses = cn(
    'flex-1 space-y-2 min-w-0',
    isUser ? 'items-end' : 'items-start'
  );

  const messageBubbleClasses = cn(
    'relative px-4 py-3 rounded-2xl overflow-hidden break-words',
    isUser
      ? variant === 'glassmorphism'
        ? 'message-bubble-user ml-12'
        : 'neuro-pressed bg-blue-50 border border-blue-200 ml-12'
      : variant === 'glassmorphism'
        ? 'message-bubble-assistant mr-12'
        : 'neuro-raised bg-white border border-gray-200 mr-12'
  );

  const textClasses = cn(
    'text-sm leading-relaxed',
    variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
  );

  const metaClasses = cn(
    'flex items-center space-x-2 text-xs opacity-70',
    variant === 'glassmorphism' ? 'text-glass' : 'text-gray-600',
    isUser ? 'justify-end' : 'justify-start'
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className={bubbleClasses}
    >
      {/* Avatar */}
      <div className={avatarClasses}>
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      {/* Content */}
      <div className={contentClasses}>
        {/* Thinking Section (for assistant only) */}
        {!isUser && hasThinking && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className={cn(
              'rounded-xl p-3 border mr-12',
              variant === 'glassmorphism'
                ? 'glass-light border-white/20'
                : 'neuro-flat bg-gray-50 border-gray-200'
            )}
          >
            <button
              onClick={() => setShowThinking(!showThinking)}
              className={cn(
                'flex items-center space-x-2 text-xs font-medium transition-colors',
                variant === 'glassmorphism'
                  ? 'text-white/70 hover:text-white/90'
                  : 'text-gray-600 hover:text-gray-800'
              )}
            >
              <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
              <span>AI Thinking Process</span>
              {showThinking ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            
            {showThinking && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-2"
              >
                <div className={cn(
                  'text-xs leading-relaxed font-mono',
                  variant === 'glassmorphism' ? 'text-white/60' : 'text-gray-500'
                )}>
                  {message.thinkingContent}
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Search Progress (for assistant only, during streaming) */}
        {!isUser && searchProgress && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mr-12 mb-4"
          >
            <EnhancedSearchProgress 
              progress={searchProgress} 
              variant={variant}
              onDocumentClick={onDocumentClick}
            />
          </motion.div>
        )}

        {/* Main Message */}
        {hasContent && (
          <div className={messageBubbleClasses}>
            {/* Streaming indicator */}
            {message.isStreaming && (
              <div className="absolute top-2 right-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}

            {/* Message Content */}
            <div className={cn(textClasses, 'overflow-hidden')}>
              {/* Debug message content */}
              <div className="hidden">
                <pre className="text-xs opacity-50 break-all">
                  {JSON.stringify({ 
                    content: message.content,
                    hasDocuments,
                    docsCount: onyxDocuments.length,
                    rawDocuments: message.documents,
                    onyxDocuments: onyxDocuments 
                  }, null, 2)}
                </pre>
              </div>
              
              {/* Debug: Log document data only when not streaming */}
              {!message.isStreaming && (() => {
                console.log('📄 MessageBubble final document debug:', {
                  'message.documents': message.documents,
                  'message.documents length': message.documents?.length || 0,
                  'onyxDocuments length': onyxDocuments.length,
                  'onyxDocuments': onyxDocuments,
                  'message.subQueries': message.subQueries,
                  'message.subQueries length': message.subQueries?.length || 0,
                  'message.subQuestions': message.subQuestions,
                  'message.subQuestions length': message.subQuestions?.length || 0,
                  'hasDocuments': hasDocuments,
                  'citation count in content': (message.content.match(/\[(D|Q)?\d+\]/g) || []).length
                });
                return null;
              })()}
              
              {/* Process message content to convert citations to links */}
              {(() => {
                // Pre-process content to convert [D1] to [[D1]](citation:D1)
                const processedContent = message.content.replace(
                  /\[([DQ]?\d+)\]/g,
                  (match, citation) => {
                    console.log('Pre-processing citation:', match, citation);
                    return `[[${citation}]](citation:${citation})`;
                  }
                );
                
                console.log('Processed content:', processedContent);
                
                return (
                  <ReactMarkdown
                    className="prose prose-sm max-w-none break-words"
                    components={{
                  // Enhanced markdown rendering with citation support
                  p: ({ children }) => (
                    <MemoizedParagraph fontSize="sm" variant={variant}>
                      {children}
                    </MemoizedParagraph>
                  ),
                  // Handle text nodes that might contain citations
                  text: ({ children }) => {
                    const text = children?.toString() || '';
                    console.log('ReactMarkdown text node:', text);
                    
                    return (
                      <CitationRenderer
                        text={text}
                        docs={onyxDocuments}
                        subQuestions={message.subQuestions}
                        onDocumentClick={handleDocumentClick}
                        onSubQuestionClick={handleSubQuestionClick}
                        variant={variant}
                      />
                    );
                  },
                  code: ({ children, className }) => {
                    const isInline = !className;
                    return isInline ? (
                      <code className={cn(
                        'px-1.5 py-0.5 rounded text-xs font-mono',
                        variant === 'glassmorphism'
                          ? 'bg-white/20 text-white/90'
                          : 'bg-gray-100 text-gray-800'
                      )}>
                        {children}
                      </code>
                    ) : (
                      <pre className={cn(
                        'p-3 rounded-lg text-xs font-mono overflow-x-auto',
                        variant === 'glassmorphism'
                          ? 'bg-black/40 text-white/90'
                          : 'bg-gray-900 text-gray-100'
                      )}>
                        <code>{children}</code>
                      </pre>
                    );
                  },
                  blockquote: ({ children }) => (
                    <blockquote className={cn(
                      'border-l-4 pl-4 py-2 my-2',
                      variant === 'glassmorphism'
                        ? 'border-white/40 bg-white/10'
                        : 'border-gray-300 bg-gray-50'
                    )}>
                      {children}
                    </blockquote>
                  ),
                      a: ({ href, children }) => {
                        console.log('ReactMarkdown link:', { href, children });
                        
                        // Check if this is a citation link
                        if (href?.startsWith('citation:')) {
                          const citationText = href.replace('citation:', '');
                          console.log('Found citation link:', citationText);
                        }
                        
                        return (
                          <MemoizedAnchor
                            docs={onyxDocuments}
                            subQuestions={message.subQuestions}
                            openQuestion={handleSubQuestionClick}
                            href={href}
                            updatePresentingDocument={handleDocumentClick}
                            variant={variant}
                          >
                            {children}
                          </MemoizedAnchor>
                        );
                      },
                      ul: ({ children }) => (
                        <ul className="list-disc list-outside ml-4 space-y-1">{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="list-decimal list-outside ml-4 space-y-1">{children}</ol>
                      ),
                      li: ({ children }) => (
                        <li className="text-sm leading-relaxed">{children}</li>
                      ),
                    }}
                  >
                    {processedContent}
                  </ReactMarkdown>
                );
              })()}
            </div>

            {/* Actions */}
            {!message.isStreaming && (
              <div className="flex items-center justify-between mt-3 pt-2 border-t border-current/10">
                <div className={metaClasses}>
                  <Clock className="w-3 h-3" />
                  <span>{formatRelativeTime(message.timestamp)}</span>
                </div>
                
                <button
                  onClick={handleCopy}
                  className={cn(
                    'p-1.5 rounded-lg transition-colors',
                    variant === 'glassmorphism'
                      ? 'hover:bg-white/20 text-white/70 hover:text-white'
                      : 'hover:bg-gray-100 text-gray-600 hover:text-gray-800'
                  )}
                  title="Copy message"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Divider before sub-questions */}
        {!isUser && (message.subQuestions && message.subQuestions.length > 0) && (
          <div className={cn(
            'mr-12 my-4 border-t border-dashed',
            variant === 'glassmorphism'
              ? 'border-white/30'
              : 'border-gray-300'
          )} />
        )}

        {/* Sub-Questions Display */}
        {!isUser && message.subQuestions && message.subQuestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mr-12"
          >
            <SubQuestionsDisplay
              subQuestions={message.subQuestions}
              variant={variant}
              onSubQuestionClick={handleSubQuestionClick}
              onDocumentClick={handleDocumentClick}
              isStreamingQuestions={message.isStreaming}
            />
          </motion.div>
        )}

        {/* Sources Display */}
        {!isUser && hasDocuments && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mr-12 mt-2"
          >
            <SourcesDisplay
              documents={onyxDocuments}
              setPresentingDocument={handleDocumentClick}
              toggleDocumentSelection={() => setShowSources(!showSources)}
              variant={variant}
              animateEntrance={false}
              threeCols={false}
              hideDocumentDisplay={false}
              docSidebarToggled={showSources}
              compact={true}
              defaultCollapsed={true}
            />
          </motion.div>
        )}

        {/* Error Display */}
        {message.error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              'mr-12 p-3 rounded-lg border',
              variant === 'glassmorphism'
                ? 'bg-red-500/20 border-red-400/40 text-red-200'
                : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              <span className="text-sm">{message.error}</span>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}