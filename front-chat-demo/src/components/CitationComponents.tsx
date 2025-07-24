'use client';

import React, { memo, ReactNode } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { FileText, ExternalLink, Search, Calendar } from 'lucide-react';
import { 
  OnyxDocument, 
  SubQuestionDetail, 
  DocumentCardProps, 
  QuestionCardProps 
} from '@/types';
import { cn } from '@/lib/utils';
import { openDocument, getDocumentDisplayInfo, getDocumentTitle } from '@/lib/documentUtils';
import { TooltipPortal } from './TooltipPortal';

// Utility function to clean sub-question text
const cleanSubQuestionText = (text: string): string => {
  if (!text) return '';
  // Remove <sub-question> and </sub-question> tags
  let cleaned = text.replace(/<\/?sub-question>/g, '');
  // Remove any other HTML-like tags that might appear
  cleaned = cleaned.replace(/<[^>]*>/g, '');
  // Remove multiple spaces and trim
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  return cleaned;
};

// Compact markdown renderer for tooltip content
const TooltipMarkdown: React.FC<{
  children: string | string[];
  variant?: 'glassmorphism' | 'neumorphic';
}> = ({ children, variant = 'glassmorphism' }) => {
  const content = Array.isArray(children) ? children.join(' ') : children;
  return (
    <ReactMarkdown
      className="prose prose-sm max-w-none"
      components={{
        p: ({ children }) => (
          <span className={cn(
            'text-xs leading-relaxed block break-words',
            variant === 'glassmorphism' ? 'text-white/60' : 'text-gray-600'
          )}>
            {children}
          </span>
        ),
        strong: ({ children }) => (
          <strong className={cn(
            'font-medium',
            variant === 'glassmorphism' ? 'text-white/80' : 'text-gray-800'
          )}>
            {children}
          </strong>
        ),
        em: ({ children }) => (
          <em className={cn(
            'italic',
            variant === 'glassmorphism' ? 'text-white/70' : 'text-gray-700'
          )}>
            {children}
          </em>
        ),
        code: ({ children }) => (
          <code className={cn(
            'px-1 py-0.5 rounded text-xs font-mono break-all',
            variant === 'glassmorphism'
              ? 'bg-white/20 text-white/90'
              : 'bg-gray-100 text-gray-800'
          )}>
            {children}
          </code>
        ),
        ul: ({ children }) => <ul className="list-disc list-outside ml-4 space-y-0.5 text-xs">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-outside ml-4 space-y-0.5 text-xs">{children}</ol>,
        li: ({ children }) => <li className="text-xs leading-relaxed">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className={cn(
            'border-l-2 pl-2 py-1 my-1 text-xs break-words',
            variant === 'glassmorphism'
              ? 'border-white/40 bg-white/5'
              : 'border-gray-300 bg-gray-50'
          )}>
            {children}
          </blockquote>
        ),
        // Remove default margins for compact display
        h1: ({ children }) => <span className="font-semibold text-xs break-words">{children}</span>,
        h2: ({ children }) => <span className="font-semibold text-xs break-words">{children}</span>,
        h3: ({ children }) => <span className="font-semibold text-xs break-words">{children}</span>,
        h4: ({ children }) => <span className="font-semibold text-xs break-words">{children}</span>,
        h5: ({ children }) => <span className="font-semibold text-xs break-words">{children}</span>,
        h6: ({ children }) => <span className="font-semibold text-xs break-words">{children}</span>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
};

// Tooltip component (simple implementation)
interface TooltipProps {
  children: React.ReactNode;
  content: React.ReactNode;
  delayDuration?: number;
  variant?: 'glassmorphism' | 'neumorphic';
}

const Tooltip: React.FC<TooltipProps> = ({ children, content, delayDuration = 0, variant = 'glassmorphism' }) => {
  const [isVisible, setIsVisible] = React.useState(false);
  const [position, setPosition] = React.useState<'top' | 'bottom' | 'left' | 'right'>('top');
  const tooltipRef = React.useRef<HTMLDivElement>(null);
  const triggerRef = React.useRef<HTMLSpanElement>(null);

  const updatePosition = React.useCallback(() => {
    if (!triggerRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight,
    };

    // Check if there's enough space above
    const spaceAbove = triggerRect.top;
    const spaceBelow = viewport.height - triggerRect.bottom;
    const spaceLeft = triggerRect.left;
    const spaceRight = viewport.width - triggerRect.right;

    // Determine best position
    if (spaceAbove >= 320 && spaceAbove > spaceBelow) {
      setPosition('top');
    } else if (spaceBelow >= 320) {
      setPosition('bottom');
    } else if (spaceRight >= 320) {
      setPosition('right');
    } else if (spaceLeft >= 320) {
      setPosition('left');
    } else {
      // Fallback to the side with most space
      if (spaceAbove > spaceBelow) {
        setPosition('top');
      } else {
        setPosition('bottom');
      }
    }
  }, []);

  const handleMouseEnter = React.useCallback(() => {
    setIsVisible(true);
    // Update position after the tooltip is rendered
    setTimeout(updatePosition, 0);
  }, [updatePosition]);

  // Update position when scrolling or resizing
  React.useEffect(() => {
    if (!isVisible) return;

    const handleScroll = () => updatePosition();
    const handleResize = () => updatePosition();

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleResize, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
    };
  }, [isVisible, updatePosition]);

  const getTooltipPosition = () => {
    if (!triggerRef.current) return { left: 0, top: 0 };
    
    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = 320;
    const tooltipHeight = position === 'top' || position === 'bottom' ? 400 : 300;
    
    let left = 0;
    let top = 0;
    
    switch (position) {
      case 'top':
        left = triggerRect.left + triggerRect.width / 2 - tooltipWidth / 2;
        top = triggerRect.top - tooltipHeight - 8;
        break;
      case 'bottom':
        left = triggerRect.left + triggerRect.width / 2 - tooltipWidth / 2;
        top = triggerRect.bottom + 8;
        break;
      case 'left':
        left = triggerRect.left - tooltipWidth - 8;
        top = triggerRect.top + triggerRect.height / 2 - tooltipHeight / 2;
        break;
      case 'right':
        left = triggerRect.right + 8;
        top = triggerRect.top + triggerRect.height / 2 - tooltipHeight / 2;
        break;
    }
    
    // Ensure tooltip stays within viewport
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipWidth - 8));
    top = Math.max(8, Math.min(top, window.innerHeight - tooltipHeight - 8));
    
    return { left, top };
  };

  const getAnimationProps = () => {
    switch (position) {
      case 'top':
        return { initial: { opacity: 0, y: 10, scale: 0.9 }, animate: { opacity: 1, y: 0, scale: 1 } };
      case 'bottom':
        return { initial: { opacity: 0, y: -10, scale: 0.9 }, animate: { opacity: 1, y: 0, scale: 1 } };
      case 'left':
        return { initial: { opacity: 0, x: 10, scale: 0.9 }, animate: { opacity: 1, x: 0, scale: 1 } };
      case 'right':
        return { initial: { opacity: 0, x: -10, scale: 0.9 }, animate: { opacity: 1, x: 0, scale: 1 } };
      default:
        return { initial: { opacity: 0, y: 10, scale: 0.9 }, animate: { opacity: 1, y: 0, scale: 1 } };
    }
  };
  
  return (
    <span className="relative inline-block">
      <span
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setIsVisible(false)}
      >
        {children}
      </span>
      {isVisible && (
        <TooltipPortal>
          <motion.div
            ref={tooltipRef}
            {...getAnimationProps()}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            className="fixed inline-block w-80 max-w-sm"
            style={{
              ...getTooltipPosition(),
              maxWidth: '320px',
              maxHeight: position === 'top' || position === 'bottom' ? '400px' : '300px',
              width: '320px',
              zIndex: 999999,
              pointerEvents: 'auto', // Enable pointer events for tooltip content
            }}
          >
            <div className={cn(
              'rounded-lg border p-3 shadow-xl block overflow-y-auto overflow-x-hidden break-words',
              variant === 'glassmorphism'
                ? 'bg-black/90 backdrop-blur-md border-white/30 text-white'
                : 'glass-light border-white/20'
            )}>
              {content}
            </div>
          </motion.div>
        </TooltipPortal>
      )}
    </span>
  );
};

// Compact Document Card for tooltip previews
export const CompactDocumentCard: React.FC<{
  document: OnyxDocument;
  updatePresentingDocument: (document: OnyxDocument) => void;
  icon?: React.ReactNode;
  url?: string;
  variant?: 'glassmorphism' | 'neumorphic';
}> = ({ document, updatePresentingDocument, icon, url, variant = 'glassmorphism' }) => {
  const handleClick = () => {
    openDocument(document, updatePresentingDocument);
  };

  const displayText = document.match_highlights?.[0] || document.blurb || '';
  const truncatedText = displayText.length > 300 ? displayText.slice(0, 300) + '...' : displayText;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={handleClick}
      className={cn(
        'cursor-pointer transition-all duration-200',
        variant === 'glassmorphism'
          ? 'hover:glass-effect'
          : 'hover:bg-gray-100'
      )}
    >
      <div className="flex items-start space-x-3">
        <div className={cn(
          'flex-shrink-0 p-2 rounded-lg',
          variant === 'glassmorphism'
            ? 'glass-light'
            : 'bg-gray-100'
        )}>
          {icon || <FileText className={cn(
            'w-4 h-4',
            variant === 'glassmorphism' ? 'text-white/70' : 'text-gray-600'
          )} />}
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className={cn(
            'text-sm font-medium mb-1',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
          )}>
            {getDocumentTitle(document)}
          </h4>
          
          {/* Show filename as subtitle if different from extracted title */}
          {getDocumentTitle(document) !== document.semantic_identifier && (
            <div className={cn(
              'text-xs mb-1',
              variant === 'glassmorphism' ? 'text-white/40' : 'text-gray-500'
            )}>
              {document.semantic_identifier}
            </div>
          )}
          
          <div className="mb-2">
            <TooltipMarkdown variant={variant}>
              {truncatedText}
            </TooltipMarkdown>
          </div>
          
          <div className={cn(
            'flex items-center space-x-2 text-xs',
            variant === 'glassmorphism' ? 'text-white/50' : 'text-gray-500'
          )}>
            <span className="px-2 py-0.5 rounded-full bg-current/20">
              {document.source_type}
            </span>
            
            {document.score && (
              <span className="px-2 py-0.5 rounded-full bg-current/20">
                Score: {(document.score * 100).toFixed(0)}%
              </span>
            )}
            
            {document.link && (
              <div className="flex items-center space-x-1">
                <ExternalLink className="w-3 h-3" />
                <span className="truncate max-w-20">Link</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Compact Question Card for sub-question citations
export const CompactQuestionCard: React.FC<{
  question: SubQuestionDetail;
  openQuestion: (question: SubQuestionDetail) => void;
  variant?: 'glassmorphism' | 'neumorphic';
}> = ({ question, openQuestion, variant = 'glassmorphism' }) => {
  const handleClick = () => {
    openQuestion(question);
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={handleClick}
      className={cn(
        'cursor-pointer transition-all duration-200',
        variant === 'glassmorphism'
          ? 'hover:glass-effect'
          : 'hover:bg-gray-100'
      )}
    >
      <div className="flex items-start space-x-3">
        <div className={cn(
          'flex-shrink-0 p-2 rounded-lg',
          variant === 'glassmorphism'
            ? 'glass-light'
            : 'bg-gray-100'
        )}>
          <Search className={cn(
            'w-4 h-4',
            variant === 'glassmorphism' ? 'text-white/70' : 'text-gray-600'
          )} />
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className={cn(
            'text-sm font-medium mb-1',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
          )}>
            Sub-Question {question.level_question_num + 1}
          </h4>
          
          <div className="mb-2">
            <TooltipMarkdown variant={variant}>
              {cleanSubQuestionText(question.question)}
            </TooltipMarkdown>
          </div>
          
          {question.answer && (
            <div className="mb-2 line-clamp-4">
              <TooltipMarkdown variant={variant}>
                {question.answer.length > 300 ? question.answer.slice(0, 300) + '...' : question.answer}
              </TooltipMarkdown>
            </div>
          )}
          
          <div className={cn(
            'flex items-center space-x-2 text-xs',
            variant === 'glassmorphism' ? 'text-white/50' : 'text-gray-500'
          )}>
            {/* Always show as complete for final answers */}
            <span className={cn(
              'px-2 py-0.5 rounded-full bg-green-500/20 text-green-300'
            )}>
              Complete
            </span>
            
            {question.context_docs?.top_documents?.length && (
              <span className="px-2 py-0.5 rounded-full bg-current/20">
                {question.context_docs.top_documents.length} docs
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Citation component with tooltip preview
export const Citation: React.FC<{
  children?: JSX.Element | string | null | ReactNode;
  document_info?: DocumentCardProps;
  question_info?: QuestionCardProps;
  index?: number;
  variant?: 'glassmorphism' | 'neumorphic';
}> = ({ children, document_info, question_info, index, variant = 'glassmorphism' }) => {
  let innerText = "";
  
  if (index !== undefined) {
    innerText = index.toString();
  }

  if (children) {
    const childrenString = children.toString();
    const childrenSegment1 = childrenString.split("[")[1];
    if (childrenSegment1 !== undefined) {
      const childrenSegment1_0 = childrenSegment1.split("]")[0];
      if (childrenSegment1_0 !== undefined) {
        innerText = childrenSegment1_0;
      }
    }
  }

  // If no document or question info, still render as citation but with explanatory tooltip
  if (!document_info && !question_info) {
    const explanatoryContent = (
      <span className="block p-3">
        <span className={cn(
          'text-sm font-medium mb-2 block',
          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
        )}>
          引用 {innerText}
        </span>
        <span className={cn(
          'text-xs leading-relaxed block',
          variant === 'glassmorphism' ? 'text-white/60' : 'text-gray-600'
        )}>
          此引用指向的文档当前不可用。这可能是因为：
        </span>
        <span className={cn(
          'text-xs mt-2 space-y-1 list-disc list-inside block',
          variant === 'glassmorphism' ? 'text-white/50' : 'text-gray-500'
        )}>
          <span className="block">• 搜索没有找到相关文档</span>
          <span className="block">• 文档索引尚未完成</span>
          <span className="block">• 回答基于 AI 的内置知识</span>
        </span>
      </span>
    );

    return (
      <Tooltip content={explanatoryContent} delayDuration={0} variant={variant}>
        <span
          className="inline-flex items-center cursor-help transition-all duration-200 ease-in-out"
        >
          <span
            className={cn(
              'flex items-center justify-center px-1 h-4 text-[10px] font-medium rounded-full border shadow-sm transition-all',
              variant === 'glassmorphism'
                ? 'text-white/50 bg-white/5 border-white/20 hover:bg-white/10 hover:text-white/70'
                : 'text-gray-500 bg-gray-50 border-gray-300 hover:bg-gray-100 hover:text-gray-700'
            )}
            style={{ transform: "translateY(-10%)", lineHeight: "1" }}
          >
            {innerText}
          </span>
        </span>
      </Tooltip>
    );
  }

  const handleClick = () => {
    if (document_info?.document) {
      openDocument(document_info.document, document_info.updatePresentingDocument);
    } else if (question_info?.question) {
      question_info.openQuestion(question_info.question);
    }
  };

  const tooltipContent = document_info?.document ? (
    <CompactDocumentCard
      document={document_info.document}
      updatePresentingDocument={document_info.updatePresentingDocument}
      icon={document_info.icon}
      url={document_info.url}
      variant={variant}
    />
  ) : question_info?.question ? (
    <CompactQuestionCard
      question={question_info.question}
      openQuestion={question_info.openQuestion}
      variant={variant}
    />
  ) : null;

  return (
    <Tooltip content={tooltipContent} delayDuration={0} variant={variant}>
      <span
        onClick={handleClick}
        className="inline-flex items-center cursor-pointer transition-all duration-200 ease-in-out"
      >
        <span
          className={cn(
            'flex items-center justify-center px-1 h-4 text-[10px] font-medium rounded-full border shadow-sm transition-all',
            variant === 'glassmorphism'
              ? 'text-white/70 bg-white/10 border-white/30 hover:bg-white/20 hover:text-white'
              : 'text-gray-700 bg-gray-100 border-gray-300 hover:bg-gray-200 hover:text-gray-900'
          )}
          style={{ transform: "translateY(-10%)", lineHeight: "1" }}
        >
          {innerText}
        </span>
      </span>
    </Tooltip>
  );
};

// Memoized components for performance
export const MemoizedCitation = memo(Citation);
export const MemoizedCompactDocumentCard = memo(CompactDocumentCard);
export const MemoizedCompactQuestionCard = memo(CompactQuestionCard);