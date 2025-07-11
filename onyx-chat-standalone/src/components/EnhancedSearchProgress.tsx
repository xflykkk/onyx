'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
} from 'lucide-react';
import { StreamingPhase, StreamingPhaseText } from '@/lib/streaming';
import { SearchProgress, SubQueryPiece, DocumentInfoPacket } from '@/types';
import { cn } from '@/lib/utils';

interface EnhancedSearchProgressProps {
  progress: SearchProgress;
  variant?: 'glassmorphism' | 'neumorphic';
  className?: string;
}

enum ProgressState {
  Todo = 'todo',
  InProgress = 'in_progress',
  Done = 'done',
}

interface SearchStep {
  id: string;
  title: string;
  description: string;
  status: ProgressState;
  subItems?: SearchSubItem[];
  isCollapsible?: boolean;
  isExpanded?: boolean;
  startTime?: number;
  elapsedTime?: number;
}

interface SearchSubItem {
  id: string;
  type: 'query' | 'document' | 'analysis';
  content: string;
  status: ProgressState;
  metadata?: any;
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

const SourceChip: React.FC<{
  icon: React.ReactNode;
  title: string;
  onClick?: () => void;
  includeAnimation?: boolean;
  className?: string;
}> = ({ icon, title, onClick, includeAnimation = false, className }) => {
  return (
    <motion.div
      initial={includeAnimation ? { opacity: 0, scale: 0.8 } : undefined}
      animate={includeAnimation ? { opacity: 1, scale: 1 } : undefined}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border',
        'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100',
        'cursor-pointer transition-colors',
        className
      )}
      title={title}
    >
      {icon}
      <span className="truncate max-w-32">{title}</span>
    </motion.div>
  );
};

const SearchStepDisplay: React.FC<{
  step: SearchStep;
  isFirst: boolean;
  isLast: boolean;
  onToggle?: () => void;
  variant?: 'glassmorphism' | 'neumorphic';
}> = ({ step, isFirst, isLast, onToggle, variant = 'glassmorphism' }) => {
  const [isExpanded, setIsExpanded] = useState(step.isExpanded || false);

  const handleToggle = useCallback(() => {
    setIsExpanded(!isExpanded);
    onToggle?.();
  }, [isExpanded, onToggle]);

  const hasSubItems = step.subItems && step.subItems.length > 0;

  return (
    <div className="relative">
      {/* Vertical Line */}
      <div
        className={cn(
          'absolute left-[5px] w-[2px] bg-gray-200',
          isFirst ? 'top-[15px]' : 'top-0',
          isLast && !isExpanded ? 'h-4' : 'h-full'
        )}
      />

      {/* Step Container */}
      <div className="flex items-start pb-2">
        {/* Status Indicator */}
        <div className="absolute left-0 mt-[12px] z-10">
          <StatusIndicator status={step.status} />
        </div>

        {/* Step Content */}
        <div className="ml-8 w-full">
          {/* Step Header */}
          <div
            className={cn(
              'flex items-center justify-between -mx-2 rounded-md px-2 py-1.5 my-0.5',
              'hover:bg-gray-50 cursor-pointer transition-colors',
              step.isCollapsible && 'cursor-pointer'
            )}
            onClick={step.isCollapsible ? handleToggle : undefined}
          >
            <div className="flex-grow">
              <div className="text-base font-medium text-gray-900">
                {step.title}
              </div>
              <div className="text-sm text-gray-600">
                {step.description}
              </div>
              {step.elapsedTime && (
                <div className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                  <Clock className="w-3 h-3" />
                  {step.elapsedTime}ms
                </div>
              )}
            </div>
            {step.isCollapsible && (
              <motion.div
                animate={{ rotate: isExpanded ? 0 : -90 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronDown className="w-5 h-5 text-gray-400" />
              </motion.div>
            )}
          </div>

          {/* Step Content */}
          <AnimatePresence>
            {isExpanded && hasSubItems && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="pl-0 pb-2">
                  {/* Search Queries */}
                  {step.subItems?.some(item => item.type === 'query') && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-gray-600 mb-2">
                        Search Queries
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {step.subItems
                          .filter(item => item.type === 'query')
                          .map((item, index) => (
                            <SourceChip
                              key={item.id}
                              icon={<Search className="w-3 h-3" />}
                              title={item.content}
                              includeAnimation
                            />
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Documents */}
                  {step.subItems?.some(item => item.type === 'document') && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-gray-600 mb-2">
                        Found Documents
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {step.subItems
                          .filter(item => item.type === 'document')
                          .slice(0, 8) // Limit to 8 documents
                          .map((item, index) => (
                            <SourceChip
                              key={item.id}
                              icon={<FileText className="w-3 h-3" />}
                              title={item.content}
                              includeAnimation
                              onClick={() => {
                                if (item.metadata?.link) {
                                  window.open(item.metadata.link, '_blank');
                                }
                              }}
                            />
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Analysis */}
                  {step.subItems?.some(item => item.type === 'analysis') && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-gray-600 mb-2">
                        Analysis
                      </div>
                      <div className="text-sm text-gray-700 space-y-1">
                        {step.subItems
                          .filter(item => item.type === 'analysis')
                          .map((item, index) => (
                            <div key={item.id} className="p-2 bg-gray-50 rounded">
                              {item.content}
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default function EnhancedSearchProgress({
  progress,
  variant = 'glassmorphism',
  className,
}: EnhancedSearchProgressProps) {
  const [steps, setSteps] = useState<SearchStep[]>([]);

  // Convert progress to steps
  const generateSteps = useCallback((progress: SearchProgress): SearchStep[] => {
    const steps: SearchStep[] = [];
    const currentPhase = progress.phase as StreamingPhase;

    // Step 1: Query Generation
    const hasSubQueries = progress.subQueries && progress.subQueries.length > 0;
    const subQueryItems: SearchSubItem[] = progress.subQueries?.map((sq, index) => ({
      id: `subquery-${index}`,
      type: 'query' as const,
      content: sq.sub_query,
      status: sq.status === 'done' ? ProgressState.Done : 
              sq.status === 'in_progress' ? ProgressState.InProgress : ProgressState.Todo,
    })) || [];

    steps.push({
      id: 'queries',
      title: 'Generate Search Queries',
      description: StreamingPhaseText[StreamingPhase.SUB_QUERIES],
      status: currentPhase >= StreamingPhase.SUB_QUERIES && hasSubQueries ? ProgressState.Done :
              currentPhase === StreamingPhase.SUB_QUERIES ? ProgressState.InProgress : ProgressState.Todo,
      subItems: subQueryItems,
      isCollapsible: hasSubQueries,
      isExpanded: currentPhase === StreamingPhase.SUB_QUERIES || hasSubQueries,
    });

    // Step 2: Document Retrieval
    const hasDocuments = progress.documents && progress.documents.length > 0;
    const documentItems: SearchSubItem[] = progress.documents?.map((doc, index) => ({
      id: `doc-${index}`,
      type: 'document' as const,
      content: doc.document_name || doc.semantic_identifier || `Document ${index + 1}`,
      status: ProgressState.Done,
      metadata: {
        link: doc.link,
        score: doc.score,
        sourceType: doc.source_type,
      }
    })) || [];

    steps.push({
      id: 'documents',
      title: 'Find Relevant Documents',
      description: StreamingPhaseText[StreamingPhase.CONTEXT_DOCS],
      status: currentPhase >= StreamingPhase.ANSWER && hasDocuments ? ProgressState.Done :
              currentPhase === StreamingPhase.CONTEXT_DOCS ? ProgressState.InProgress : ProgressState.Todo,
      subItems: documentItems,
      isCollapsible: hasDocuments,
      isExpanded: currentPhase === StreamingPhase.CONTEXT_DOCS || hasDocuments,
    });

    // Step 3: Analysis and Answer
    const hasAnswer = progress.currentAnswer && progress.currentAnswer.length > 0;
    const analysisItems: SearchSubItem[] = [];
    if (progress.thinkingContent) {
      analysisItems.push({
        id: 'thinking',
        type: 'analysis',
        content: progress.thinkingContent,
        status: ProgressState.Done,
      });
    }

    steps.push({
      id: 'analysis',
      title: 'Analyze and Generate Answer',
      description: StreamingPhaseText[StreamingPhase.ANSWER],
      status: currentPhase >= StreamingPhase.COMPLETE ? ProgressState.Done :
              currentPhase === StreamingPhase.ANSWER ? ProgressState.InProgress : ProgressState.Todo,
      subItems: analysisItems,
      isCollapsible: analysisItems.length > 0,
      isExpanded: currentPhase === StreamingPhase.ANSWER,
    });

    return steps;
  }, []);

  // Update steps when progress changes
  useEffect(() => {
    const newSteps = generateSteps(progress);
    setSteps(newSteps);
  }, [progress, generateSteps]);

  const containerClasses = cn(
    'w-full p-4 rounded-lg',
    variant === 'glassmorphism'
      ? 'glass-light border border-white/20'
      : 'neuro-flat bg-gray-50 border border-gray-200',
    className
  );

  if (!progress || steps.length === 0) {
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
          <Search className={cn(
            'w-4 h-4',
            variant === 'glassmorphism' ? 'text-white/80' : 'text-gray-600'
          )} />
        </div>
        <div>
          <div className={cn(
            'text-sm font-medium',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-800'
          )}>
            Agent Search Progress
          </div>
          <div className={cn(
            'text-xs opacity-70',
            variant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
          )}>
            {StreamingPhaseText[progress.phase as StreamingPhase] || 'Processing...'}
          </div>
        </div>
      </div>

      {/* Steps */}
      <div className="relative">
        {steps.map((step, index) => (
          <SearchStepDisplay
            key={step.id}
            step={step}
            isFirst={index === 0}
            isLast={index === steps.length - 1}
            variant={variant}
          />
        ))}
      </div>
    </motion.div>
  );
}

export { ProgressState, type SearchStep, type SearchSubItem };