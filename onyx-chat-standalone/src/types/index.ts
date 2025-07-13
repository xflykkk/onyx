// API Types based on Onyx backend interfaces

export interface FileUploadResponse {
  id: number;
  name: string;
  size: number;
  content_type: string;
  created_at: string;
  updated_at: string;
  is_public: boolean;
  folder_id?: number;
  file_id?: string; // The actual file ID from backend (for chat uploads)
}

export interface IndexingStatus {
  [fileId: string]: boolean;
}

export interface ChatSession {
  chat_session_id: string;
  persona_id: number;
  description: string;
  created_at: string;
}

export interface CreateChatSessionRequest {
  persona_id?: number;
  description?: string;
}

export interface CreateChatMessageRequest {
  chat_session_id: string;
  parent_message_id?: number | null;
  message: string;
  file_descriptors?: FileDescriptor[];
  search_doc_ids?: number[];
  user_file_ids?: number[]; // Changed back to number[] for UserFile IDs
  user_folder_ids?: number[];
  prompt_id?: number | null;
  retrieval_options?: RetrievalDetails | null;
  rerank_settings?: RerankingDetails | null;
  query_override?: string | null;
  regenerate?: boolean;
  llm_override?: LLMOverride | null;
  prompt_override?: string | null;
  temperature_override?: number | null;
  alternate_assistant_id?: number | null;
  persona_override_config?: PersonaOverrideConfig | null;
  use_existing_user_message?: boolean;
  existing_assistant_message_id?: number | null;
  structured_response_format?: any | null;
  use_agentic_search?: boolean;
  skip_gen_ai_answer_generation?: boolean;
}

export interface FileDescriptor {
  id: string;
  type: 'image' | 'document' | 'plain_text' | 'csv' | 'user_knowledge';
  filename: string;
  content_type: string;
  size: number;
}

export interface RetrievalDetails {
  run_search?: "always" | "never" | "auto";
  real_time?: boolean;
  enable_auto_detect_filters?: boolean;
  dedupe_docs?: boolean;
  chunks_above?: number;
  chunks_below?: number;
  full_doc?: boolean;
}

export interface RerankingDetails {
  num_rerank?: number;
}

export interface LLMOverride {
  model_provider: string;
  model_version: string;
  temperature?: number;
}

export interface PersonaOverrideConfig {
  // Define as needed
}

export interface Persona {
  id: number;
  name: string;
  description?: string;
  system_prompt?: string;
  tools?: string[];
  is_public: boolean;
  created_at: string;
}

// SSE Response Types
export interface SSEMessage {
  type: string;
  data: any;
}

export interface AnswerPiecePacket {
  answer_piece: string;
}

export interface DocumentInfoPacket {
  document_id: string;
  document_name: string;
  link: string;
  source_type: string;
  semantic_identifier: string;
  blurb: string;
  boost: number;
  score: number;
  chunk_ind: number;
  match_highlights: string[];
  metadata: Record<string, any>;
  updated_at: string;
  is_internet: boolean;
}

// Based on onyx/web implementation
export interface SubQueryDetail {
  query: string;
  query_id: number;
  doc_ids?: number[] | null;
}

export interface SubQuestionDetail {
  level: number;
  level_question_num: number;
  question: string;
  answer?: string;
  sub_queries?: SubQueryDetail[] | null;
  context_docs?: { top_documents: OnyxDocument[] } | null;
  is_complete?: boolean;
  is_stopped?: boolean;
  answer_streaming?: boolean;
}

// For streaming pieces - compatible with backend data
export interface SubQueryPiece {
  sub_query: string;
  level: number;
  level_question_num: number;
  query_id?: number;
  status?: "todo" | "in_progress" | "done";
  analysis?: string;
  search_queries?: string[];
  documents?: DocumentInfoPacket[];
  
  // Additional fields that may come from backend
  question?: string;
  answer?: string;
  is_complete?: boolean;
  sub_queries?: SubQueryDetail[] | Array<{
    query: string;
    status: "todo" | "in_progress" | "done";
  }>;
  context_docs?: {
    top_documents: OnyxDocument[];
  };
}

// Stream piece types for constructSubQuestions
export interface SubQuestionPiece {
  sub_question: string;
  level: number;
  level_question_num: number;
}

export interface AgentAnswerPiece {
  answer_piece: string;
  level: number;
  level_question_num: number;
  answer_type?: string;
}

export interface SubQuestionSearchDoc {
  top_documents: OnyxDocument[];
  level: number;
  level_question_num: number;
  rephrased_query?: string;
}

export interface StreamStopInfo {
  stop_reason: string;
  stream_type: string;
  level: number;
  level_question_num: number;
}

// Union type for constructSubQuestions
export type StreamingDetail = 
  | SubQuestionPiece 
  | SubQueryPiece 
  | AgentAnswerPiece 
  | SubQuestionSearchDoc 
  | StreamStopInfo;

export interface ThinkingTokens {
  thinking_content: string;
}

export interface StreamingError {
  error: string;
  error_type: string;
}

export interface ChatMessageDetailPacket {
  message_id: number;
  parent_message: number | null;
  latest_child_message: number | null;
  message: string;
  message_type: string;
  time_sent: string;
  citations: any[];
  files: any[];
  error: string | null;
  feedback: any | null;
}

export interface ToolCallMetadata {
  tool_name: string;
  tool_input: any;
  tool_result?: any;
}

export interface BackendMessage {
  message_type: string;
  content: any;
}

export type PacketType = 
  | ToolCallMetadata
  | BackendMessage
  | AnswerPiecePacket
  | DocumentInfoPacket
  | StreamingError
  | SubQueryPiece
  | ThinkingTokens
  | ChatMessageDetailPacket;

// Chat UI Types
export interface ChatMessage {
  id: string;
  messageId?: number | null; // Backend message ID for parentMessageId tracking
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  documents?: DocumentInfoPacket[];
  subQuestions?: SubQuestionDetail[]; // 正确字段名，使用 SubQuestionDetail 类型
  subQueries?: SubQueryPiece[]; // 保留兼容性
  thinkingContent?: string;
  error?: string;
  citations?: Citation[];
}

export interface Citation {
  documentId: string;
  documentName: string;
  link: string;
  text: string;
  sourceType: string;
  // Extended properties for enhanced functionality
  semanticIdentifier?: string;
  blurb?: string;
  matchHighlights?: string[];
  score?: number;
  isInternet?: boolean;
  metadata?: Record<string, any>;
}

// Enhanced Document interface for compatibility with onyx/web
export interface OnyxDocument {
  document_id: string;
  semantic_identifier: string;
  link: string | null;
  source_type: string;
  blurb: string;
  boost: number;
  score: number;
  chunk_ind: number;
  match_highlights: string[];
  metadata: Record<string, any>;
  updated_at: string;
  is_internet: boolean;
}

// Document card properties for citation tooltips
export interface DocumentCardProps {
  document: OnyxDocument;
  updatePresentingDocument: (document: OnyxDocument) => void;
  icon?: React.ReactNode;
  url?: string;
}

// Question card properties for sub-question citations
export interface QuestionCardProps {
  question: SubQuestionDetail;
  openQuestion: (question: SubQuestionDetail) => void;
}

// Sub question detail for agentic search
// Remove duplicate - already defined above

// File Upload Types
export interface UploadedFile {
  id: string;          // 🔧 使用UUID作为文件ID
  name: string;
  size: number;
  type: string;
  uploadedAt: Date;
  indexingStatus: "indexing" | "indexed" | "failed" | "reindexing";
  progress?: number;
  file_id?: string;    // 后端文件ID（与id相同）
}

// Chat State Types
export type ChatState = "idle" | "uploading" | "indexing" | "sending" | "streaming" | "error";

export interface SearchProgress {
  phase: "waiting" | "sub_queries" | "context_docs" | "answer" | "evaluate" | "complete";
  subQueries: SubQueryPiece[];
  subQuestions: SubQuestionDetail[]; // 添加子问题详情
  documents: DocumentInfoPacket[];
  thinkingContent: string;
  currentAnswer: string;
  isCollapsed?: boolean; // 添加折叠状态
  isCompleted?: boolean; // 添加完成状态
}

// API Error Types
export interface APIError {
  status: number;
  message: string;
  details?: any;
}

// Component Props Types
export interface FileUploadProps {
  onFileUpload: (files: File[]) => void;
  uploadedFiles: UploadedFile[];
  isUploading: boolean;
  className?: string;
}

export interface ChatInterfaceProps {
  uploadedFiles: UploadedFile[];
  onSendMessage: (message: string, fileIds: number[]) => void;
  messages: ChatMessage[];
  isLoading: boolean;
  searchProgress?: SearchProgress;
  className?: string;
}

export interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
  onCitationClick?: (citation: Citation) => void;
  className?: string;
}

export interface SearchProgressProps {
  progress: SearchProgress;
  className?: string;
}

// Utility Types
export interface StreamingResponse {
  reader: ReadableStreamDefaultReader<Uint8Array>;
  abortController: AbortController;
}

export interface StreamProcessor {
  processChunk: (chunk: string) => PacketType | null;
  isComplete: boolean;
  error: string | null;
}

// Configuration Types
export interface AppConfig {
  apiBaseUrl: string;
  maxFileSize: number;
  allowedFileTypes: string[];
  maxFiles: number;
  streamingEnabled: boolean;
  agenticSearchEnabled: boolean;
}

// Hook Types
export interface UseFileUploadReturn {
  uploadFiles: (files: File[]) => Promise<void>;
  uploadedFiles: UploadedFile[];
  isUploading: boolean;
  uploadProgress: Record<string, number>;
  error: string | null;
  clearFiles: () => void;
  removeFile: (fileId: string) => Promise<void>;  // 🔧 Changed from number to string
  retryIndexing: (fileId: string) => Promise<void>;  // 🔧 Changed from number to string
  clearError: () => void;
  getIndexedFileIds: () => string[];
  getFileById: (fileId: string) => UploadedFile | undefined;  // 🔧 Changed from number to string
  getTotalSize: () => number;
  getFilesByStatus: (status: UploadedFile['indexingStatus']) => UploadedFile[];
}

export interface UseChatReturn {
  messages: ChatMessage[];
  sendMessage: (message: string, fileIds?: number[], folderIds?: number[]) => Promise<void>;
  isLoading: boolean;
  searchProgress: SearchProgress | null;
  error: string | null;
  clearChat: () => void;
  newSession: () => Promise<void>;
  stopGeneration: () => void;
  clearError: () => void;
  regenerateLastMessage: () => Promise<void>;
  exportChat: () => void;
  getMessageById: (messageId: string) => ChatMessage | undefined;
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;
  deleteMessage: (messageId: string) => void;
  chatState: ChatState;
  chatSessionId: string | null;
  personas: Persona[];
}

export interface UseStreamingReturn {
  startStreaming: (url: string, body: any) => Promise<void>;
  isStreaming: boolean;
  error: string | null;
  stopStreaming: () => void;
}

// Theme Types
export type ThemeMode = "light" | "dark" | "auto";

export interface ThemeConfig {
  mode: ThemeMode;
  primaryColor: string;
  glassmorphism: boolean;
  neumorphic: boolean;
  animations: boolean;
}

// Animation Types
export interface AnimationConfig {
  duration: number;
  easing: string;
  enabled: boolean;
}

// Layout Types
export interface LayoutProps {
  children: React.ReactNode;
  className?: string;
  showSidebar?: boolean;
  sidebarContent?: React.ReactNode;
}

// Responsive Types
export type BreakpointSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl";

export interface ResponsiveConfig {
  breakpoint: BreakpointSize;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

// Accessibility Types
export interface A11yConfig {
  reduceMotion: boolean;
  highContrast: boolean;
  focusVisible: boolean;
  screenReader: boolean;
}

// Performance Types
export interface PerformanceMetrics {
  renderTime: number;
  streamingLatency: number;
  fileUploadSpeed: number;
  memoryUsage: number;
}

// Error Boundary Types
export interface ErrorInfo {
  componentStack: string;
  errorBoundary?: string;
}

export interface ErrorFallbackProps {
  error: Error;
  errorInfo: ErrorInfo;
  retry: () => void;
}

// Local Storage Types
export interface StoredChatSession {
  id: string;
  messages: ChatMessage[];
  uploadedFiles: UploadedFile[];
  createdAt: Date;
  lastActive: Date;
}

export interface UserPreferences {
  theme: ThemeConfig;
  accessibility: A11yConfig;
  performance: {
    enableAnimations: boolean;
    enableGlassmorphism: boolean;
    enableNeumorphic: boolean;
  };
  chat: {
    enableAgenticSearch: boolean;
    defaultTemperature: number;
    autoSave: boolean;
  };
}

// Export commonly used type combinations
export type ChatContextValue = {
  messages: ChatMessage[];
  sendMessage: (message: string, fileIds?: string[]) => Promise<void>;
  isLoading: boolean;
  searchProgress: SearchProgress | null;
  error: string | null;
  clearChat: () => void;
  stopGeneration: () => void;
  uploadedFiles: UploadedFile[];
  uploadFiles: (files: File[]) => Promise<void>;
  isUploading: boolean;
  chatState: ChatState;
};

export type APIResponse<T = any> = {
  success: boolean;
  data?: T;
  error?: APIError;
};

export type EventHandler<T = any> = (data: T) => void;

export type AsyncEventHandler<T = any> = (data: T) => Promise<void>;

// LLM Provider Management Types
export interface ModelConfiguration {
  name: string;
  is_visible: boolean;
  max_input_tokens?: number;
  api_key?: string;
  api_base?: string;
}

export interface LLMProvider {
  id: number;
  name: string;
  provider: string;
  api_key?: string;
  api_base?: string;
  api_version?: string;
  custom_config?: Record<string, string>;
  default_model_name: string;
  fast_default_model_name?: string;
  deployment_name?: string;
  is_public: boolean;
  groups: number[];
  default_vision_model?: string;
  model_configurations: ModelConfiguration[];
  is_default_provider?: boolean;
}

export interface CreateLLMProviderRequest {
  name: string;
  provider: string;
  api_key?: string;
  api_base?: string;
  api_version?: string;
  custom_config?: Record<string, string>;
  default_model_name: string;
  fast_default_model_name?: string;
  deployment_name?: string;
  is_public: boolean;
  groups: number[];
  default_vision_model?: string;
  model_configurations: ModelConfiguration[];
  api_key_changed: boolean;
}

export interface TestLLMProviderRequest {
  name: string;
  provider: string;
  api_key?: string;
  api_base?: string;
  api_version?: string;
  custom_config?: Record<string, string>;
  default_model_name: string;
  fast_default_model_name?: string;
  deployment_name?: string;
  model_configurations: ModelConfiguration[];
  api_key_changed: boolean;
}

export interface LLMProviderTestResult {
  success: boolean;
  error?: string;
}