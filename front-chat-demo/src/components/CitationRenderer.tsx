'use client';

import React from 'react';
import { OnyxDocument, SubQuestionDetail } from '@/types';
import { MemoizedAnchor } from './MemoizedTextComponents';

interface CitationRendererProps {
  text: string;
  docs?: OnyxDocument[];
  subQuestions?: SubQuestionDetail[];
  onDocumentClick?: (doc: OnyxDocument) => void;
  onSubQuestionClick?: (question: SubQuestionDetail) => void;
  variant?: 'glassmorphism' | 'neumorphic';
}

export const CitationRenderer: React.FC<CitationRendererProps> = ({
  text,
  docs = [],
  subQuestions = [],
  onDocumentClick,
  onSubQuestionClick,
  variant = 'glassmorphism',
}) => {
  // Enhanced regex to catch various citation patterns
  const citationRegex = /\[([DQ]?\d+)\]/g;
  
  if (!citationRegex.test(text)) {
    return <>{text}</>;
  }

  // Split text while keeping delimiters
  const parts = text.split(/(\[[DQ]?\d+\])/);
  
  return (
    <>
      {parts.map((part, index) => {
        const match = part.match(/\[([DQ]?\d+)\]/);
        
        if (match) {
          console.log('CitationRenderer: Found citation', part, match);
          
          return (
            <MemoizedAnchor
              key={index}
              docs={docs}
              subQuestions={subQuestions}
              openQuestion={onSubQuestionClick}
              updatePresentingDocument={onDocumentClick || (() => {})}
              variant={variant}
            >
              {part}
            </MemoizedAnchor>
          );
        }
        
        return <span key={index}>{part}</span>;
      })}
    </>
  );
};

export default CitationRenderer;