import { AppConfig } from '@/types';

export const APP_CONFIG: AppConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080',
  maxFileSize: 10 * 1024 * 1024, // 10MB
  allowedFileTypes: [
    // Documents
    '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
    // Spreadsheets
    '.csv', '.xls', '.xlsx', '.ods',
    // Presentations
    '.ppt', '.pptx', '.odp',
    // Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
    // Web files
    '.html', '.htm', '.xml', '.json', '.md', '.markdown',
    // Archives
    '.zip', '.rar', '.7z', '.tar', '.gz',
    // Code files
    '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.c', '.cpp',
    '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
    '.sh', '.bash', '.sql', '.yaml', '.yml', '.toml', '.ini',
  ],
  maxFiles: 150,
  streamingEnabled: true,
  agenticSearchEnabled: true,
};

export const THEMES = {
  glassmorphism: {
    name: 'Glassmorphism',
    primary: 'rgba(255, 255, 255, 0.1)',
    secondary: 'rgba(255, 255, 255, 0.05)',
    accent: 'rgba(59, 130, 246, 0.8)',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    blur: 'blur(10px)',
    border: 'rgba(255, 255, 255, 0.2)',
  },
  neumorphic: {
    name: 'Neumorphic',
    primary: '#e0e0e0',
    secondary: '#f5f5f5',
    accent: '#3b82f6',
    background: 'linear-gradient(145deg, #e6e6e6, #ffffff)',
    shadowLight: 'rgba(255, 255, 255, 0.8)',
    shadowDark: 'rgba(0, 0, 0, 0.2)',
  },
};

export const ANIMATIONS = {
  duration: {
    fast: 150,
    normal: 300,
    slow: 500,
  },
  easing: {
    ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },
};

export const BREAKPOINTS = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
};

export const Z_INDEX = {
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
  toast: 1080,
};

export const FILE_UPLOAD_CONFIG = {
  chunkSize: 1024 * 1024, // 1MB chunks
  maxRetries: 3,
  retryDelay: 1000, // 1 second
  progressUpdateInterval: 100, // 100ms
};

export const CHAT_CONFIG = {
  maxMessageLength: 4000,
  streamingChunkSize: 1024,
  typingIndicatorDelay: 500,
  autoSaveInterval: 30000, // 30 seconds
  maxStoredSessions: 10,
  defaultTemperature: 0.7,
  maxTokens: 4000,
};

export const API_ENDPOINTS = {
  // File management
  uploadFile: '/chat/file',  // Use chat file upload for FILE_CONNECTOR__ prefix
  indexingStatus: '/user/file/indexing-status', // GET method with query params
  deleteFile: '/user/file',
  reindexFile: '/user/file/reindex',
  
  // Folder management
  createFolder: '/user/folder',
  deleteFolder: '/user/folder',
  getUserFolders: '/user/folder',
  
  // Chat
  sendMessage: '/chat/send-message',
  createChatSession: '/chat/create-chat-session',
  
  // Personas
  getPersonas: '/persona',
  
  // LLM Provider Management
  getLLMProviders: '/admin/llm/provider',
  createLLMProvider: '/admin/llm/provider',
  updateLLMProvider: '/admin/llm/provider',
  deleteLLMProvider: '/admin/llm/provider',
  testLLMProvider: '/admin/llm/test',
  setDefaultProvider: '/admin/llm/provider',
  setDefaultVisionProvider: '/admin/llm/provider',
} as const;

export const STORAGE_KEYS = {
  chatSessions: 'onyx-chat-sessions',
  userPreferences: 'onyx-user-preferences',
  uploadedFiles: 'onyx-uploaded-files',
  appTheme: 'onyx-app-theme',
  apiConfig: 'onyx-api-config',
} as const;

export const ERROR_MESSAGES = {
  upload: {
    fileTooBig: 'File is too large. Maximum size is 10MB.',
    invalidType: 'File type not supported.',
    tooManyFiles: 'Too many files. Maximum is 150 files.',
    uploadFailed: 'Failed to upload file. Please try again.',
    indexingFailed: 'File indexing failed. Please try again.',
  },
  chat: {
    messageEmpty: 'Please enter a message.',
    messageTooLong: 'Message is too long. Maximum length is 4000 characters.',
    sendFailed: 'Failed to send message. Please try again.',
    streamingError: 'Error in streaming response.',
    noSession: 'No chat session found. Please refresh the page.',
  },
  api: {
    networkError: 'Network error. Please check your connection.',
    serverError: 'Server error. Please try again later.',
    unauthorized: 'Unauthorized. Please check your credentials.',
    rateLimited: 'Too many requests. Please wait a moment.',
    timeout: 'Request timeout. Please try again.',
  },
  general: {
    unknown: 'An unknown error occurred.',
    browserNotSupported: 'Your browser is not supported.',
    featureNotAvailable: 'This feature is not available.',
  },
} as const;

export const SUCCESS_MESSAGES = {
  upload: {
    fileUploaded: 'File uploaded successfully.',
    filesUploaded: 'All files uploaded successfully.',
    indexingComplete: 'File indexing completed.',
  },
  chat: {
    messageSent: 'Message sent successfully.',
    sessionCreated: 'Chat session created.',
    chatCleared: 'Chat cleared successfully.',
  },
  general: {
    saved: 'Settings saved successfully.',
    copied: 'Copied to clipboard.',
    deleted: 'Deleted successfully.',
  },
} as const;

export const LOADING_MESSAGES = {
  upload: [
    'Uploading your file...',
    'Processing file content...',
    'Creating document index...',
    'Almost ready...',
  ],
  chat: [
    'Thinking...',
    'Searching through documents...',
    'Analyzing content...',
    'Generating response...',
  ],
  index: [
    'Indexing document...',
    'Extracting text content...',
    'Building search vectors...',
    'Finalizing index...',
  ],
};

export const DEFAULT_USER_PREFERENCES = {
  theme: {
    mode: 'auto' as const,
    primaryColor: '#3b82f6',
    glassmorphism: true,
    neumorphic: false,
    animations: true,
  },
  accessibility: {
    reduceMotion: false,
    highContrast: false,
    focusVisible: true,
    screenReader: false,
  },
  performance: {
    enableAnimations: true,
    enableGlassmorphism: true,
    enableNeumorphic: false,
  },
  chat: {
    enableAgenticSearch: true,
    defaultTemperature: 0.7,
    autoSave: true,
  },
};

export const SUPPORTED_MODELS = {
  openai: [
    { id: 'gpt-4o', name: 'GPT-4O', provider: 'openai' },
    { id: 'gpt-4o-mini', name: 'GPT-4O Mini', provider: 'openai' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai' },
  ],
  anthropic: [
    { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', provider: 'anthropic' },
    { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', provider: 'anthropic' },
  ],
  custom: [
    { id: 'custom-model', name: 'Custom Model', provider: 'custom' },
  ],
};

export const GLASSMORPHISM_VARIANTS = {
  light: 'rgba(255, 255, 255, 0.1)',
  medium: 'rgba(255, 255, 255, 0.15)',
  strong: 'rgba(255, 255, 255, 0.25)',
  accent: 'rgba(59, 130, 246, 0.1)',
  success: 'rgba(34, 197, 94, 0.1)',
  warning: 'rgba(245, 158, 11, 0.1)',
  danger: 'rgba(239, 68, 68, 0.1)',
};

export const NEUMORPHIC_VARIANTS = {
  raised: {
    boxShadow: '8px 8px 16px rgba(0, 0, 0, 0.2), -8px -8px 16px rgba(255, 255, 255, 0.8)',
  },
  pressed: {
    boxShadow: 'inset 6px 6px 12px rgba(0, 0, 0, 0.2), inset -6px -6px 12px rgba(255, 255, 255, 0.8)',
  },
  flat: {
    boxShadow: '4px 4px 8px rgba(0, 0, 0, 0.15), -4px -4px 8px rgba(255, 255, 255, 0.9)',
  },
};