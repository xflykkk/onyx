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
  Quote,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { ChatMessage, Citation } from '@/types';
import { cn, formatRelativeTime, copyToClipboard } from '@/lib/utils';

interface MessageBubbleProps {
  message: ChatMessage;
  variant?: 'glassmorphism' | 'neumorphic';
  isLast?: boolean;
  onCitationClick?: (citation: Citation) => void;
  className?: string;
}

export default function MessageBubble({
  message,
  variant = 'glassmorphism',
  isLast = false,
  onCitationClick,
  className,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [showCitations, setShowCitations] = useState(false);
  const [showThinking, setShowThinking] = useState(false);

  const handleCopy = useCallback(async () => {
    const success = await copyToClipboard(message.content);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [message.content]);

  const isUser = message.type === 'user';
  const hasContent = message.content && message.content.trim().length > 0;
  const hasCitations = message.citations && message.citations.length > 0;
  const hasThinking = message.thinkingContent && message.thinkingContent.trim().length > 0;

  const bubbleClasses = cn(
    'flex space-x-3 max-w-4xl mx-auto w-full',
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
    'flex-1 space-y-2',
    isUser ? 'items-end' : 'items-start'
  );

  const messageBubbleClasses = cn(
    'relative px-4 py-3 rounded-2xl max-w-none',
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
            <div className={textClasses}>
              <ReactMarkdown
                className="prose prose-sm max-w-none"
                components={{
                  // Customize markdown rendering
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
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
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(
                        'inline-flex items-center space-x-1 underline hover:no-underline transition-colors',
                        variant === 'glassmorphism'
                          ? 'text-blue-300 hover:text-blue-200'
                          : 'text-blue-600 hover:text-blue-800'
                      )}
                    >
                      <span>{children}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ),
                  ul: ({ children }) => <ul className="list-disc list-inside space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="text-sm">{children}</li>,
                }}
              >
                {message.content}
              </ReactMarkdown>
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

        {/* Citations */}
        {!isUser && hasCitations && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mr-12"
          >
            <button
              onClick={() => setShowCitations(!showCitations)}
              className={cn(
                'flex items-center space-x-2 text-xs font-medium transition-colors mb-2',
                variant === 'glassmorphism'
                  ? 'text-white/70 hover:text-white/90'
                  : 'text-gray-600 hover:text-gray-800'
              )}
            >
              <Quote className="w-4 h-4" />
              <span>{message.citations!.length} Source{message.citations!.length !== 1 ? 's' : ''}</span>
              {showCitations ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showCitations && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-2"
              >
                {message.citations!.map((citation, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={cn(
                      'p-3 rounded-lg border cursor-pointer transition-all group',
                      variant === 'glassmorphism'
                        ? 'glass-light border-white/20 hover:glass-effect'
                        : 'neuro-flat bg-gray-50 border-gray-200 hover:neuro-raised'
                    )}
                    onClick={() => onCitationClick?.(citation)}
                  >
                    <div className="flex items-start space-x-3">
                      <FileText className={cn(
                        'w-4 h-4 flex-shrink-0 mt-0.5',
                        variant === 'glassmorphism' ? 'text-white/70' : 'text-gray-600'
                      )} />
                      
                      <div className="flex-1 min-w-0">
                        <h4 className={cn(
                          'text-sm font-medium truncate',
                          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
                        )}>
                          {citation.documentName}
                        </h4>
                        
                        <p className={cn(
                          'text-xs mt-1 line-clamp-2',
                          variant === 'glassmorphism' ? 'text-white/60' : 'text-gray-600'
                        )}>
                          {citation.text}
                        </p>
                        
                        <div className={cn(
                          'flex items-center space-x-2 mt-2 text-xs',
                          variant === 'glassmorphism' ? 'text-white/50' : 'text-gray-500'
                        )}>
                          <span className="px-2 py-0.5 rounded-full bg-current/20">
                            {citation.sourceType}
                          </span>
                          
                          {citation.link && (
                            <div className="flex items-center space-x-1">
                              <ExternalLink className="w-3 h-3" />
                              <span className="truncate max-w-32">{citation.link}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )}
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