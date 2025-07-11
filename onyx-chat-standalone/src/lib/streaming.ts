import { 
  PacketType, 
  AnswerPiecePacket, 
  DocumentInfoPacket, 
  SubQueryPiece, 
  ThinkingTokens, 
  StreamingError, 
  ToolCallMetadata, 
  BackendMessage,
  ChatMessageDetailPacket,
  SearchProgress,
  ChatMessage,
} from '@/types';

export class StreamingProcessor {
  private currentAnswer = '';
  private currentThinking = '';
  private subQueries: SubQueryPiece[] = [];
  private documents: DocumentInfoPacket[] = [];
  private isComplete = false;
  private error: string | null = null;
  private messageId: string;
  private messageDetail: ChatMessageDetailPacket | null = null;

  constructor(messageId: string) {
    this.messageId = messageId;
  }

  processPacket(data: string): PacketType | null {
    console.log('🔧 Processing packet data:', data);
    try {
      const packet = JSON.parse(data);
      console.log('📋 Parsed packet:', packet);
      
      // Determine packet type and process accordingly
      if (packet.answer_piece !== undefined) {
        console.log('📝 Processing answer piece:', packet.answer_piece);
        return this.processAnswerPiece(packet as AnswerPiecePacket);
      }
      
      if (packet.document_id !== undefined) {
        console.log('📄 Processing document info');
        return this.processDocumentInfo(packet as DocumentInfoPacket);
      }
      
      if (packet.sub_query !== undefined) {
        console.log('🔍 Processing sub query');
        return this.processSubQuery(packet as SubQueryPiece);
      }
      
      if (packet.thinking_content !== undefined) {
        console.log('🤔 Processing thinking tokens');
        return this.processThinkingTokens(packet as ThinkingTokens);
      }
      
      if (packet.error !== undefined) {
        console.log('❌ Processing error');
        return this.processError(packet as StreamingError);
      }
      
      if (packet.tool_name !== undefined) {
        console.log('🔧 Processing tool call');
        return this.processToolCall(packet as ToolCallMetadata);
      }
      
      if (packet.message_type !== undefined) {
        console.log('💌 Processing backend message');
        return this.processBackendMessage(packet as BackendMessage);
      }
      
      // Handle ChatMessageDetail packets (contains real message ID)
      if (packet.message_id !== undefined && packet.message_type !== undefined && packet.time_sent !== undefined) {
        console.log('🆔 Processing chat message detail');
        return this.processChatMessageDetail(packet as ChatMessageDetailPacket);
      }
      
      // Handle completion signals
      if (packet.type === 'complete' || packet.complete === true) {
        console.log('✅ Processing completion signal');
        this.isComplete = true;
        return packet;
      }
      
      console.log('⚠️ Unknown packet type:', packet);
      return packet;
    } catch (error) {
      console.error('❌ Error parsing streaming packet:', error, 'Raw data:', data);
      return null;
    }
  }

  private processAnswerPiece(packet: AnswerPiecePacket): AnswerPiecePacket {
    console.log('📝 Adding answer piece to current answer:', packet.answer_piece);
    console.log('📝 Current answer before update:', this.currentAnswer);
    
    // Handle null answer pieces (end of stream indicator)
    if (packet.answer_piece === null || packet.answer_piece === undefined) {
      console.log('🏁 Received null answer piece - marking as complete');
      this.isComplete = true;
      return packet;
    }
    
    this.currentAnswer += packet.answer_piece;
    console.log('📝 Current answer after update:', this.currentAnswer);
    return packet;
  }

  private processDocumentInfo(packet: DocumentInfoPacket): DocumentInfoPacket {
    // Avoid duplicates
    const exists = this.documents.some(doc => doc.document_id === packet.document_id);
    if (!exists) {
      this.documents.push(packet);
    }
    return packet;
  }

  private processSubQuery(packet: SubQueryPiece): SubQueryPiece {
    const existingIndex = this.subQueries.findIndex(sq => sq.sub_query === packet.sub_query);
    if (existingIndex >= 0) {
      // Update existing sub-query
      this.subQueries[existingIndex] = { ...this.subQueries[existingIndex], ...packet };
    } else {
      // Add new sub-query
      this.subQueries.push(packet);
    }
    return packet;
  }

  private processThinkingTokens(packet: ThinkingTokens): ThinkingTokens {
    this.currentThinking += packet.thinking_content;
    return packet;
  }

  private processError(packet: StreamingError): StreamingError {
    this.error = packet.error;
    this.isComplete = true;
    return packet;
  }

  private processToolCall(packet: ToolCallMetadata): ToolCallMetadata {
    // Handle tool calls if needed
    return packet;
  }

  private processBackendMessage(packet: BackendMessage): BackendMessage {
    // Handle backend messages if needed
    return packet;
  }

  private processChatMessageDetail(packet: ChatMessageDetailPacket): ChatMessageDetailPacket {
    this.messageDetail = packet;
    this.isComplete = true; // Message detail usually comes at the end
    return packet;
  }

  getCurrentAnswer(): string {
    return this.currentAnswer;
  }

  getCurrentThinking(): string {
    return this.currentThinking;
  }

  getSubQueries(): SubQueryPiece[] {
    return this.subQueries;
  }

  getDocuments(): DocumentInfoPacket[] {
    return this.documents;
  }

  getSearchProgress(): SearchProgress {
    // Determine current phase based on the state
    let phase: SearchProgress['phase'] = 'waiting';
    
    if (this.subQueries.length > 0) {
      const allDone = this.subQueries.every(sq => sq.status === 'done');
      const anyInProgress = this.subQueries.some(sq => sq.status === 'in_progress');
      
      if (anyInProgress) {
        phase = 'sub_queries';
      } else if (allDone && this.documents.length > 0) {
        phase = 'context_docs';
      } else if (allDone && this.currentAnswer) {
        phase = 'answer';
      }
    }
    
    if (this.isComplete) {
      phase = 'complete';
    }

    return {
      phase,
      subQueries: this.subQueries,
      documents: this.documents,
      thinkingContent: this.currentThinking,
      currentAnswer: this.currentAnswer,
    };
  }

  isStreamComplete(): boolean {
    return this.isComplete;
  }

  getError(): string | null {
    return this.error;
  }

  getMessageDetail(): ChatMessageDetailPacket | null {
    return this.messageDetail;
  }

  reset(): void {
    this.currentAnswer = '';
    this.currentThinking = '';
    this.subQueries = [];
    this.documents = [];
    this.isComplete = false;
    this.error = null;
    this.messageDetail = null;
  }

  // Generate a complete ChatMessage from the current state
  generateChatMessage(): ChatMessage {
    return {
      id: this.messageId,
      type: 'assistant',
      content: this.currentAnswer,
      timestamp: new Date(),
      isStreaming: !this.isComplete,
      documents: this.documents,
      subQueries: this.subQueries,
      thinkingContent: this.currentThinking,
      error: this.error || undefined,
      citations: this.generateCitations(),
    };
  }

  private generateCitations() {
    return this.documents.map(doc => ({
      documentId: doc.document_id,
      documentName: doc.document_name,
      link: doc.link,
      text: doc.blurb,
      sourceType: doc.source_type,
    }));
  }
}

// Thinking token detection utilities
export class ThinkingTokenProcessor {
  private static readonly THINKING_PATTERNS = [
    /<think>([\s\S]*?)<\/think>/g,
    /<thinking>([\s\S]*?)<\/thinking>/g,
  ];

  static extractThinkingContent(text: string): string[] {
    const results: string[] = [];
    
    for (const pattern of this.THINKING_PATTERNS) {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        if (match[1]) {
          results.push(match[1].trim());
        }
      }
      // Reset regex state for global patterns
      pattern.lastIndex = 0;
    }
    
    return results;
  }

  static removeThinkingTags(text: string): string {
    let cleanText = text;
    
    for (const pattern of this.THINKING_PATTERNS) {
      cleanText = cleanText.replace(pattern, '');
    }
    
    return cleanText.trim();
  }

  static hasPartialThinkingTokens(text: string): boolean {
    return text.includes('<think') || text.includes('<thinking');
  }

  static isThinkingComplete(text: string): boolean {
    const openTags = (text.match(/<think(?:ing)?>/g) || []).length;
    const closeTags = (text.match(/<\/think(?:ing)?>/g) || []).length;
    return openTags === closeTags && openTags > 0;
  }
}

// Enhanced streaming for smooth typing effect with smart text chunking
export class TypingEffectProcessor {
  private targetText = '';
  private currentIndex = 0;
  private isActive = false;
  private intervalId: NodeJS.Timeout | null = null;
  private onUpdate: (text: string) => void;
  private onComplete: () => void;
  private speed: number;
  private chunks: string[] = [];
  private chunkIndex = 0;

  constructor(
    onUpdate: (text: string) => void,
    onComplete: () => void = () => {},
    speed: number = 10 // milliseconds per chunk (faster than per character)
  ) {
    this.onUpdate = onUpdate;
    this.onComplete = onComplete;
    this.speed = speed;
  }

  updateTarget(newText: string): void {
    console.log('⌨️ TypingEffect: updateTarget called with text:', newText);
    this.targetText = newText;
    
    // Smart chunk the text to avoid breaking words or sentences
    this.chunks = this.smartChunkText(newText);
    
    if (!this.isActive && this.chunkIndex < this.chunks.length) {
      console.log('⌨️ TypingEffect: Starting typing animation');
      this.start();
    }
  }

  private smartChunkText(text: string): string[] {
    if (!text) return [];
    
    const chunks: string[] = [];
    let currentChunk = '';
    let i = 0;
    
    while (i < text.length) {
      const char = text[i];
      currentChunk += char;
      
      // Define break points for natural text flow
      const isBreakPoint = this.isNaturalBreakPoint(char, text, i);
      const shouldBreakForLength = currentChunk.length >= 5; // 3-8 characters per chunk
      
      // Break at natural points or when chunk is long enough
      if ((isBreakPoint && currentChunk.length >= 2) || shouldBreakForLength) {
        chunks.push(currentChunk);
        currentChunk = '';
      }
      
      i++;
    }
    
    // Add remaining chunk if any
    if (currentChunk) {
      chunks.push(currentChunk);
    }
    
    return chunks;
  }

  private isNaturalBreakPoint(char: string, text: string, index: number): boolean {
    // Natural break points to avoid breaking words or sentences awkwardly
    const naturalBreaks = [' ', '\n', '\t', '.', '!', '?', ',', ';', ':', '-', '—'];
    
    // Break after punctuation
    if (naturalBreaks.includes(char)) {
      return true;
    }
    
    // Break before opening brackets/quotes
    const openingChars = ['(', '[', '{', '"', "'", '`'];
    if (openingChars.includes(char)) {
      return true;
    }
    
    // Break after closing brackets/quotes
    const closingChars = [')', ']', '}', '"', "'", '`'];
    if (index > 0 && closingChars.includes(text[index - 1])) {
      return true;
    }
    
    return false;
  }

  private start(): void {
    if (this.isActive) {
      console.log('⌨️ TypingEffect: Already active, skipping start');
      return;
    }
    
    console.log('⌨️ TypingEffect: Starting animation with', this.chunks.length, 'chunks');
    this.isActive = true;
    this.intervalId = setInterval(() => {
      if (this.chunkIndex < this.chunks.length) {
        // Add next chunk(s) - sometimes add multiple chunks for variety
        const chunksToAdd = Math.min(
          Math.ceil(Math.random() * 2), // 1-2 chunks at a time
          this.chunks.length - this.chunkIndex
        );
        
        this.chunkIndex = Math.min(this.chunkIndex + chunksToAdd, this.chunks.length);
        
        // Reconstruct text from chunks
        const currentText = this.chunks.slice(0, this.chunkIndex).join('');
        console.log('⌨️ TypingEffect: Updating with text:', currentText);
        this.onUpdate(currentText);
      } else {
        console.log('⌨️ TypingEffect: Animation complete');
        this.stop();
        this.onComplete();
      }
    }, this.speed);
  }

  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isActive = false;
  }

  complete(): void {
    this.stop();
    this.chunkIndex = this.chunks.length;
    this.onUpdate(this.targetText);
    this.onComplete();
  }

  reset(): void {
    this.stop();
    this.targetText = '';
    this.currentIndex = 0;
    this.chunks = [];
    this.chunkIndex = 0;
  }

  isCompleted(): boolean {
    return this.chunkIndex >= this.chunks.length;
  }

  getCurrentText(): string {
    return this.chunks.slice(0, this.chunkIndex).join('');
  }
}

// Enhanced phase management for Agent-style search with better timing control
export enum StreamingPhase {
  WAITING = 'waiting',
  SUB_QUERIES = 'sub_queries',
  CONTEXT_DOCS = 'context_docs',
  ANSWER = 'answer',
  EVALUATE = 'evaluate',
  COMPLETE = 'complete',
}

export const StreamingPhaseText: Record<StreamingPhase, string> = {
  [StreamingPhase.WAITING]: 'Preparing search...',
  [StreamingPhase.SUB_QUERIES]: 'Generating search queries...',
  [StreamingPhase.CONTEXT_DOCS]: 'Finding relevant documents...',
  [StreamingPhase.ANSWER]: 'Analyzing and answering...',
  [StreamingPhase.EVALUATE]: 'Evaluating results...',
  [StreamingPhase.COMPLETE]: 'Complete',
};

export const PHASES_ORDER: StreamingPhase[] = [
  StreamingPhase.WAITING,
  StreamingPhase.SUB_QUERIES,
  StreamingPhase.CONTEXT_DOCS,
  StreamingPhase.ANSWER,
  StreamingPhase.EVALUATE,
  StreamingPhase.COMPLETE,
];

export class StreamingPhaseManager {
  private currentPhase: StreamingPhase = StreamingPhase.WAITING;
  private phaseStartTime = 0;
  private readonly PHASE_MIN_MS = 800; // Minimum phase duration in ms
  private pendingTransitions: Map<StreamingPhase, NodeJS.Timeout> = new Map();
  private onPhaseChange: (phase: StreamingPhase) => void;

  constructor(onPhaseChange: (phase: StreamingPhase) => void) {
    this.onPhaseChange = onPhaseChange;
    this.phaseStartTime = Date.now();
  }

  canTransitionTo(newPhase: StreamingPhase): boolean {
    if (newPhase === this.currentPhase) return false;
    
    const elapsed = Date.now() - this.phaseStartTime;
    const canTransition = elapsed >= this.PHASE_MIN_MS;
    
    console.log(`🎭 Phase Manager: Can transition from ${this.currentPhase} to ${newPhase}? ${canTransition} (elapsed: ${elapsed}ms)`);
    return canTransition;
  }

  transitionTo(newPhase: StreamingPhase): void {
    if (newPhase === this.currentPhase) return;

    // Cancel any pending transition for this phase
    const pendingTimeout = this.pendingTransitions.get(newPhase);
    if (pendingTimeout) {
      clearTimeout(pendingTimeout);
      this.pendingTransitions.delete(newPhase);
    }

    if (this.canTransitionTo(newPhase)) {
      console.log(`🎭 Phase Manager: Immediate transition from ${this.currentPhase} to ${newPhase}`);
      this.executeTransition(newPhase);
    } else {
      // Schedule transition after minimum duration
      const elapsed = Date.now() - this.phaseStartTime;
      const delay = this.PHASE_MIN_MS - elapsed;
      
      console.log(`🎭 Phase Manager: Scheduled transition from ${this.currentPhase} to ${newPhase} in ${delay}ms`);
      
      const timeoutId = setTimeout(() => {
        this.executeTransition(newPhase);
        this.pendingTransitions.delete(newPhase);
      }, delay);
      
      this.pendingTransitions.set(newPhase, timeoutId);
    }
  }

  private executeTransition(phase: StreamingPhase): void {
    console.log(`🎭 Phase Manager: Executing transition to ${phase}`);
    this.currentPhase = phase;
    this.phaseStartTime = Date.now();
    this.onPhaseChange(phase);
  }

  getCurrentPhase(): StreamingPhase {
    return this.currentPhase;
  }

  getElapsedTime(): number {
    return Date.now() - this.phaseStartTime;
  }

  reset(): void {
    console.log('🎭 Phase Manager: Resetting to WAITING phase');
    
    // Cancel all pending transitions
    this.pendingTransitions.forEach(timeout => clearTimeout(timeout));
    this.pendingTransitions.clear();
    
    this.currentPhase = StreamingPhase.WAITING;
    this.phaseStartTime = Date.now();
  }

  // Detect phase from packet content
  detectPhaseFromPacket(packet: any): StreamingPhase {
    if (!packet) return this.currentPhase;

    // Sub query generation phase
    if (packet.sub_query !== undefined) {
      return StreamingPhase.SUB_QUERIES;
    }

    // Document retrieval phase
    if (packet.document_id !== undefined) {
      return StreamingPhase.CONTEXT_DOCS;
    }

    // Answer generation phase
    if (packet.answer_piece !== undefined) {
      return StreamingPhase.ANSWER;
    }

    // Completion signals
    if (packet.type === 'complete' || packet.complete === true) {
      return StreamingPhase.COMPLETE;
    }

    // Error state should stay in current phase
    if (packet.error !== undefined) {
      return this.currentPhase;
    }

    return this.currentPhase;
  }

  // Force transition without timing constraints (for completion or error states)
  forceTransition(phase: StreamingPhase): void {
    console.log(`🎭 Phase Manager: Force transition to ${phase}`);
    
    // Cancel any pending transitions
    this.pendingTransitions.forEach(timeout => clearTimeout(timeout));
    this.pendingTransitions.clear();
    
    this.executeTransition(phase);
  }

  destroy(): void {
    // Cleanup method for when the component unmounts
    this.pendingTransitions.forEach(timeout => clearTimeout(timeout));
    this.pendingTransitions.clear();
  }
}

// Legacy PhaseController for backward compatibility
export class PhaseController {
  private phaseManager: StreamingPhaseManager;

  constructor(onPhaseChange: (phase: SearchProgress['phase']) => void) {
    // Convert new StreamingPhase to old phase format
    this.phaseManager = new StreamingPhaseManager((newPhase) => {
      onPhaseChange(newPhase as SearchProgress['phase']);
    });
  }

  setPhase(newPhase: SearchProgress['phase']): void {
    this.phaseManager.transitionTo(newPhase as StreamingPhase);
  }

  getCurrentPhase(): SearchProgress['phase'] {
    return this.phaseManager.getCurrentPhase() as SearchProgress['phase'];
  }

  reset(): void {
    this.phaseManager.reset();
  }
}

// Utility functions for streaming
export function createMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function createSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function formatTimestamp(date: Date): string {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours();
  const minutes = date.getMinutes();
  
  const formattedHours = hours.toString().padStart(2, '0');
  const formattedMinutes = minutes.toString().padStart(2, '0');
  
  return `${month}/${day} ${formattedHours}:${formattedMinutes}`;
}

export function estimateReadingTime(text: string): number {
  const wordsPerMinute = 200;
  const words = text.split(/\s+/).length;
  return Math.ceil(words / wordsPerMinute);
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

export function highlightSearchTerms(text: string, terms: string[]): string {
  let highlighted = text;
  
  terms.forEach(term => {
    const regex = new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
    highlighted = highlighted.replace(regex, `<mark>$&</mark>`);
  });
  
  return highlighted;
}

// Error handling utilities
export function isStreamingError(error: any): error is StreamingError {
  return error && typeof error.error === 'string' && typeof error.error_type === 'string';
}

export function isNetworkError(error: any): boolean {
  return error instanceof TypeError && error.message.includes('fetch');
}

export function isAbortError(error: any): boolean {
  return error.name === 'AbortError';
}

export function getErrorMessage(error: any): string {
  if (isStreamingError(error)) {
    return error.error;
  }
  
  if (isNetworkError(error)) {
    return 'Network connection error. Please check your internet connection.';
  }
  
  if (isAbortError(error)) {
    return 'Request was cancelled.';
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unknown error occurred.';
}