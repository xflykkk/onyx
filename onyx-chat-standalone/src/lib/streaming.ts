import { 
  PacketType, 
  AnswerPiecePacket, 
  DocumentInfoPacket, 
  SubQueryPiece, 
  SubQuestionDetail,
  ThinkingTokens, 
  StreamingError, 
  ToolCallMetadata, 
  BackendMessage,
  ChatMessageDetailPacket,
  SearchProgress,
  ChatMessage,
  StreamingDetail,
  SubQuestionPiece,
  AgentAnswerPiece,
  SubQuestionSearchDoc,
  StreamStopInfo,
} from '@/types';
import { constructSubQuestions } from './subQuestions';

export class StreamingProcessor {
  private currentAnswer = '';
  private currentThinking = '';
  private subQueries: SubQueryPiece[] = [];
  private subQuestions: SubQuestionDetail[] = []; // 新增：正确的 subQuestions 数组
  private documents: DocumentInfoPacket[] = [];
  private isComplete = false;
  private error: string | null = null;
  private messageId: string;
  private messageDetail: ChatMessageDetailPacket | null = null;
  private hasFinalSubQuestions = false; // 标记是否已收到最终子问题

  constructor(messageId: string) {
    this.messageId = messageId;
  }

  processPacket(data: string): PacketType | null {
    console.log('🔧 Processing packet data:', data);
    try {
      const packet = JSON.parse(data);
      console.log('📋 Parsed packet:', packet);
      
      // Debug: Log all packet keys to understand structure
      console.log('🔍 Packet keys:', Object.keys(packet));
      console.log('📄 Has top_documents:', Object.hasOwnProperty.call(packet, "top_documents"));
      console.log('📄 Has context_docs:', Object.hasOwnProperty.call(packet, "context_docs"));
      console.log('📄 Has documents:', Object.hasOwnProperty.call(packet, "documents"));
      
      // Determine packet type and process accordingly
      if (packet.answer_piece !== undefined) {
        console.log('📝 Processing answer piece:', packet.answer_piece);
        
        // 检查是否是子问题的答案片段
        if (packet.answer_type === "agent_sub_answer" && packet.level !== undefined && packet.level_question_num !== undefined) {
          console.log('📝 Processing SubQuestion answer piece');
          return this.processAgentAnswerPiece(packet);
        }
        
        return this.processAnswerPiece(packet as AnswerPiecePacket);
      }
      
      if (packet.document_id !== undefined) {
        console.log('📄 Processing document info');
        return this.processDocumentInfo(packet as DocumentInfoPacket);
      }
      
      // Handle SubQuestionPiece - 子问题片段
      if (Object.hasOwnProperty.call(packet, "sub_question")) {
        console.log('❓ Processing SubQuestionPiece:', packet.sub_question);
        return this.processSubQuestionPiece(packet);
      }
      
      // Handle SubQueryPiece - 子查询片段  
      if (Object.hasOwnProperty.call(packet, "sub_query")) {
        console.log('🔍 Processing SubQueryPiece:', packet.sub_query);
        return this.processSubQueryPiece(packet);
      }
      
      if (packet.thinking_content !== undefined) {
        console.log('🤔 Processing thinking tokens');
        return this.processThinkingTokens(packet as ThinkingTokens);
      }
      
      if (packet.error !== undefined && packet.error !== null) {
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
      
      // Handle document packets following onyx/web pattern
      if (Object.hasOwnProperty.call(packet, "top_documents")) {
        console.log('📄 Processing document packet (onyx/web style)');
        console.log('📋 Document packet keys:', Object.keys(packet));
        
        // Extract documents directly like onyx/web
        if (Array.isArray(packet.top_documents)) {
          packet.top_documents.forEach((doc: any) => {
            const documentPacket: DocumentInfoPacket = {
              document_id: doc.document_id,
              document_name: doc.semantic_identifier,
              link: doc.link || '',
              source_type: doc.source_type,
              semantic_identifier: doc.semantic_identifier,
              blurb: doc.blurb,
              boost: doc.boost,
              score: doc.score,
              chunk_ind: doc.chunk_ind,
              match_highlights: doc.match_highlights || [],
              metadata: doc.metadata || {},
              updated_at: doc.updated_at,
              is_internet: doc.is_internet || false,
            };
            
            const exists = this.documents.some(existingDoc => existingDoc.document_id === doc.document_id);
            if (!exists) {
              this.documents.push(documentPacket);
              console.log('📄 Added document (onyx/web style):', documentPacket.semantic_identifier);
            }
          });
        }
        return packet;
      }

      // Handle ChatMessageDetail packets (contains real message ID and context docs)
      // More specific check: must have message_id AND be assistant type AND have complete message structure
      if (packet.message_id !== undefined && 
          packet.message_type === 'assistant' && 
          packet.time_sent !== undefined &&
          packet.message !== undefined) {
        console.log('🆔 Processing chat message detail packet');
        console.log('📋 ChatMessageDetail packet keys:', Object.keys(packet));
        console.log('📄 Has context_docs:', !!packet.context_docs);
        console.log('🔍 Has sub_questions:', !!packet.sub_questions);
        console.log('📋 ChatMessageDetail full packet (truncated):', {
          message_id: packet.message_id,
          message_type: packet.message_type,
          time_sent: packet.time_sent,
          context_docs_keys: packet.context_docs ? Object.keys(packet.context_docs) : null,
          context_docs_top_docs_count: packet.context_docs?.top_documents?.length || 0,
          sub_questions_count: packet.sub_questions?.length || 0,
          message_length: packet.message?.length || 0
        });
        
        this.extractDocumentsFromContext(packet);
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

  // 处理子问题片段 - 使用 constructSubQuestions 构建
  private processSubQuestionPiece(packet: any): any {
    const { sub_question, level = 1, level_question_num = 1, stop_reason, stream_type } = packet;
    
    console.log(`❓ Processing SubQuestionPiece: level=${level}, num=${level_question_num}, question="${sub_question}", stop_reason="${stop_reason}"`);
    
    // 构建 StreamingDetail 对象
    let streamingDetail: StreamingDetail;
    
    if (stop_reason === 'FINISHED' && stream_type === 'sub_questions') {
      // 停止信号
      streamingDetail = {
        stop_reason,
        stream_type,
        level,
        level_question_num,
      } as StreamStopInfo;
    } else {
      // 子问题片段
      streamingDetail = {
        sub_question,
        level,
        level_question_num,
      } as SubQuestionPiece;
    }
    
    // 使用统一的构建函数
    this.subQuestions = constructSubQuestions(this.subQuestions, streamingDetail);
    
    return packet;
  }
  
  // 清理子问题文本中的 HTML 标签
  private cleanSubQuestionText(text: string): string {
    if (!text) return '';
    // 移除 <sub-question> 和 </sub-question> 标签
    let cleaned = text.replace(/<\/?sub-question>/g, '');
    // 移除任何其他可能出现的 HTML 标签
    cleaned = cleaned.replace(/<[^>]*>/g, '');
    // 移除多余的空格并去除首尾空格
    cleaned = cleaned.replace(/\s+/g, ' ').trim();
    return cleaned;
  }
  
  // 处理子查询片段 - 使用 constructSubQuestions 构建
  private processSubQueryPiece(packet: any): any {
    const { sub_query, level = 1, level_question_num = 1, query_id = 0, stop_reason, stream_type } = packet;
    
    console.log(`🔍 Processing SubQueryPiece: level=${level}, num=${level_question_num}, query="${sub_query}", stop_reason="${stop_reason}"`);
    
    // 构建 StreamingDetail 对象
    let streamingDetail: StreamingDetail;
    
    if (stop_reason === 'FINISHED' && stream_type === 'sub_queries') {
      // 停止信号
      streamingDetail = {
        stop_reason,
        stream_type,
        level,
        level_question_num,
      } as StreamStopInfo;
    } else {
      // 子查询片段
      streamingDetail = {
        sub_query,
        level,
        level_question_num,
        query_id,
      } as SubQueryPiece;
    }
    
    // 使用统一的构建函数
    this.subQuestions = constructSubQuestions(this.subQuestions, streamingDetail);
    
    // 向后兼容：也更新旧的 subQueries 数组
    if (!stop_reason) {
      const existingIndex = this.subQueries.findIndex(sq => 
        sq.level === level && 
        sq.level_question_num === level_question_num &&
        sq.query_id === query_id
      );
      
      if (existingIndex >= 0) {
        this.subQueries[existingIndex] = { ...this.subQueries[existingIndex], ...packet };
      } else {
        this.subQueries.push(packet);
      }
    }
    
    return packet;
  }
  
  // 清理子查询文本中的标签
  private cleanSubQueryText(text: string): string {
    // 移除 <query 1>, <query 2>, </query 1>, </query 2> 等标签
    let cleaned = text.replace(/<\/?query\s*\d*>/g, '');
    // 移除多余的空格
    cleaned = cleaned.trim();
    return cleaned;
  }

  // 处理子问题答案片段 - 使用 constructSubQuestions 构建
  private processAgentAnswerPiece(packet: any): any {
    const { answer_piece, level, level_question_num, answer_type } = packet;
    
    console.log(`📝 Processing AgentAnswerPiece: level=${level}, num=${level_question_num}, piece="${answer_piece?.substring(0, 50)}..."`);
    
    // 构建 StreamingDetail 对象
    const streamingDetail: AgentAnswerPiece = {
      answer_piece,
      level,
      level_question_num,
      answer_type,
    };
    
    // 使用统一的构建函数
    this.subQuestions = constructSubQuestions(this.subQuestions, streamingDetail);
    
    return packet;
  }

  private processSubQuery(packet: SubQueryPiece): SubQueryPiece {
    // 这个方法保留用于向后兼容，但现在优先使用 processSubQueryPiece
    console.log('🔍 Processing legacy SubQuery:', packet.sub_query);
    return this.processSubQueryPiece(packet);
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

  private extractDocumentsFromContext(packet: any): void {
    // Always prioritize final sub_questions over streaming sub_questions
    // This ensures we use the complete, final questions rather than streaming fragments
    if (packet.sub_questions && packet.sub_questions.length > 0) {
      // Clear existing streaming sub-questions and use final complete ones
      this.subQuestions = [];
      this.hasFinalSubQuestions = true; // Mark that we've received final sub_questions
      console.log('🎯 Found final sub_questions array, clearing all existing subQuestions');
      console.log('📊 Final sub_questions count:', packet.sub_questions.length);
    } else {
      console.log('🧹 No sub_questions in current packet, keeping existing subQuestions');
    }
    
    console.log('🔍 extractDocumentsFromContext called with packet:', {
      hasContextDocs: !!packet.context_docs,
      hasTopDocs: !!packet.context_docs?.top_documents,
      topDocsLength: packet.context_docs?.top_documents?.length || 0,
      hasSubQuestions: !!packet.sub_questions,
      subQuestionsLength: packet.sub_questions?.length || 0,
      // 检查其他可能的字段名
      hasSubQueries: !!packet.sub_queries,
      hasQuestions: !!packet.questions,
      hasAnswers: !!packet.answers,
      currentDocsCount: this.documents.length,
      packetKeys: Object.keys(packet),
      // 打印完整数据包结构
      packetStructure: JSON.stringify(packet, null, 2)
    });
    
    // Extract documents from context_docs.top_documents
    if (packet.context_docs?.top_documents) {
      console.log('📄 Extracting documents from context_docs:', packet.context_docs.top_documents.length);
      
      packet.context_docs.top_documents.forEach((doc: any, idx: number) => {
        console.log(`📋 Processing document ${idx + 1}:`, {
          document_id: doc.document_id,
          semantic_identifier: doc.semantic_identifier,
          link: doc.link,
          source_type: doc.source_type,
          hasBlurb: !!doc.blurb,
          score: doc.score
        });
        // Convert to DocumentInfoPacket format
        const documentPacket: DocumentInfoPacket = {
          document_id: doc.document_id,
          document_name: doc.semantic_identifier,
          link: doc.link || '',
          source_type: doc.source_type,
          semantic_identifier: doc.semantic_identifier,
          blurb: doc.blurb,
          boost: doc.boost,
          score: doc.score,
          chunk_ind: doc.chunk_ind,
          match_highlights: doc.match_highlights || [],
          metadata: doc.metadata || {},
          updated_at: doc.updated_at,
          is_internet: doc.is_internet || false,
        };
        
        // Add to documents array (avoid duplicates)
        const exists = this.documents.some(existingDoc => existingDoc.document_id === doc.document_id);
        if (!exists) {
          this.documents.push(documentPacket);
          console.log('📄 Added document:', documentPacket.semantic_identifier);
        }
      });
    }

    // Convert backend sub_questions to frontend subQueries format
    if (packet.sub_questions && packet.sub_questions.length > 0) {
      console.log('🎯 Processing FINAL sub_questions from packet (AUTHORITATIVE):', packet.sub_questions.length);
      console.log('📊 Current temporary subQuestions count before replacement:', this.subQuestions.length);
      
      packet.sub_questions.forEach((subQ: any, idx: number) => {
        console.log(`📋 Processing final sub_question ${idx + 1}:`, {
          question: subQ.question,
          answer: subQ.answer?.substring(0, 100) + '...',
          level: subQ.level,
          level_question_num: subQ.level_question_num,
          hasContextDocs: !!subQ.context_docs?.top_documents,
          contextDocsCount: subQ.context_docs?.top_documents?.length || 0
        });
        
        // Clean the question text from the final sub_questions
        const cleanedQuestion = this.cleanSubQuestionText(subQ.question || '');
        
        // Convert sub_questions to SubQuestionDetail format for frontend compatibility
        const subQuestionDetail = {
          level: subQ.level || 0,
          level_question_num: subQ.level_question_num || 1,
          question: cleanedQuestion,
          answer: subQ.answer || '',
          sub_queries: subQ.sub_queries || null,
          context_docs: subQ.context_docs || null,
          is_complete: true
        };
        
        // Always add final sub_questions (they are authoritative)
        this.subQuestions.push(subQuestionDetail);
        console.log('✅ Added FINAL sub_question to subQuestions:', cleanedQuestion);
        
        // Extract documents from sub-question context_docs
        if (subQ.context_docs?.top_documents) {
          console.log('📄 Extracting documents from sub-question context_docs:', subQ.context_docs.top_documents.length);
          subQ.context_docs.top_documents.forEach((doc: any) => {
            const documentPacket: DocumentInfoPacket = {
              document_id: doc.document_id,
              document_name: doc.semantic_identifier,
              link: doc.link || '',
              source_type: doc.source_type,
              semantic_identifier: doc.semantic_identifier,
              blurb: doc.blurb,
              boost: doc.boost,
              score: doc.score,
              chunk_ind: doc.chunk_ind,
              match_highlights: doc.match_highlights || [],
              metadata: doc.metadata || {},
              updated_at: doc.updated_at,
              is_internet: doc.is_internet || false,
            };
            
            const exists = this.documents.some(existingDoc => existingDoc.document_id === doc.document_id);
            if (!exists) {
              this.documents.push(documentPacket);
              console.log('📄 Added document from sub-question:', documentPacket.semantic_identifier);
            }
          });
        }
      });
      
      console.log('✅ FINAL sub_questions processing complete. Total count:', this.subQuestions.length);
      console.log('📋 Final subQuestions summary:', this.subQuestions.map(sq => ({
        level_question_num: sq.level_question_num,
        question: sq.question.substring(0, 50) + '...'
      })));
    }
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
    // When stream is complete, mark all sub-queries as done for progress display
    const progressSubQueries = this.isComplete 
      ? this.subQueries.map(sq => ({ ...sq, status: 'done' as const }))
      : this.subQueries;

    // Determine current phase based on the state
    let phase: SearchProgress['phase'] = 'waiting';
    
    if (progressSubQueries.length > 0) {
      const allDone = progressSubQueries.every(sq => sq.status === 'done');
      const anyInProgress = progressSubQueries.some(sq => sq.status === 'in_progress');
      
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
      subQueries: progressSubQueries,
      subQuestions: this.subQuestions, // 添加子问题详情
      documents: this.documents,
      thinkingContent: this.currentThinking,
      currentAnswer: this.currentAnswer,
    };
  }

  isStreamComplete(): boolean {
    console.log('🔍 Checking stream completion:', this.isComplete);
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
    this.subQuestions = [];
    this.documents = [];
    this.isComplete = false;
    this.error = null;
    this.messageDetail = null;
    this.hasFinalSubQuestions = false;
  }

  // Clear only sub-queries to remove fragmented data
  clearSubQueries(): void {
    this.subQueries = [];
    this.subQuestions = [];
    this.hasFinalSubQuestions = false;
  }

  // Generate a complete ChatMessage from the current state
  generateChatMessage(): ChatMessage {
    // When generating final message, mark all sub-queries as complete if stream is done
    const finalSubQueries = this.isComplete 
      ? this.subQueries.map(sq => ({ ...sq, status: 'done' as const }))
      : this.subQueries;

    // When generating final message, ensure all sub-questions are complete
    // Note: Final sub_questions from ChatMessageDetail packets are already complete
    const finalSubQuestions = this.subQuestions.map(sq => ({ 
      ...sq, 
      is_complete: true // Always mark as complete for final message display
    }));

    // Enhanced debugging for complete message generation
    console.log('📊 generateChatMessage - Final data status:', {
      documentsCount: this.documents.length,
      subQueriesCount: finalSubQueries.length,
      subQuestionsCount: finalSubQuestions.length,
      isComplete: this.isComplete,
      currentAnswerLength: this.currentAnswer.length,
      // Debug subQuestions structure
      subQuestionsStructure: finalSubQuestions.map(sq => ({
        question: sq.question?.substring(0, 50) + '...',
        hasAnswer: !!sq.answer,
        level: sq.level,
        level_question_num: sq.level_question_num,
        is_complete: sq.is_complete
      }))
    });

    const message: ChatMessage = {
      id: this.messageId,
      type: 'assistant' as const,
      content: this.currentAnswer,
      timestamp: new Date(),
      isStreaming: !this.isComplete,
      documents: this.documents,
      subQueries: finalSubQueries, // 保留兼容性
      subQuestions: finalSubQuestions, // 新增：正确的字段
      thinkingContent: this.currentThinking,
      error: this.error || undefined,
      citations: this.generateCitations(),
    };

    console.log('📨 Final ChatMessage generated:', {
      id: message.id,
      documentsLength: message.documents?.length || 0,
      subQueriesLength: message.subQueries?.length || 0,
      subQuestionsLength: message.subQuestions?.length || 0,
      citationsLength: message.citations?.length || 0,
      isStreaming: message.isStreaming
    });

    return message;
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
    
    // 如果新文本与当前目标文本相同，跳过处理
    if (this.targetText === newText) {
      return;
    }
    
    // 如果新文本是当前文本的延伸（追加内容），只处理新增部分
    if (newText.startsWith(this.targetText)) {
      const newPart = newText.substring(this.targetText.length);
      this.targetText = newText;
      
      // 将新部分切分并添加到现有chunks
      const newChunks = this.smartChunkText(newPart);
      this.chunks = [...this.chunks, ...newChunks];
      
      console.log('⌨️ TypingEffect: Appended new chunks:', newChunks);
    } else {
      // 完全新的文本，重新开始
      this.targetText = newText;
      this.chunks = this.smartChunkText(newText);
      this.chunkIndex = 0;
      
      console.log('⌨️ TypingEffect: Full text reset');
    }
    
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