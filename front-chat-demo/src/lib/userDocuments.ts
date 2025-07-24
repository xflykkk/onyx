import { APP_CONFIG } from './config';

// 用户文档相关的类型定义
export interface UserFolder {
  id: number;
  name: string;
  description: string;
  created_at: string;
  user_id: number;
  display_priority?: number;
}

export interface UserFile {
  id: number;
  name: string;
  display_name?: string; // 可选，因为可能不存在
  file_size_bytes?: number; // 可选，因为可能不存在
  file_origin?: string; // 可选
  created_at?: string; // 可选
  updated_at?: string; // 可选
  folder_id?: number; // 可选
  file_id: string; // 用于文档检索的ID
  document_id?: string; // 索引后的文档ID
  is_public?: boolean; // 可选
  cc_pair_id?: number; // connector_credential_pair ID
}

export interface UploadFileResponse {
  id: number;
  name: string;
  size: number;
  content_type: string;
  created_at: string;
  file_id: string;
}

export interface CreateFolderRequest {
  name: string;
  description?: string;
}

export interface CreateFolderResponse {
  id: number;
  name: string;
  description: string;
  created_at: string;
  user_id: number;
  display_priority?: number;
}

// 根据 onyx/web 的实现，API 返回的是 Record<number, boolean>
export interface IndexingStatusResponse {
  [fileId: number]: boolean; // 文件ID -> 是否已索引
}

// API错误处理
export class UserDocumentAPIError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = 'UserDocumentAPIError';
  }
}

// 用户文档API类
export class UserDocumentAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = APP_CONFIG.apiBaseUrl;
  }

  // 获取API headers
  private getHeaders(): HeadersInit {
    return {
      'Content-Type': 'application/json',
      // 如果需要认证，可以在这里添加
    };
  }

  // 处理API响应
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorText = await response.text();
      throw new UserDocumentAPIError(
        `API Error: ${response.status} - ${errorText}`,
        response.status
      );
    }
    return response.json();
  }

  // 获取用户文件夹列表
  async getFolders(): Promise<UserFolder[]> {
    try {
      const url = `${this.baseUrl}/user/folder`;
      console.log('🌐 API请求文件夹列表:', url);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(),
      });
      
      console.log('📡 API响应状态:', response.status, response.statusText);
      const data = await this.handleResponse<UserFolder[] | { folders: UserFolder[] }>(response);
      console.log('📦 API返回数据:', data);
      
      // 处理两种可能的响应格式：直接数组或包装对象
      if (Array.isArray(data)) {
        console.log('📊 API返回直接数组格式，文件夹数量:', data.length);
        return data;
      } else if (data && typeof data === 'object' && 'folders' in data) {
        console.log('📊 API返回包装对象格式，文件夹数量:', data.folders?.length || 0);
        return data.folders || [];
      } else {
        console.warn('⚠️ API返回了未预期的数据格式:', data);
        return [];
      }
    } catch (error) {
      console.error('❌ API获取文件夹失败:', error);
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to fetch folders: ${error}`);
    }
  }

  // 创建新文件夹
  async createFolder(request: CreateFolderRequest): Promise<CreateFolderResponse> {
    try {
      console.log('API: 创建文件夹请求:', request);
      console.log('API: 请求 URL:', `${this.baseUrl}/user/folder`);
      
      const response = await fetch(`${this.baseUrl}/user/folder`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(request),
      });
      
      console.log('API: 创建文件夹响应状态:', response.status);
      const result = await this.handleResponse<CreateFolderResponse>(response);
      console.log('API: 创建文件夹响应数据:', result);
      return result;
    } catch (error) {
      console.error('API: 创建文件夹错误:', error);
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to create folder: ${error}`);
    }
  }

  // 删除文件夹
  async deleteFolder(folderId: number): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/user/folder/${folderId}`, {
        method: 'DELETE',
        headers: this.getHeaders(),
      });
      
      if (!response.ok) {
        throw new UserDocumentAPIError(
          `Failed to delete folder: ${response.status}`,
          response.status
        );
      }
    } catch (error) {
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to delete folder: ${error}`);
    }
  }

  // 获取文件夹中的文件
  async getFolderFiles(folderId: number): Promise<UserFile[]> {
    try {
      const response = await fetch(`${this.baseUrl}/user/folder/${folderId}`, {
        method: 'GET',
        headers: this.getHeaders(),
      });
      
      const data = await this.handleResponse<{ files: UserFile[] }>(response);
      return data.files || [];
    } catch (error) {
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to fetch folder files: ${error}`);
    }
  }

  // 上传文件到文件夹
  async uploadFilesToFolder(files: File[], folderId: number): Promise<UploadFileResponse[]> {
    try {
      const formData = new FormData();
      
      files.forEach((file) => {
        formData.append('files', file);
      });
      formData.append('folder_id', folderId.toString());

      const response = await fetch(`${this.baseUrl}/user/file/upload`, {
        method: 'POST',
        body: formData,
        // 不设置Content-Type，让浏览器自动设置multipart/form-data boundary
      });
      
      const data = await this.handleResponse<{ files: UploadFileResponse[] }>(response);
      return data.files || [];
    } catch (error) {
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to upload files: ${error}`);
    }
  }

  // 删除文件
  async deleteFile(fileId: number): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/user/file/${fileId}`, {
        method: 'DELETE',
        headers: this.getHeaders(),
      });
      
      if (!response.ok) {
        throw new UserDocumentAPIError(
          `Failed to delete file: ${response.status}`,
          response.status
        );
      }
    } catch (error) {
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to delete file: ${error}`);
    }
  }

  // 获取文件索引状态
  async getIndexingStatus(userFileIds: number[]): Promise<IndexingStatusResponse> {
    try {
      // 使用 GET 方法，通过查询参数传递 file_ids (integer IDs)
      const queryParams = userFileIds.map(id => `file_ids=${id}`).join('&');
      const url = `${this.baseUrl}/user/file/indexing-status?${queryParams}`;
      
      console.log('API: 获取文件索引状态，URL:', url);
      console.log('API: 文件ID列表:', userFileIds);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(),
      });
      
      console.log('API: 文件索引状态响应状态:', response.status);
      const result = await this.handleResponse<IndexingStatusResponse>(response);
      console.log('API: 文件索引状态响应数据:', result);
      console.log('API: 响应数据类型:', typeof result);
      console.log('API: 响应数据键值对:', Object.entries(result));
      return result;
    } catch (error) {
      console.error('API: 获取文件索引状态错误:', error);
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to get indexing status: ${error}`);
    }
  }

  // 重新索引文件
  async reindexFile(fileId: number): Promise<void> {
    try {
      console.log('API: 重新索引文件:', fileId);
      const response = await fetch(`${this.baseUrl}/user/file/reindex`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ file_id: fileId }),
      });
      
      console.log('API: 重新索引响应状态:', response.status);
      if (!response.ok) {
        throw new UserDocumentAPIError(
          `Failed to reindex file: ${response.status}`,
          response.status
        );
      }
    } catch (error) {
      console.error('API: 重新索引错误:', error);
      if (error instanceof UserDocumentAPIError) {
        throw error;
      }
      throw new UserDocumentAPIError(`Failed to reindex file: ${error}`);
    }
  }

  // 生成随机文件夹名称
  generateRandomFolderName(): string {
    const adjectives = [
      '智能', '高效', '创新', '灵活', '强大', '精准', '快速', '稳定',
      '可靠', '优雅', '简洁', '清晰', '专业', '实用', '便捷', '先进'
    ];
    
    const nouns = [
      '文档库', '知识库', '资料库', '档案室', '信息库', '数据库',
      '文件夹', '资源库', '素材库', '工具箱', '智囊团', '宝库'
    ];
    
    const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    const now = new Date();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    
    const formattedHours = hours.toString().padStart(2, '0');
    const formattedMinutes = minutes.toString().padStart(2, '0');
    
    const timestamp = `${month}/${day} ${formattedHours}:${formattedMinutes}`;
    
    return `${adjective}${noun} (${timestamp})`;
  }
}

// 创建单例实例
export const userDocumentAPI = new UserDocumentAPI();

// 便捷的导出函数
export const getUserFolders = () => userDocumentAPI.getFolders();
export const createUserFolder = (request: CreateFolderRequest) => userDocumentAPI.createFolder(request);
export const deleteUserFolder = (folderId: number) => userDocumentAPI.deleteFolder(folderId);
export const getFolderFiles = (folderId: number) => userDocumentAPI.getFolderFiles(folderId);
export const uploadFilesToFolder = (files: File[], folderId: number) => userDocumentAPI.uploadFilesToFolder(files, folderId);
export const deleteUserFile = (fileId: number) => userDocumentAPI.deleteFile(fileId);
export const getFileIndexingStatus = (userFileIds: number[]) => userDocumentAPI.getIndexingStatus(userFileIds);
export const reindexUserFile = (fileId: number) => userDocumentAPI.reindexFile(fileId);
export const generateRandomFolderName = () => userDocumentAPI.generateRandomFolderName(); 