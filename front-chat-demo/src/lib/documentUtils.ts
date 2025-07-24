/**
 * Document utilities for unified document opening behavior
 * Based on onyx/web implementation patterns
 */

import { OnyxDocument } from '@/types';

/**
 * Extract a meaningful title from document content
 * Prioritizes: H1 headers > meaningful first lines > semantic_identifier
 */
const extractDocumentTitle = (document: OnyxDocument): string => {
  const { blurb, semantic_identifier } = document;
  
  if (!blurb) {
    return semantic_identifier;
  }
  
  // 1. Try to extract H1 header (# Title)
  const h1Match = blurb.match(/^#\s+(.+)$/m);
  if (h1Match) {
    return h1Match[1].trim();
  }
  
  // 2. Try to extract H2 header (## Title) if no H1
  const h2Match = blurb.match(/^##\s+(.+)$/m);
  if (h2Match) {
    return h2Match[1].trim();
  }
  
  // 3. Try to extract H3 header (### Title) if no H1/H2
  const h3Match = blurb.match(/^###\s+(.+)$/m);
  if (h3Match) {
    return h3Match[1].trim();
  }
  
  // 4. Try to extract meaningful first line (not URL, not separator)
  const lines = blurb.split('\n').map(line => line.trim());
  for (const line of lines) {
    if (line && 
        !line.startsWith('**Source URL:**') && 
        !line.startsWith('---') &&
        !line.startsWith('http') &&
        line.length > 3) {
      return line;
    }
  }
  
  // 5. Fallback to semantic_identifier
  return semantic_identifier;
};

/**
 * Extract source URL from document content
 * Handles cases where the actual URL is embedded in the document blurb/content
 */
const extractSourceUrl = (document: OnyxDocument): string | null => {
  // Check if blurb contains a Source URL pattern
  if (document.blurb) {
    console.log('🔍 Searching for source URL in blurb:', document.blurb.substring(0, 200) + '...');
    
    // Pattern: **Source URL:** https://... (most common)
    // Handle URLs with fragments (#section) and other URL characters
    const sourceUrlMatch = document.blurb.match(/\*\*Source URL:\*\*\s+(https?:\/\/[^\s\n\r]+)/);
    if (sourceUrlMatch) {
      console.log('📎 Found source URL (pattern 1 - **Source URL:**):', sourceUrlMatch[1]);
      return sourceUrlMatch[1];
    }
    
    // Pattern: Source URL: https://... (without markdown bold)
    const sourceUrlMatch2 = document.blurb.match(/Source URL:\s+(https?:\/\/[^\s\n\r]+)/);
    if (sourceUrlMatch2) {
      console.log('📎 Found source URL (pattern 2 - Source URL:):', sourceUrlMatch2[1]);
      return sourceUrlMatch2[1];
    }
    
    // Pattern: any URL at the beginning of content (after title/headers)
    const lines = document.blurb.split('\n');
    for (let i = 0; i < Math.min(5, lines.length); i++) {
      const urlMatch = lines[i].match(/(https?:\/\/[^\s\n\r]+)/);
      if (urlMatch) {
        console.log('📎 Found URL (pattern 3 - early line):', urlMatch[1]);
        return urlMatch[1];
      }
    }
    
    // Pattern: any URL in the entire content (fallback)
    const urlMatch = document.blurb.match(/(https?:\/\/[^\s\n\r]+)/);
    if (urlMatch) {
      console.log('📎 Found URL (pattern 4 - anywhere):', urlMatch[1]);
      return urlMatch[1];
    }
    
    console.log('❌ No URL found in document blurb');
  } else {
    console.log('❌ No blurb available for URL extraction');
  }
  
  return null;
};

/**
 * Unified document opening function
 * Handles both external links and local file presentation
 */
export const openDocument = (
  document: OnyxDocument,
  updatePresentingDocument?: (document: OnyxDocument) => void
) => {
  console.log('🔗 openDocument called:', {
    semantic_identifier: document.semantic_identifier,
    link: document.link,
    source_type: document.source_type,
    document_id: document.document_id,
    blurb_preview: document.blurb ? document.blurb.substring(0, 100) + '...' : 'No blurb available'
  });

  // Priority 1: Open external link if available
  if (document.link && document.link.trim()) {
    console.log('🌐 Opening external link:', document.link);
    window.open(document.link, "_blank");
    return;
  }

  // Priority 2: Extract source URL from content
  const extractedUrl = extractSourceUrl(document);
  if (extractedUrl) {
    console.log('🔍 Found extracted source URL:', extractedUrl);
    window.open(extractedUrl, "_blank");
    return;
  }

  // Priority 3: For local files, show in current interface
  if (document.source_type === "file" || document.source_type === "File") {
    console.log('📁 Presenting local file document');
    updatePresentingDocument?.(document);
    return;
  }

  // Priority 4: For documents without links, still present them locally
  // This covers cases where external documents don't have accessible URLs
  console.log('📄 Presenting document without external link');
  updatePresentingDocument?.(document);
  
  // Optional: Show a toast or notification that the document is being presented locally
  // since there's no external link available
};

/**
 * Check if a document can be opened externally
 */
export const canOpenExternally = (document: OnyxDocument): boolean => {
  // Check direct link
  if (document.link && document.link.trim().length > 0) {
    return true;
  }
  
  // Check for embedded source URL
  const extractedUrl = extractSourceUrl(document);
  return Boolean(extractedUrl);
};

/**
 * Check if a document should be presented locally
 */
export const shouldPresentLocally = (document: OnyxDocument): boolean => {
  return document.source_type === "file" || 
         document.source_type === "File" || 
         !canOpenExternally(document);
};

/**
 * Get display information for a document link
 */
export const getDocumentDisplayInfo = (document: OnyxDocument) => {
  const hasExternalLink = canOpenExternally(document);
  const isLocalFile = document.source_type === "file" || document.source_type === "File";
  const extractedUrl = extractSourceUrl(document);
  const displayTitle = extractDocumentTitle(document);
  
  // Determine the effective URL for display
  const effectiveUrl = document.link || extractedUrl;
  
  return {
    hasExternalLink,
    isLocalFile,
    shouldShowExternalIcon: hasExternalLink,
    tooltip: hasExternalLink 
      ? `Open ${displayTitle} in new tab${effectiveUrl ? ` (${effectiveUrl})` : ''}`
      : `View ${displayTitle} content`,
    actionText: hasExternalLink ? "Open Link" : "View Content",
    effectiveUrl,
    displayTitle
  };
};

/**
 * Get a meaningful title for document display
 */
export const getDocumentTitle = (document: OnyxDocument): string => {
  return extractDocumentTitle(document);
};