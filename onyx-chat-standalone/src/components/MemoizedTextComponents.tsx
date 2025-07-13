'use client';

import React, { memo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { FileText, Globe, ExternalLink } from 'lucide-react';
// Simple deep equality check for React children comparison
const isEqual = (a: any, b: any): boolean => {
  if (a === b) return true;
  if (a == null || b == null) return false;
  if (typeof a !== typeof b) return false;
  
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((item, index) => isEqual(item, b[index]));
  }
  
  if (typeof a === 'object') {
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;
    return keysA.every(key => isEqual(a[key], b[key]));
  }
  
  return false;
};
import { 
  OnyxDocument, 
  SubQuestionDetail, 
  DocumentCardProps, 
  QuestionCardProps 
} from '@/types';
import { Citation } from './CitationComponents';
import { cn } from '@/lib/utils';

// Utility function to get file icon based on source type
const getSourceIcon = (sourceType: string, isInternet: boolean) => {
  if (isInternet || sourceType === "web") {
    return <Globe className="w-4 h-4" />;
  }
  
  switch (sourceType) {
    case "file":
    case "pdf":
      return <FileText className="w-4 h-4" />;
    case "slack":
      return <div className="w-4 h-4 rounded bg-purple-500 flex items-center justify-center text-xs font-bold text-white">S</div>;
    case "confluence":
      return <div className="w-4 h-4 rounded bg-blue-500 flex items-center justify-center text-xs font-bold text-white">C</div>;
    case "notion":
      return <div className="w-4 h-4 rounded bg-gray-800 flex items-center justify-center text-xs font-bold text-white">N</div>;
    case "google_drive":
      return <div className="w-4 h-4 rounded bg-green-500 flex items-center justify-center text-xs font-bold text-white">G</div>;
    default:
      return <FileText className="w-4 h-4" />;
  }
};

// Enhanced anchor component with citation support
export const MemoizedAnchor = memo(
  ({
    docs,
    subQuestions,
    openQuestion,
    href,
    updatePresentingDocument,
    children,
    variant = 'glassmorphism',
  }: {
    subQuestions?: SubQuestionDetail[];
    openQuestion?: (question: SubQuestionDetail) => void;
    docs?: OnyxDocument[] | null;
    updatePresentingDocument: (doc: OnyxDocument) => void;
    href?: string;
    children: React.ReactNode;
    variant?: 'glassmorphism' | 'neumorphic';
  }): JSX.Element => {
    const value = children?.toString();
    
    // Check if this is a citation link format [1], [D1], [Q1], etc.
    if (value?.startsWith("[") && value?.endsWith("]")) {
      const match = value.match(/\[(D|Q)?(\d+)\]/);
      
      if (match) {
        const match_item = match[2];
        if (match_item !== undefined) {
          const isSubQuestion = match[1] === "Q";
          const isDocument = match[1] === "D" || !match[1]; // [D1] or [1] are documents
          
          // Parse the numeric index (1-based in citation, 0-based in array)
          const citationIndex = parseInt(match_item, 10);
          const arrayIndex = citationIndex - 1;
          
          // Debug: Citation parsing
          console.log('🔍 MemoizedAnchor Citation parsing:', { 
            value, 
            match, 
            isDocument, 
            isSubQuestion, 
            citationIndex,
            arrayIndex, 
            docsLength: docs?.length,
            subQuestionsLength: subQuestions?.length,
            'docs array': docs,
            'subQuestions array': subQuestions
          });
          
          const associatedDoc = isDocument ? docs?.[arrayIndex] : null;
          
          // For sub-questions, match by level_question_num instead of array index
          let associatedSubQuestion = undefined;
          if (isSubQuestion && subQuestions) {
            // First try to find by level_question_num
            associatedSubQuestion = subQuestions.find(sq => 
              sq.level_question_num === citationIndex
            );
            
            // If not found by level_question_num, fall back to array index
            if (!associatedSubQuestion) {
              associatedSubQuestion = subQuestions[arrayIndex];
            }
            
            console.log('🔍 SubQuestion matching:', {
              citationIndex,
              foundByLevelNum: !!subQuestions.find(sq => sq.level_question_num === citationIndex),
              foundByArrayIndex: !!subQuestions[arrayIndex],
              associatedSubQuestion: associatedSubQuestion ? {
                question: associatedSubQuestion.question,
                level: associatedSubQuestion.level,
                level_question_num: associatedSubQuestion.level_question_num
              } : null
            });
          }
          
          console.log('🎯 Citation association result:', {
            associatedDoc: associatedDoc ? {
              id: associatedDoc.document_id,
              title: associatedDoc.semantic_identifier,
              hasLink: !!associatedDoc.link
            } : null,
            associatedSubQuestion: associatedSubQuestion ? {
              question: associatedSubQuestion.question,
              level: associatedSubQuestion.level
            } : null
          });
          
          // Always render citation if it's a valid format, even without associated data
          if (!associatedDoc && !associatedSubQuestion) {
            console.log('❌ No associated data found, rendering as styled citation:', { 
              value, 
              citationIndex,
              arrayIndex, 
              isDocument, 
              isSubQuestion,
              expectedDocIndex: isDocument ? arrayIndex : 'N/A',
              expectedSubQuestionIndex: isSubQuestion ? citationIndex : 'N/A',
              availableDocs: docs?.length || 0,
              availableSubQuestions: subQuestions?.length || 0
            });
            // Render as a styled citation placeholder with tooltip explaining the issue
            return (
              <Citation
                index={citationIndex}
                variant={variant}
                document_info={undefined}
                question_info={undefined}
              >
                {children}
              </Citation>
            );
          }
          
          // Create icon for the document
          let icon: React.ReactNode = null;
          if (associatedDoc) {
            icon = getSourceIcon(associatedDoc.source_type, associatedDoc.is_internet);
          }
          
          const documentCardProps: DocumentCardProps | undefined = associatedDoc
            ? {
                document: associatedDoc,
                updatePresentingDocument: updatePresentingDocument,
                icon: icon,
                url: associatedDoc.link || undefined,
              }
            : undefined;
            
          const questionCardProps: QuestionCardProps | undefined = 
            associatedSubQuestion && openQuestion
              ? {
                  question: associatedSubQuestion,
                  openQuestion: openQuestion,
                }
              : undefined;
          
          return (
            <Citation
              document_info={documentCardProps}
              question_info={questionCardProps}
              variant={variant}
            >
              {children}
            </Citation>
          );
        }
      }
    }
    
    // Regular link handling
    return (
      <MemoizedLink
        updatePresentingDocument={updatePresentingDocument}
        href={href}
        variant={variant}
      >
        {children}
      </MemoizedLink>
    );
  }
);

// Enhanced link component
export const MemoizedLink = memo(
  ({
    href,
    updatePresentingDocument,
    variant = 'glassmorphism',
    ...rest
  }: {
    href?: string;
    updatePresentingDocument?: (doc: OnyxDocument) => void;
    variant?: 'glassmorphism' | 'neumorphic';
    [key: string]: any;
  }) => {
    const value = rest.children;
    
    // Handle streaming indicator
    if (value?.toString().startsWith("*")) {
      return (
        <div className={cn(
          'flex-none inline-block rounded-full h-3 w-3 ml-2',
          variant === 'glassmorphism' 
            ? 'bg-white/20' 
            : 'bg-gray-800'
        )} />
      );
    }

    const handleMouseDown = useCallback(() => {
      let url = href || rest.children?.toString();

      if (url && !url.includes("://")) {
        // Only add https:// if the URL doesn't already have a protocol
        const httpsUrl = `https://${url}`;
        try {
          new URL(httpsUrl);
          url = httpsUrl;
        } catch {
          // If not a valid URL, don't modify original url
        }
      }
      if (url) {
        window.open(url, "_blank");
      }
    }, [href, rest.children]);

    return (
      <motion.a
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onMouseDown={handleMouseDown}
        className={cn(
          'cursor-pointer transition-colors inline-flex items-center space-x-1',
          variant === 'glassmorphism'
            ? 'text-blue-300 hover:text-blue-200'
            : 'text-blue-600 hover:text-blue-800'
        )}
      >
        <span>{rest.children}</span>
        {href && <ExternalLink className="w-3 h-3" />}
      </motion.a>
    );
  }
);

// Enhanced paragraph component
export const MemoizedParagraph = memo(
  function MemoizedParagraph({ 
    children, 
    fontSize = 'base',
    variant = 'glassmorphism'
  }: {
    children: React.ReactNode;
    fontSize?: 'sm' | 'base';
    variant?: 'glassmorphism' | 'neumorphic';
  }) {
    return (
      <div
        className={cn(
          'my-0 leading-relaxed',
          fontSize === 'sm' ? 'text-sm leading-tight' : 'text-base',
          variant === 'glassmorphism' 
            ? 'text-glass' 
            : 'text-gray-900 dark:text-gray-200'
        )}
      >
        {children}
      </div>
    );
  },
  (prevProps, nextProps) => {
    return isEqual(prevProps.children, nextProps.children) &&
           prevProps.fontSize === nextProps.fontSize &&
           prevProps.variant === nextProps.variant;
  }
);

// Set display names for debugging
MemoizedAnchor.displayName = "MemoizedAnchor";
MemoizedLink.displayName = "MemoizedLink";
MemoizedParagraph.displayName = "MemoizedParagraph";