'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search,
  MessageSquare,
  FileText,
  Eye,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { SubQuestionDetail, OnyxDocument } from '@/types';
import { cleanSubQuestionText } from '@/lib/subQuestions';
import SubQuestionItem from './SubQuestionItem';
import { cn } from '@/lib/utils';

interface BaseQuestionIdentifier {
  level: number;
  level_question_num: number;
}

interface SubQuestionsDisplayProps {
  subQuestions: SubQuestionDetail[];
  variant?: 'glassmorphism' | 'neumorphic';
  onSubQuestionClick?: (question: SubQuestionDetail) => void;
  onDocumentClick?: (document: OnyxDocument) => void;
  isStreamingQuestions?: boolean;
  currentlyOpenQuestion?: BaseQuestionIdentifier | null;
  className?: string;
}

export default function SubQuestionsDisplay({
  subQuestions,
  variant = 'glassmorphism',
  onSubQuestionClick,
  onDocumentClick,
  isStreamingQuestions = false,
  currentlyOpenQuestion = null,
  className
}: SubQuestionsDisplayProps) {
  const [showProcessDetails, setShowProcessDetails] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false); // 默认折叠

  if (!subQuestions || subQuestions.length === 0) {
    return null;
  }

  // Sort sub-questions by level and level_question_num for consistent display
  const sortedSubQuestions = useMemo(() => {
    return [...subQuestions].sort((a, b) => {
      if (a.level !== b.level) return a.level - b.level;
      return a.level_question_num - b.level_question_num;
    });
  }, [subQuestions]);

  const handleSubQuestionClick = (question: SubQuestionDetail) => {
    onSubQuestionClick?.(question);
  };

  const containerClasses = cn(
    'w-full py-1.5 px-4 rounded-lg',
    variant === 'glassmorphism'
      ? 'glass-light border border-white/20'
      : 'neuro-flat bg-gray-50 border border-gray-200',
    className
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={containerClasses}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex-1">
          <div className={cn(
            'text-sm font-medium flex items-center space-x-2',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-900'
          )}>
            <Search className="w-4 h-4" />
            <span>Sub-Questions</span>
            <span className={cn(
              'text-xs px-2 py-0.5 rounded-full',
              variant === 'glassmorphism' 
                ? 'bg-white/20 text-white/70' 
                : 'bg-gray-200 text-gray-600'
            )}>
              {subQuestions.length}
            </span>
          </div>
          <div className={cn(
            'text-xs opacity-70 mt-0.5',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
          )}>
            {subQuestions.length} question{subQuestions.length !== 1 ? 's' : ''} analyzed
          </div>
        </div>
        
        {/* Toggle Expand/Collapse */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            'flex items-center space-x-1 text-xs transition-colors',
            variant === 'glassmorphism'
              ? 'text-white/70 hover:text-white'
              : 'text-gray-600 hover:text-gray-800'
          )}
        >
          <Eye className="w-3 h-3" />
          <span>{isExpanded ? 'Hide Details' : 'View Details'}</span>
          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
        
        {/* Toggle Process Details (only show when expanded) */}
        {isExpanded && (
          <button
            onClick={() => setShowProcessDetails(!showProcessDetails)}
            className={cn(
              'ml-2 px-2 py-1 text-xs rounded transition-colors',
              showProcessDetails
                ? variant === 'glassmorphism'
                  ? 'bg-blue-500/40 text-blue-200 border border-blue-400/40'
                  : 'bg-blue-100 text-blue-800 border border-blue-200'
                : variant === 'glassmorphism'
                  ? 'bg-white/10 text-white/70 border border-white/20 hover:bg-white/20'
                  : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'
            )}
          >
            {showProcessDetails ? 'Hide Process' : 'Show Process'}
          </button>
        )}
      </div>

      {/* Main Content - only show when expanded */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            {/* Process Details View */}
            {showProcessDetails && (
              <div className="mb-4">
                <div className="relative">
                  {sortedSubQuestions.map((subQuestion, index) => (
                    <SubQuestionItem
                      key={`${subQuestion.level}-${subQuestion.level_question_num}`}
                      subQuestion={subQuestion}
                      isFirst={index === 0}
                      isLast={index === sortedSubQuestions.length - 1}
                      variant={variant}
                      onDocumentClick={onDocumentClick}
                      currentlyOpen={
                        currentlyOpenQuestion?.level === subQuestion.level &&
                        currentlyOpenQuestion?.level_question_num === subQuestion.level_question_num
                      }
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Summary View (Default when expanded) */}
            {!showProcessDetails && (
              <div className="space-y-2">
                {sortedSubQuestions.map((subQuestion, index) => (
                  <motion.div
                    key={`${subQuestion.level}-${subQuestion.level_question_num}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => handleSubQuestionClick(subQuestion)}
                    className={cn(
                      'p-3 rounded border cursor-pointer transition-all group',
                      variant === 'glassmorphism'
                        ? 'glass-light border-white/20 hover:glass-effect'
                        : 'neuro-flat bg-white border-gray-200 hover:neuro-raised'
                    )}
                  >
                    <div className="flex items-start space-x-2">
                      {/* Question Number */}
                      <div className={cn(
                        'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold',
                        variant === 'glassmorphism'
                          ? 'glass-effect text-white/80'
                          : 'neuro-raised bg-blue-100 text-blue-600'
                      )}>
                        Q{subQuestion.level_question_num}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        {/* Question Text */}
                        <h4 className={cn(
                          'text-xs font-medium mb-1 leading-snug',
                          variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
                        )}>
                          {cleanSubQuestionText(subQuestion.question)}
                        </h4>
                        
                        {/* Answer Preview */}
                        {subQuestion.answer && (
                          <div className={cn(
                            'text-xs leading-snug mb-2',
                            variant === 'glassmorphism' ? 'text-white/60' : 'text-gray-600'
                          )}>
                            {subQuestion.answer.length > 100 
                              ? subQuestion.answer.slice(0, 100) + '...' 
                              : subQuestion.answer
                            }
                          </div>
                        )}
                        
                        {/* Metadata */}
                        <div className={cn(
                          'flex items-center space-x-2 text-xs',
                          variant === 'glassmorphism' ? 'text-white/50' : 'text-gray-500'
                        )}>
                          {/* Status */}
                          <span className={cn(
                            'px-1.5 py-0.5 rounded text-xs',
                            subQuestion.is_complete
                              ? 'bg-green-500/20 text-green-300'
                              : subQuestion.answer_streaming
                              ? 'bg-blue-500/20 text-blue-300'
                              : 'bg-gray-500/20 text-gray-400'
                          )}>
                            {subQuestion.is_complete ? 'Complete' : 
                             subQuestion.answer_streaming ? 'Processing' : 'Pending'}
                          </span>
                          
                          {/* Sub-queries count */}
                          {subQuestion.sub_queries && subQuestion.sub_queries.length > 0 && (
                            <span className="flex items-center space-x-1">
                              <MessageSquare className="w-3 h-3" />
                              <span>{subQuestion.sub_queries.length} queries</span>
                            </span>
                          )}
                          
                          {/* Documents count */}
                          {subQuestion.context_docs?.top_documents?.length && (
                            <span className="flex items-center space-x-1">
                              <FileText className="w-3 h-3" />
                              <span>{subQuestion.context_docs.top_documents.length} docs</span>
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}