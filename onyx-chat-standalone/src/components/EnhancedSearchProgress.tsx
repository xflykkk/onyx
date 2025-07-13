'use client';

import React, { useCallback, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  FileText,
  CheckCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileIcon,
  ExternalLink,
  Eye,
  EyeOff,
} from 'lucide-react';
import { StreamingPhase, StreamingPhaseText } from '@/lib/streaming';
import { SearchProgress, SubQueryPiece, DocumentInfoPacket, SubQuestionDetail, OnyxDocument } from '@/types';
import { cn } from '@/lib/utils';
import { cleanSubQuestionText } from '@/lib/subQuestions';
import SubQuestionItem from './SubQuestionItem';

interface EnhancedSearchProgressProps {
  progress: SearchProgress;
  variant?: 'glassmorphism' | 'neumorphic';
  className?: string;
  onDocumentClick?: (document: OnyxDocument) => void;
  onToggleCollapse?: (collapsed: boolean) => void;
}

enum ProgressState {
  Todo = 'todo',
  InProgress = 'in_progress',
  Done = 'done',
}


const StatusIndicator: React.FC<{ status: ProgressState }> = ({ status }) => {
  return (
    <div className="relative w-3 h-3 rounded-full">
      {status === ProgressState.Todo && (
        <div className="w-full h-full rounded-full border-2 border-gray-300 bg-white" />
      )}
      {status === ProgressState.InProgress && (
        <div className="w-full h-full rounded-full bg-blue-500 flex items-center justify-center">
          <Loader2 className="w-2 h-2 text-white animate-spin" />
        </div>
      )}
      {status === ProgressState.Done && (
        <div className="w-full h-full rounded-full bg-green-500 flex items-center justify-center">
          <CheckCircle className="w-2 h-2 text-white" />
        </div>
      )}
    </div>
  );
};



export default function EnhancedSearchProgress({
  progress,
  variant = 'glassmorphism',
  className,
  onDocumentClick,
  onToggleCollapse,
}: EnhancedSearchProgressProps) {
  const [isManuallyExpanded, setIsManuallyExpanded] = useState(false);

  // Convert progress to steps - 不再使用这种方式，直接展示子问题
  const hasSubQuestions = progress.subQuestions && progress.subQuestions.length > 0;
  const sortedSubQuestions = useMemo(() => {
    if (!hasSubQuestions) return [];
    return [...progress.subQuestions].sort((a, b) => {
      if (a.level !== b.level) return a.level - b.level;
      return a.level_question_num - b.level_question_num;
    });
  }, [progress.subQuestions, hasSubQuestions]);

  // 获取当前阶段的状态
  const getPhaseStatus = useCallback((targetPhase: StreamingPhase) => {
    const currentPhase = progress.phase as StreamingPhase;
    if (currentPhase === 'complete') return ProgressState.Done;
    if (currentPhase === targetPhase) return ProgressState.InProgress;
    if (currentPhase > targetPhase) return ProgressState.Done;
    return ProgressState.Todo;
  }, [progress.phase]);

  // 判断是否应该显示为折叠状态
  const shouldCollapse = progress.isCompleted && progress.isCollapsed && !isManuallyExpanded;
  
  // 切换折叠状态
  const handleToggleCollapse = useCallback(() => {
    if (progress.isCompleted) {
      const newExpanded = !isManuallyExpanded;
      setIsManuallyExpanded(newExpanded);
      onToggleCollapse?.(!newExpanded);
    }
  }, [progress.isCompleted, isManuallyExpanded, onToggleCollapse]);

  const containerClasses = cn(
    'w-full py-3 px-4 rounded-lg',
    variant === 'glassmorphism'
      ? 'glass-light border border-white/20'
      : 'neuro-flat bg-gray-50 border border-gray-200',
    className
  );

  if (!progress) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={containerClasses}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className={cn(
          'p-2 rounded-lg',
          variant === 'glassmorphism'
            ? 'glass-light'
            : 'neuro-flat bg-white'
        )}>
          {progress.isCompleted ? (
            <CheckCircle className={cn(
              'w-4 h-4',
              variant === 'glassmorphism' ? 'text-green-300' : 'text-green-600'
            )} />
          ) : (
            <Search className={cn(
              'w-4 h-4',
              variant === 'glassmorphism' ? 'text-white/80' : 'text-gray-600'
            )} />
          )}
        </div>
        <div className="flex-1">
          <div className={cn(
            'text-sm font-medium',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
          )}>
            {progress.isCompleted ? 'Search Completed' : 'Agent Search Progress'}
          </div>
          <div className={cn(
            'text-xs opacity-70',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
          )}>
            {progress.isCompleted 
              ? `Found ${hasSubQuestions ? sortedSubQuestions.length : 0} sub-questions`
              : (StreamingPhaseText[progress.phase as StreamingPhase] || 'Processing...')
            }
          </div>
        </div>
        
        {/* Collapse/Expand Toggle */}
        {progress.isCompleted && (
          <button
            onClick={handleToggleCollapse}
            className={cn(
              'p-2 rounded-lg transition-colors',
              variant === 'glassmorphism'
                ? 'hover:bg-white/20 text-white/70 hover:text-white'
                : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800'
            )}
            title={shouldCollapse ? 'Expand search details' : 'Collapse search details'}
          >
            {shouldCollapse ? (
              <Eye className="w-4 h-4" />
            ) : (
              <EyeOff className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* Progress Content */}
      <AnimatePresence mode="wait">
        {!shouldCollapse && (
          <motion.div
            key="progress-content"
            initial={progress.isCompleted ? { height: 0, opacity: 0 } : { height: 'auto', opacity: 1 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="relative">
              {/* Step 1: Analysis Phase */}
              <div className="relative">
                <div className={cn(
                  'absolute left-[5px] w-[2px] bg-gray-200',
                  'top-[15px]',
                  hasSubQuestions ? 'h-full' : 'h-4'
                )} />
                <div className="flex items-start pb-2">
                  <div className="absolute left-0 mt-[12px] z-10">
                    <StatusIndicator status={getPhaseStatus(StreamingPhase.ANSWER)} />
                  </div>
                  <div className="ml-8 w-full">
                    <div className="text-base font-medium text-gray-900">
                      Analyze and Generate Answer
                    </div>
                    <div className="text-sm text-gray-600">
                      {StreamingPhaseText[StreamingPhase.ANSWER]}
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 2: Sub-Questions (详细展示) */}
              {hasSubQuestions && (
                <div className="relative">
                  <div className={cn(
                    'absolute left-[5px] w-[2px] bg-gray-200',
                    'top-0 h-full'
                  )} />
                  <div className="flex items-start pb-2">
                    <div className="absolute left-0 mt-[12px] z-10">
                      <StatusIndicator status={getPhaseStatus(StreamingPhase.SUB_QUERIES)} />
                    </div>
                    <div className="ml-8 w-full">
                      <div className="text-base font-medium text-gray-900 mb-2">
                        Process Sub-Questions
                      </div>
                      <div className="border-l-2 border-gray-200 pl-4 ml-2">
                        {sortedSubQuestions.map((subQuestion, index) => (
                          <SubQuestionItem
                            key={`${subQuestion.level}-${subQuestion.level_question_num}`}
                            subQuestion={subQuestion}
                            isFirst={index === 0}
                            isLast={index === sortedSubQuestions.length - 1}
                            variant={variant}
                            onDocumentClick={onDocumentClick}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3: Final Summary */}
              <div className="relative">
                <div className={cn(
                  'absolute left-[5px] w-[2px] bg-gray-200',
                  'top-0',
                  'h-4'
                )} />
                <div className="flex items-start pb-2">
                  <div className="absolute left-0 mt-[12px] z-10">
                    <StatusIndicator status={progress.phase === 'complete' ? ProgressState.Done : ProgressState.Todo} />
                  </div>
                  <div className="ml-8 w-full">
                    <div className="text-base font-medium text-gray-900">
                      Generate Final Answer
                    </div>
                    <div className="text-sm text-gray-600">
                      Synthesizing all findings into comprehensive response
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export { ProgressState };