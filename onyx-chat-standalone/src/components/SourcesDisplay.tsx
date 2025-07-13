'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  Globe, 
  ChevronDown, 
  ChevronUp, 
  ExternalLink,
  Eye,
  Search
} from 'lucide-react';
import { OnyxDocument } from '@/types';
import { cn } from '@/lib/utils';
import { getDocumentTitle } from '@/lib/documentUtils';

// Source icon component
const SourceIcon: React.FC<{
  sourceType: string;
  isInternet?: boolean;
  size?: number;
}> = ({ sourceType, isInternet = false, size = 18 }) => {
  const className = `w-${size/4} h-${size/4}`;
  
  if (isInternet || sourceType === "web") {
    return <Globe className={className} />;
  }
  
  switch (sourceType) {
    case "file":
    case "pdf":
      return <FileText className={className} />;
    case "slack":
      return (
        <div className={`${className} rounded bg-purple-500 flex items-center justify-center text-xs font-bold text-white`}>
          S
        </div>
      );
    case "confluence":
      return (
        <div className={`${className} rounded bg-blue-500 flex items-center justify-center text-xs font-bold text-white`}>
          C
        </div>
      );
    case "notion":
      return (
        <div className={`${className} rounded bg-gray-800 flex items-center justify-center text-xs font-bold text-white`}>
          N
        </div>
      );
    case "google_drive":
      return (
        <div className={`${className} rounded bg-green-500 flex items-center justify-center text-xs font-bold text-white`}>
          G
        </div>
      );
    default:
      return <FileText className={className} />;
  }
};

// Individual source card component
export const SourceCard: React.FC<{
  document: OnyxDocument;
  setPresentingDocument: (document: OnyxDocument) => void;
  variant?: 'glassmorphism' | 'neumorphic';
  hideDocumentDisplay?: boolean;
  compact?: boolean;
  isExpanded?: boolean;
}> = ({ document, setPresentingDocument, variant = 'glassmorphism', hideDocumentDisplay = false, compact = false, isExpanded = false }) => {
  const handleClick = () => {
    if (document.link) {
      window.open(document.link, '_blank');
    }
    setPresentingDocument(document);
  };

  // Get display text with highlights
  const getDisplayText = () => {
    if (hideDocumentDisplay) {
      return document.blurb || '';
    }
    
    if (document.match_highlights && document.match_highlights.length > 0) {
      return document.match_highlights[0];
    }
    
    return document.blurb || '';
  };

  const displayText = getDisplayText();
  const maxTextLength = compact ? 60 : 80;
  const maxTitleLength = compact ? 25 : 30;
  const truncatedText = displayText.length > maxTextLength ? displayText.slice(0, maxTextLength) + '...' : displayText;
  const documentTitle = getDocumentTitle(document);
  const truncatedIdentifier = documentTitle.length > maxTitleLength ? documentTitle.slice(0, maxTitleLength) + '...' : documentTitle;

  return (
    <motion.button
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={handleClick}
      className={cn(
        'w-full text-left cursor-pointer transition-all duration-200',
        'flex flex-col justify-between overflow-hidden',
        compact 
          ? (isExpanded ? 'h-[60px] p-2 rounded border' : 'h-[30px] p-2 rounded border')
          : 'max-w-[260px] h-[80px] p-3 rounded-lg',
        variant === 'glassmorphism'
          ? 'glass-light border-white/20 hover:glass-effect'
          : 'neuro-flat bg-gray-50 border-gray-200 hover:neuro-raised'
      )}
    >
      {/* Document content */}
      <div className={cn(
        'font-medium leading-tight whitespace-normal break-all line-clamp-2 overflow-hidden',
        compact ? 'text-xs' : 'text-xs',
        variant === 'glassmorphism' ? 'text-glass' : 'text-gray-900'
      )}>
        {truncatedText}
      </div>

      {/* Document info */}
      <div className={cn(
        'flex items-center gap-1',
        compact ? 'mt-1' : 'mt-1'
      )}>
        <SourceIcon 
          sourceType={document.source_type} 
          isInternet={document.is_internet}
          size={compact ? 14 : 18} 
        />
        
        <div className={cn(
          'leading-tight truncate flex-1 min-w-0',
          compact ? 'text-xs' : 'text-xs',
          variant === 'glassmorphism' ? 'text-white/70' : 'text-gray-700'
        )}>
          {truncatedIdentifier}
        </div>
        
        {document.score && (
          <div className={cn(
            'px-1 py-0.5 rounded bg-current/20',
            compact ? 'text-xs' : 'text-xs',
            variant === 'glassmorphism' ? 'text-white/60' : 'text-gray-600'
          )}>
            {Math.round(document.score * 100)}%
          </div>
        )}
      </div>
    </motion.button>
  );
};

// See more block for additional documents
export const SeeMoreBlock: React.FC<{
  toggleDocumentSelection: () => void;
  docs: OnyxDocument[];
  toggled: boolean;
  variant?: 'glassmorphism' | 'neumorphic';
  fullWidth?: boolean;
}> = ({ toggleDocumentSelection, docs, toggled, variant = 'glassmorphism', fullWidth = false }) => {
  // Get unique icons for preview
  const getUniqueIcons = () => {
    const uniqueIcons: React.ReactNode[] = [];
    const seenTypes = new Set<string>();
    
    for (const doc of docs.slice(0, 3)) {
      const key = doc.is_internet ? 'web' : doc.source_type;
      if (!seenTypes.has(key)) {
        seenTypes.add(key);
        uniqueIcons.push(
          <SourceIcon 
            key={key}
            sourceType={doc.source_type} 
            isInternet={doc.is_internet}
            size={18} 
          />
        );
      }
    }
    
    return uniqueIcons.slice(0, 3);
  };

  const icons = getUniqueIcons();

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={toggleDocumentSelection}
      className={cn(
        'h-[80px] p-3 border text-left cursor-pointer rounded-lg',
        'flex flex-col justify-between overflow-hidden transition-all duration-200',
        fullWidth ? 'w-full' : 'max-w-[200px]',
        variant === 'glassmorphism'
          ? 'glass-light border-white/20 hover:glass-effect'
          : 'neuro-flat bg-gray-50 border border-gray-200 hover:neuro-raised'
      )}
    >
      <div className="flex items-center gap-1">
        {icons.map((icon, index) => (
          <div key={index} className="flex-shrink-0">
            {icon}
          </div>
        ))}
      </div>
      
      <div className={cn(
        'text-xs font-semibold',
        variant === 'glassmorphism' ? 'text-white/80' : 'text-gray-700'
      )}>
        {toggled ? 'Hide Results' : 'Show All'}
      </div>
    </motion.button>
  );
};

// Main sources display component
export const SourcesDisplay: React.FC<{
  documents: OnyxDocument[];
  toggleDocumentSelection: () => void;
  setPresentingDocument: (document: OnyxDocument) => void;
  variant?: 'glassmorphism' | 'neumorphic';
  animateEntrance?: boolean;
  threeCols?: boolean;
  hideDocumentDisplay?: boolean;
  docSidebarToggled?: boolean;
  className?: string;
  compact?: boolean;
  defaultCollapsed?: boolean;
}> = ({
  documents,
  toggleDocumentSelection,
  setPresentingDocument,
  variant = 'glassmorphism',
  animateEntrance = false,
  threeCols = false,
  hideDocumentDisplay = false,
  docSidebarToggled = false,
  className,
  compact = false,
  defaultCollapsed = false,
}) => {
  const [isVisible, setIsVisible] = useState(!animateEntrance);
  const [isExpanded, setIsExpanded] = useState(!defaultCollapsed);
  
  useEffect(() => {
    if (animateEntrance) {
      const timer = setTimeout(() => setIsVisible(true), 100);
      return () => clearTimeout(timer);
    }
  }, [animateEntrance]);

  if (!documents || documents.length === 0) {
    return null;
  }

  const displayedDocuments = documents.slice(0, 5);
  const hasMoreDocuments = documents.length > 3;

  const containerClasses = cn(
    'w-full flex flex-col',
    compact ? 'py-1.5 px-4 rounded-lg border' : 'py-4 gap-4',
    compact && variant === 'glassmorphism'
      ? 'glass-light border-white/20'
      : compact && 'neuro-flat bg-gray-50 border-gray-200',
    !threeCols && !compact && 'max-w-[562px]',
    className
  );

  const gridClasses = cn(
    'grid w-full gap-4 px-4',
    threeCols ? 'grid-cols-3' : 'grid-cols-2'
  );

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={animateEntrance ? { opacity: 0, y: 20 } : undefined}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className={containerClasses}
        >
          {/* Header */}
          <div className={cn(
            'flex items-center justify-between',
            compact ? 'mb-1' : 'px-4'
          )}>
            <div className="flex-1">
              <div className={cn(
                'flex items-center space-x-2',
                compact ? 'text-sm font-medium' : 'text-lg font-medium',
                variant === 'glassmorphism' ? 'text-glass' : 'text-gray-900'
              )}>
                <Search className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
                <span>Sources</span>
                <span className={cn(
                  'px-2 py-0.5 rounded-full',
                  compact ? 'text-xs' : 'text-sm',
                  variant === 'glassmorphism' 
                    ? 'bg-white/20 text-white/70' 
                    : 'bg-gray-200 text-gray-600'
                )}>
                  {documents.length}
                </span>
              </div>
              {compact && (
                <div className={cn(
                  'text-xs opacity-70 mt-0.5',
                  variant === 'glassmorphism' ? 'text-glass' : 'text-gray-600'
                )}>
                  {documents.length} source{documents.length !== 1 ? 's' : ''} found
                </div>
              )}
            </div>
            
            {compact ? (
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
            ) : (
              hasMoreDocuments && (
                <button
                  onClick={toggleDocumentSelection}
                  className={cn(
                    'flex items-center space-x-2 text-sm transition-colors',
                    variant === 'glassmorphism'
                      ? 'text-white/70 hover:text-white'
                      : 'text-gray-600 hover:text-gray-800'
                  )}
                >
                  <Eye className="w-4 h-4" />
                  <span>{docSidebarToggled ? 'Hide All' : 'View All'}</span>
                  {docSidebarToggled ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              )
            )}
          </div>
          
          {/* Document grid - only show when expanded in compact mode */}
          <AnimatePresence>
            {(!compact || isExpanded) && (
              <motion.div
                initial={compact ? { height: 0, opacity: 0 } : undefined}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className={cn(
                  gridClasses,
                  compact && 'gap-2 mt-2'
                )}>
              {displayedDocuments.slice(0, compact ? 4 : displayedDocuments.length).map((doc, index) => (
                <motion.div
                  key={doc.document_id}
                  initial={animateEntrance && !compact ? { opacity: 0, y: 20 } : undefined}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ 
                    duration: 0.3, 
                    delay: animateEntrance && !compact ? index * 0.1 : 0 
                  }}
                  className="transition-opacity duration-300"
                >
                  <SourceCard
                    document={doc}
                    setPresentingDocument={setPresentingDocument}
                    variant={variant}
                    hideDocumentDisplay={hideDocumentDisplay}
                    compact={compact}
                    isExpanded={isExpanded}
                  />
                </motion.div>
              ))}
              
              {!compact && hasMoreDocuments && (
                <motion.div
                  initial={animateEntrance ? { opacity: 0, y: 20 } : undefined}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ 
                    duration: 0.3, 
                    delay: animateEntrance ? displayedDocuments.length * 0.1 : 0 
                  }}
                >
                  <SeeMoreBlock
                    fullWidth
                    toggled={docSidebarToggled}
                    toggleDocumentSelection={toggleDocumentSelection}
                    docs={documents}
                    variant={variant}
                  />
                </motion.div>
              )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
};