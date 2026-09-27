export interface DocumentItem {
  id: number;
  filename: string;
  stored_filename?: string;
  file_path?: string;

  page_count: number;
  text_length: number;

  uploaded_at: string;

  file_size?: number;
  file_extension?: string;

  chunk_count?: number;
  embedding_count?: number;

  processing_status?: "pending" | "processed";
  file_available?: boolean;
}

export interface DocumentResponse {
  id: number;
  filename: string;
  stored_filename?: string;
  file_path?: string;

  page_count: number;
  text_length: number;

  extracted_text?: string | null;

  uploaded_at: string;

  file_size?: number;
  file_extension?: string;

  chunk_count?: number;
  embedding_count?: number;

  processing_status?: "pending" | "processed";
  file_available?: boolean;
}

export interface DocumentDetails extends DocumentResponse {
  extracted_text?: string | null;
  file_size?: number;
  file_extension?: string;
}

export interface UploadResponse {
  id: number;
  filename: string;

  page_count: number;
  text_length: number;

  uploaded_at: string;

  file_size?: number;
  file_extension?: string;

  chunk_count?: number;
  embedding_count?: number;

  processing_status?: "pending" | "processed";
  file_available?: boolean;
}

export interface DocumentUploadResponse {
  message: string;
  document: DocumentResponse;
}

export interface DeleteDocumentResponse {
  message: string;
}