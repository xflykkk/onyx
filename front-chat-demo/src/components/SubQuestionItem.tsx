'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronDown, 
  Search, 
  FileText, 
  CheckCircle,
  Loader2,
  Clock,
} from 'lucide-react';
import { SubQuestionDetail, OnyxDocument } from '@/types';
import { cleanSubQuestionText } from '@/lib/subQuestions';
import { cn } from '@/lib/utils';

enum ProgressState {
  Todo = 'todo',
  InProgress = 'in_progress', 
  Done = 'done',
}

interface SearchSubItem {
  id: string;
  type: 'query' | 'document' | 'analysis';
  content: string;
  status: ProgressState;
  metadata?: any;
}

interface SubQuestionItemProps {
  subQuestion: SubQuestionDetail;
  isFirst?: boolean;
  isLast?: boolean;
  variant?: 'glassmorphism' | 'neumorphic';
  onDocumentClick?: (document: OnyxDocument) => void;
  currentlyOpen?: boolean;
  forcedStatus?: ProgressState;
  temporaryDisplay?: {
    question: string;
    tinyQuestion: string;
  };
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

export default function SubQuestionItem({
  subQuestion,
  isFirst = false,
  isLast = false,
  variant = 'glassmorphism',
  onDocumentClick,
  currentlyOpen = false,
  forcedStatus,
  temporaryDisplay,
}: SubQuestionItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [status, setStatus] = useState<ProgressState>(
    subQuestion.is_complete ? ProgressState.Done : 
    subQuestion.answer_streaming ? ProgressState.InProgress : 
    ProgressState.Todo
  );

  // Update status based on sub-question state
  useEffect(() => {
    if (forcedStatus) {
      setStatus(forcedStatus);
      return;
    }
    
    if (subQuestion.is_complete) {
      setStatus(ProgressState.Done);
    } else if (subQuestion.answer_streaming || (subQuestion.answer && subQuestion.answer.length > 0)) {
      setStatus(ProgressState.InProgress);
    } else {
      setStatus(ProgressState.Todo);
    }
  }, [subQuestion.is_complete, subQuestion.answer_streaming, subQuestion.answer, forcedStatus]);

  // Auto-expand when currently open
  useEffect(() => {
    if (currentlyOpen) {
      setIsExpanded(true);
    }
  }, [currentlyOpen]);

  const handleToggle = useCallback(() => {
    setIsExpanded(!isExpanded);
  }, [isExpanded]);

  const cleanedQuestion = cleanSubQuestionText(subQuestion.question);
  const hasSubQueries = subQuestion.sub_queries && subQuestion.sub_queries.length > 0;
  const hasDocuments = subQuestion.context_docs?.top_documents && subQuestion.context_docs.top_documents.length > 0;
  const hasAnswer = subQuestion.answer && subQuestion.answer.length > 0;

  // Convert data to SearchSubItem format for display
  const searchItems: SearchSubItem[] = [];
  
  // Add search queries
  if (hasSubQueries) {
    subQuestion.sub_queries!.forEach((query, index) => {
      if (query.query.trim()) {
        searchItems.push({
          id: `query-${index}`,
          type: 'query',
          content: cleanSubQuestionText(query.query),
          status: ProgressState.Done,
        });
      }
    });
  }

  // Add documents
  if (hasDocuments) {
    subQuestion.context_docs!.top_documents.forEach((doc, index) => {
      searchItems.push({
        id: `doc-${index}`,
        type: 'document',
        content: doc.semantic_identifier || doc.document_id,
        status: ProgressState.Done,
        metadata: doc,
      });
    });
  }

  // Add analysis
  if (hasAnswer) {
    searchItems.push({
      id: 'analysis',
      type: 'analysis',
      content: subQuestion.answer!,
      status: subQuestion.answer_streaming ? ProgressState.InProgress : ProgressState.Done,
    });
  }

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
          <StatusIndicator status={status} />
        </div>

        {/* Step Content */}
        <div className="ml-8 w-full">
          {/* Step Header */}
          <div
            className={cn(
              'flex items-center justify-between -mx-2 rounded-md px-2 py-1.5 my-0.5',
              'hover:bg-gray-50 cursor-pointer transition-colors'
            )}
            onClick={handleToggle}
          >
            <div className="flex-grow">
              <div className="text-base font-medium text-gray-900">
                {temporaryDisplay ? temporaryDisplay.question : cleanedQuestion}
              </div>
              <div className="text-sm text-gray-600">
                {temporaryDisplay ? temporaryDisplay.tinyQuestion : 
                 hasSubQueries ? `${subQuestion.sub_queries!.length} searches` : 'Preparing search...'
                }
              </div>
            </div>
            <motion.div
              animate={{ rotate: isExpanded ? 0 : -90 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-5 h-5 text-gray-400" />
            </motion.div>
          </div>

          {/* Step Content */}
          <AnimatePresence>
            {isExpanded && !temporaryDisplay && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="pl-0 pb-2">
                  {/* Search Queries */}
                  {searchItems.some(item => item.type === 'query') && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-gray-600 mb-2">
                        Search Queries
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {searchItems
                          .filter(item => item.type === 'query')
                          .map((item) => (
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
                  {searchItems.some(item => item.type === 'document') && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-gray-600 mb-2">
                        Found Documents
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {searchItems
                          .filter(item => item.type === 'document')
                          .slice(0, 8) // Limit to 8 documents
                          .map((item) => (
                            <SourceChip
                              key={item.id}
                              icon={<FileText className="w-3 h-3" />}
                              title={item.content}
                              includeAnimation
                              onClick={() => {
                                if (item.metadata && onDocumentClick) {
                                  onDocumentClick(item.metadata);
                                }
                              }}
                            />
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Analysis */}
                  {searchItems.some(item => item.type === 'analysis') && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-gray-600 mb-2">
                        Analysis
                      </div>
                      <div className="text-sm text-gray-700 space-y-1">
                        {searchItems
                          .filter(item => item.type === 'analysis')
                          .map((item) => (
                            <div key={item.id} className="p-2 bg-gray-50 rounded">
                              {item.content.length > 200 
                                ? item.content.slice(0, 200) + '...' 
                                : item.content
                              }
                              {item.status === ProgressState.InProgress && (
                                <span className="ml-1 text-blue-500">●</span>
                              )}
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Temporary Display Content */}
          {temporaryDisplay && isExpanded && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="pl-0 pb-2"
            >
              <div className="text-xs text-gray-600">
                {temporaryDisplay.tinyQuestion}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}