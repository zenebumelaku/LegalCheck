import { apiRequest } from '../lib/api-client';

export interface BackendDocumentItem {
  id: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  document_type?: string;
  processing_status: string;
  created_at: string;
  chunks_created?: number;
}

export interface DocumentUploadResult extends BackendDocumentItem {
  extracted_characters: number;
  chunks_created: number;
  warnings: string[];
}

export interface DocumentListResult {
  items: BackendDocumentItem[];
  limit: number;
  offset: number;
}

export class DocumentService {
  static async uploadDocument(file: File): Promise<DocumentUploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    return apiRequest<DocumentUploadResult>('/api/v1/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  static async listDocuments(limit = 50, offset = 0): Promise<DocumentListResult> {
    return apiRequest<DocumentListResult>('/api/v1/documents', {
      params: { limit, offset },
    });
  }

  static async deleteDocument(documentId: string): Promise<void> {
    await apiRequest<void>(`/api/v1/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
    });
  }
}
