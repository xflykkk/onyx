import { 
  APP_CONFIG, 
  API_ENDPOINTS, 
  FILE_UPLOAD_CONFIG, 
  ERROR_MESSAGES 
} from './config';
import {
  FileUploadResponse,
  IndexingStatus,
  ChatSession,
  CreateChatSessionRequest,
  CreateChatMessageRequest,
  Persona,
  APIError,
  StreamingResponse,
  LLMProvider,
  CreateLLMProviderRequest,
  TestLLMProviderRequest,
  LLMProviderTestResult,
  StreamLogDetail,
  StreamLogListItem,
  StreamLogsStats,
  StreamLogRawContent,
  SearchSettings,
  UpdateSearchSettingsRequest,
} from '@/types';

class APIClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseUrl = APP_CONFIG.apiBaseUrl;
    this.defaultHeaders = {
      'Accept': 'application/json',
    };
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let errorMessage: string = ERROR_MESSAGES.api.serverError;
      
      switch (response.status) {
        case 400:
          errorMessage = ERROR_MESSAGES.api.serverError; // Use generic server error for consistency
          break;
        case 401:
          errorMessage = ERROR_MESSAGES.api.unauthorized;
          break;
        case 403:
          errorMessage = ERROR_MESSAGES.api.serverError; // Use generic server error for consistency
          break;
        case 404:
          errorMessage = ERROR_MESSAGES.api.serverError; // Use generic server error for consistency
          break;
        case 422:
          errorMessage = ERROR_MESSAGES.api.serverError; // Use generic server error for consistency
          break;
        case 429:
          errorMessage = ERROR_MESSAGES.api.rateLimited;
          break;
        case 500:
          errorMessage = ERROR_MESSAGES.api.serverError;
          break;
        case 502:
        case 503:
        case 504:
          errorMessage = ERROR_MESSAGES.api.serverError; // Use generic server error for consistency
          break;
        default:
          errorMessage = ERROR_MESSAGES.api.serverError; // Use generic server error for consistency
      }

      try {
        const errorData = await response.json();
        if (errorData.message || errorData.detail) {
          errorMessage = errorData.message || errorData.detail;
        }
      } catch {
        // Use the default error message if JSON parsing fails
      }

      const error: APIError = {
        status: response.status,
        message: errorMessage,
      };
      
      throw error;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return response.text() as T;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
    };

    // Add Content-Type for JSON requests
    if (options.body && typeof options.body === 'string') {
      config.headers = {
        ...config.headers,
        'Content-Type': 'application/json',
      };
    }

    try {
      const response = await fetch(url, config);
      return await this.handleResponse<T>(response);
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        const networkError: APIError = {
          status: 0,
          message: ERROR_MESSAGES.api.networkError,
        };
        throw networkError;
      }
      throw error;
    }
  }

  // File Upload APIs
  async uploadFiles(files: File[], folderId?: number): Promise<FileUploadResponse[]> {
    const formData = new FormData();
    
    files.forEach(file => {
      formData.append('files', file);
    });

    // Note: /chat/file endpoint doesn't support folder_id parameter
    // folderId is ignored for chat uploads

    const response = await this.request<{files: any[]}>(API_ENDPOINTS.uploadFile, {
      method: 'POST',
      body: formData,
      headers: {
        // Don't set Content-Type for FormData, let browser set it
        'Accept': 'application/json',
      },
    });

    // Convert chat file response format to FileUploadResponse format
    return response.files.map((file, index) => ({
      id: file.id, // 🔧 Use the actual file UUID as ID instead of timestamp
      name: file.name || 'Unknown',
      size: 0, // Chat endpoint doesn't return size
      content_type: 'application/octet-stream', // Default content type
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_public: false,
      folder_id: undefined,
      file_id: file.id, // Store the actual string file ID for backend reference
    }));
  }

  async getIndexingStatus(fileIds: (number | string)[]): Promise<IndexingStatus> {
    const params = new URLSearchParams();
    fileIds.forEach(id => params.append('file_ids', id.toString()));
    
    return this.request<IndexingStatus>(
      `${API_ENDPOINTS.indexingStatus}?${params.toString()}`
    );
  }

  async deleteFile(fileId: number): Promise<void> {
    await this.request<void>(`${API_ENDPOINTS.deleteFile}/${fileId}`, {
      method: 'DELETE',
    });
  }

  async reindexFile(fileId: number): Promise<void> {
    return this.request<void>(API_ENDPOINTS.reindexFile, {
      method: 'POST',
      body: JSON.stringify({ file_id: fileId }),
    });
  }

  // 🔧 新增：获取用户文件夹列表
  async getUserFolders(): Promise<Array<{
    id: number;
    name: string;
    files: Array<{
      id: number;
      file_id: string;
      name: string;
      user_id: string;
    }>;
  }>> {
    return this.request<Array<{
      id: number;
      name: string;
      files: Array<{
        id: number;
        file_id: string;
        name: string;
        user_id: string;
      }>;
    }>>(API_ENDPOINTS.getUserFolders);
  }

  async getUserFileByUUID(fileUUID: string): Promise<{id: number, file_id: string} | null> {
    try {
      console.log('🔍 Looking up UserFile for UUID:', fileUUID);
      
      // 获取所有文件夹及其文件列表
      const folders = await this.getUserFolders();
      
      // 遍历所有文件夹中的文件，查找匹配的 UUID
      for (const folder of folders) {
        for (const file of folder.files) {
          if (file.file_id === fileUUID) {
            console.log('✅ Found UserFile:', { id: file.id, file_id: file.file_id, name: file.name });
            return { id: file.id, file_id: file.file_id };
          }
        }
      }
      
      console.warn('⚠️ UserFile not found for UUID:', fileUUID);
      return null;
    } catch (error) {
      console.error('Error looking up UserFile by UUID:', error);
      return null;
    }
  }

  // 🔧 新增：批量转换UUID到UserFile ID
  async convertUUIDsToUserFileIds(fileUUIDs: string[]): Promise<number[]> {
    const userFileIds: number[] = [];
    
    for (const uuid of fileUUIDs) {
      const userFile = await this.getUserFileByUUID(uuid);
      if (userFile) {
        userFileIds.push(userFile.id);
      } else {
        console.warn('⚠️ Could not find UserFile for UUID:', uuid);
      }
    }
    
    return userFileIds;
  }

  // Folder APIs
  async createFolder(name: string, description?: string): Promise<{ id: number }> {
    return this.request<{ id: number }>(API_ENDPOINTS.createFolder, {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  }

  async deleteFolder(folderId: number): Promise<void> {
    await this.request<void>(`${API_ENDPOINTS.deleteFolder}/${folderId}`, {
      method: 'DELETE',
    });
  }

  // Chat APIs
  async getPersonas(): Promise<Persona[]> {
    return this.request<Persona[]>(API_ENDPOINTS.getPersonas);
  }

  async createChatSession(request: CreateChatSessionRequest): Promise<ChatSession> {
    return this.request<ChatSession>(API_ENDPOINTS.createChatSession, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async sendMessage(request: CreateChatMessageRequest): Promise<StreamingResponse> {
    const url = `${this.baseUrl}${API_ENDPOINTS.sendMessage}`;
    const abortController = new AbortController();
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(request),
      signal: abortController.signal,
    });

    if (!response.ok) {
      await this.handleResponse(response); // This will throw an error
    }

    if (!response.body) {
      throw new Error('No response body available for streaming');
    }

    const reader = response.body.getReader();
    
    return {
      reader,
      abortController,
    };
  }

  // Utility methods
  async checkHealth(): Promise<{ status: string }> {
    try {
      return await this.request<{ status: string }>('/health');
    } catch {
      return { status: 'unhealthy' };
    }
  }

  // LLM Provider Management APIs
  async getLLMProviders(): Promise<LLMProvider[]> {
    return this.request<LLMProvider[]>('/admin/llm/provider');
  }

  async createLLMProvider(request: CreateLLMProviderRequest): Promise<LLMProvider> {
    return this.request<LLMProvider>('/admin/llm/provider?is_creation=true', {
      method: 'PUT',
      body: JSON.stringify(request),
    });
  }

  async updateLLMProvider(request: CreateLLMProviderRequest): Promise<LLMProvider> {
    return this.request<LLMProvider>('/admin/llm/provider?is_creation=false', {
      method: 'PUT',
      body: JSON.stringify(request),
    });
  }

  async deleteLLMProvider(providerId: number): Promise<void> {
    await this.request<void>(`/admin/llm/provider/${providerId}`, {
      method: 'DELETE',
    });
  }

  async testLLMProvider(request: TestLLMProviderRequest): Promise<LLMProviderTestResult> {
    try {
      console.log('🔗 Calling LLM test API:', '/admin/llm/test');
      console.log('📦 Request payload:', JSON.stringify(request, null, 2));
      
      const response = await this.request<void>('/admin/llm/test', {
        method: 'POST',
        body: JSON.stringify(request),
      });
      
      console.log('✅ LLM test successful:', response);
      return { success: true };
    } catch (error: any) {
      // Use console.warn instead of console.error to avoid triggering Next.js error boundary
      console.warn('⚠️ LLM test failed:', error?.message || 'Unknown error');
      console.warn('Status:', error?.status);
      console.warn('Message:', error?.message);
      
      return { 
        success: false, 
        error: error.message || 'Test failed' 
      };
    }
  }

  async setDefaultProvider(providerId: number): Promise<void> {
    await this.request<void>(`/admin/llm/provider/${providerId}/default`, {
      method: 'POST',
    });
  }

  async setDefaultVisionProvider(providerId: number, visionModel?: string): Promise<void> {
    const params = visionModel ? `?vision_model=${encodeURIComponent(visionModel)}` : '';
    await this.request<void>(`/admin/llm/provider/${providerId}/default-vision${params}`, {
      method: 'POST',
    });
  }

  async validateFileType(file: File): Promise<boolean> {
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    return APP_CONFIG.allowedFileTypes.includes(fileExtension);
  }

  async validateFileSize(file: File): Promise<boolean> {
    return file.size <= APP_CONFIG.maxFileSize;
  }

  async validateFiles(files: File[]): Promise<{
    valid: File[];
    invalid: { file: File; reason: string }[];
  }> {
    const valid: File[] = [];
    const invalid: { file: File; reason: string }[] = [];

    for (const file of files) {
      if (!await this.validateFileSize(file)) {
        invalid.push({ file, reason: ERROR_MESSAGES.upload.fileTooBig });
        continue;
      }

      if (!await this.validateFileType(file)) {
        invalid.push({ file, reason: ERROR_MESSAGES.upload.invalidType });
        continue;
      }

      valid.push(file);
    }

    if (valid.length > APP_CONFIG.maxFiles) {
      const excess = valid.splice(APP_CONFIG.maxFiles);
      excess.forEach(file => {
        invalid.push({ file, reason: ERROR_MESSAGES.upload.tooManyFiles });
      });
    }

    return { valid, invalid };
  }

  // Stream Logs API methods
  async getLatestStreamLog(): Promise<StreamLogDetail> {
    return this.request<StreamLogDetail>('/stream-logs/latest');
  }

  async getStreamLogsList(): Promise<{ log_files: StreamLogListItem[] }> {
    return this.request<{ log_files: StreamLogListItem[] }>('/stream-logs/list');
  }

  async getStreamLogByFilename(filename: string): Promise<StreamLogDetail> {
    return this.request<StreamLogDetail>(`/stream-logs/${filename}`);
  }

  async getStreamLogsStats(): Promise<StreamLogsStats> {
    return this.request<StreamLogsStats>('/stream-logs/summary/stats');
  }

  async getStreamLogRawContent(filename: string): Promise<StreamLogRawContent> {
    return this.request<StreamLogRawContent>(`/stream-logs/${filename}/raw`);
  }

  async getCurrentSearchSettings(): Promise<SearchSettings> {
    return this.request<SearchSettings>('/search-settings/get-current-search-settings');
  }

  async updateSearchSettings(request: UpdateSearchSettingsRequest): Promise<SearchSettings> {
    // First get current settings
    const currentSettings = await this.getCurrentSearchSettings();
    
    // Create a request with only the multilingual_expansion changed
    // Using the update-inference-settings endpoint which updates existing settings
    const fullRequest = {
      model_name: currentSettings.model_name,
      model_dim: currentSettings.model_dim,
      normalize: currentSettings.normalize,
      query_prefix: currentSettings.query_prefix,
      passage_prefix: currentSettings.passage_prefix,
      provider_type: currentSettings.provider_type,
      index_name: currentSettings.index_name, // Keep the existing index_name
      multipass_indexing: currentSettings.multipass_indexing,
      embedding_precision: currentSettings.embedding_precision,
      reduced_dimension: currentSettings.reduced_dimension,
      background_reindex_enabled: currentSettings.background_reindex_enabled,
      enable_contextual_rag: currentSettings.enable_contextual_rag,
      contextual_rag_llm_name: currentSettings.contextual_rag_llm_name,
      contextual_rag_llm_provider: currentSettings.contextual_rag_llm_provider,
      multilingual_expansion: request.multilingual_expansion,
      disable_rerank_for_streaming: currentSettings.disable_rerank_for_streaming,
      rerank_model_name: currentSettings.rerank_model_name,
      rerank_provider_type: currentSettings.rerank_provider_type,
      rerank_api_key: currentSettings.rerank_api_key,
      rerank_api_url: currentSettings.rerank_api_url,
      num_rerank: currentSettings.num_rerank,
    };
    
    // Use the update-inference-settings endpoint which updates existing settings
    await this.request<void>('/search-settings/update-inference-settings', {
      method: 'POST',
      body: JSON.stringify(fullRequest),
    });
    
    // Return the updated settings
    return this.getCurrentSearchSettings();
  }
}

// Streaming utilities (note: this class may already be exported elsewhere)
class SSEParserInternal {
  private buffer = '';
  
  parseChunk(chunk: string): string[] {
    this.buffer += chunk;
    const lines = this.buffer.split('\n');
    
    // Keep the last (potentially incomplete) line in the buffer
    this.buffer = lines.pop() || '';
    
    const events: string[] = [];
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      
      // Skip empty lines
      if (!trimmedLine) {
        continue;
      }
      
      // Handle standard SSE format with "data: " prefix
      if (line.startsWith('data: ')) {
        const data = line.slice(6); // Remove 'data: ' prefix
        if (data.trim() && data !== '[DONE]') {
          events.push(data);
        }
      }
      // Handle direct JSON format (what Onyx backend actually sends)
      else if (trimmedLine.startsWith('{') && trimmedLine.endsWith('}')) {
        try {
          // Validate it's proper JSON by attempting to parse
          JSON.parse(trimmedLine);
          events.push(trimmedLine);
        } catch (error) {
          console.warn('Failed to parse JSON line:', trimmedLine, error);
        }
      }
      // Handle other SSE event types if needed
      else if (line.startsWith('event: ') || line.startsWith('id: ') || line.startsWith('retry: ')) {
        // These are SSE metadata lines, skip them for now
        continue;
      }
      else {
        // Log unexpected formats for debugging
        console.warn('Unexpected SSE line format:', line);
      }
    }
    
    return events;
  }
  
  reset(): void {
    this.buffer = '';
  }
}

export { SSEParserInternal as SSEParser };

export async function* processSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  signal?: AbortSignal
): AsyncGenerator<string, void, unknown> {
  const decoder = new TextDecoder();
  const parser = new SSEParserInternal();
  
  try {
    while (!signal?.aborted) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }
      
      const chunk = decoder.decode(value, { stream: true });
      const events = parser.parseChunk(chunk);
      
      for (const event of events) {
        yield event;
      }
    }
  } finally {
    parser.reset();
    reader.releaseLock();
  }
}

// Create singleton instance
export const apiClient = new APIClient();

// Export utility functions
export const uploadFiles = (files: File[], folderId?: number) => 
  apiClient.uploadFiles(files, folderId);

export const getIndexingStatus = (fileIds: (number | string)[]) => 
  apiClient.getIndexingStatus(fileIds);

export const deleteFile = (fileId: number) => 
  apiClient.deleteFile(fileId);

export const reindexFile = (fileId: number) => 
  apiClient.reindexFile(fileId);

export const createFolder = (name: string, description?: string) => 
  apiClient.createFolder(name, description);

export const deleteFolder = (folderId: number) => 
  apiClient.deleteFolder(folderId);

export const getPersonas = () => 
  apiClient.getPersonas();

export const createChatSession = (request: CreateChatSessionRequest) => 
  apiClient.createChatSession(request);

export const sendMessage = (request: CreateChatMessageRequest) => 
  apiClient.sendMessage(request);

export const validateFiles = (files: File[]) => 
  apiClient.validateFiles(files);

export const checkAPIHealth = () => 
  apiClient.checkHealth();

// LLM Provider management functions
export const getLLMProviders = () => 
  apiClient.getLLMProviders();

export const createLLMProvider = (request: CreateLLMProviderRequest) => 
  apiClient.createLLMProvider(request);

export const updateLLMProvider = (request: CreateLLMProviderRequest) => 
  apiClient.updateLLMProvider(request);

export const deleteLLMProvider = (providerId: number) => 
  apiClient.deleteLLMProvider(providerId);

export const testLLMProvider = (request: TestLLMProviderRequest) => 
  apiClient.testLLMProvider(request);

export const setDefaultProvider = (providerId: number) => 
  apiClient.setDefaultProvider(providerId);

export const setDefaultVisionProvider = (providerId: number, visionModel?: string) => 
  apiClient.setDefaultVisionProvider(providerId, visionModel);

// Stream Logs API exports
export const getLatestStreamLog = () => 
  apiClient.getLatestStreamLog();

export const getStreamLogsList = () => 
  apiClient.getStreamLogsList();

export const getStreamLogByFilename = (filename: string) => 
  apiClient.getStreamLogByFilename(filename);

export const getStreamLogsStats = () => 
  apiClient.getStreamLogsStats();

export const getStreamLogRawContent = (filename: string) => 
  apiClient.getStreamLogRawContent(filename);

// Search Settings API exports
export const getCurrentSearchSettings = () => 
  apiClient.getCurrentSearchSettings();

export const updateSearchSettings = (request: UpdateSearchSettingsRequest) => 
  apiClient.updateSearchSettings(request);