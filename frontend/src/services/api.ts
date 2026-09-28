const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/* =========================================================
   Document Types
========================================================= */

export interface DocumentResponse {
  id: number;
  filename: string;
  stored_filename: string;
  page_count: number;
  text_length: number;
  chunk_count: number;
  uploaded_at: string;
  processing_status?: "pending" | "processed";
  file_available?: boolean;
}

export interface DocumentStats {
  total_documents: number;
  total_pages: number;
  total_chunks: number;
}

/* =========================================================
   Chat Types
========================================================= */

export type ChatResponseStyle =
  | "concise"
  | "balanced"
  | "detailed";

export interface ChatSource {
  document_id: number;
  filename: string;
  page_number: number | null;
  chunk_index: number | null;
  score: number | null;
}

export interface ChatMessageResponse {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  session_id: number;
  message: ChatMessageResponse;
  sources: ChatSource[];
}

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatHistoryResponse {
  session: ChatSession;
  messages: ChatMessageResponse[];
}

/* =========================================================
   Send Chat Options
========================================================= */

export interface SendChatMessageOptions {
  responseStyle?: ChatResponseStyle;
  showSources?: boolean;
  sourceCount?: number;

  /*
   * When true, Ollama can answer using general knowledge
   * when the selected documents do not contain the answer.
   */
  useGeneralKnowledge?: boolean;

  /*
   * When false, new messages are not saved to chat history.
   */
  saveChatHistory?: boolean;
}

/* =========================================================
   Generic Helpers
========================================================= */

async function parseResponse(
  response: Response,
): Promise<unknown> {
  const contentType =
    response.headers.get("content-type") || "";

  if (
    contentType.includes(
      "application/json",
    )
  ) {
    return response.json();
  }

  return response.text();
}

async function handleResponse<T>(
  response: Response,
): Promise<T> {
  const data =
    await parseResponse(response);

  if (!response.ok) {
    let message =
      "Something went wrong.";

    if (
      typeof data === "string" &&
      data.trim()
    ) {
      message = data;
    } else if (
      typeof data === "object" &&
      data !== null &&
      "detail" in data
    ) {
      const detail = (
        data as {
          detail?: unknown;
        }
      ).detail;

      message =
        typeof detail === "string"
          ? detail
          : JSON.stringify(detail);
    } else if (
      typeof data === "object" &&
      data !== null &&
      "message" in data
    ) {
      const responseMessage = (
        data as {
          message?: unknown;
        }
      ).message;

      if (
        typeof responseMessage ===
        "string"
      ) {
        message = responseMessage;
      }
    }

    throw new Error(message);
  }

  return data as T;
}

/* =========================================================
   Documents
========================================================= */

export async function getDocuments(): Promise<
  DocumentResponse[]
> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents`,
  );

  return handleResponse<
    DocumentResponse[]
  >(response);
}

export async function getDocument(
  documentId: number,
): Promise<DocumentResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}`,
  );

  return handleResponse<DocumentResponse>(
    response,
  );
}

export async function getDocumentStats(): Promise<DocumentStats> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/stats`,
  );

  return handleResponse<DocumentStats>(
    response,
  );
}

export async function uploadDocument(
  file: File,
  autoProcess = true,
  keepFile = true,
): Promise<DocumentResponse> {
  const formData = new FormData();

  formData.append(
    "file",
    file,
  );

  formData.append(
    "auto_process",
    String(autoProcess),
  );

  formData.append(
    "keep_file",
    String(keepFile),
  );

  const response = await fetch(
    `${API_BASE_URL}/api/documents/upload`,
    {
      method: "POST",
      body: formData,
    },
  );

  return handleResponse<DocumentResponse>(
    response,
  );
}

export async function processDocument(
  documentId: number,
  keepFile = true,
): Promise<DocumentResponse> {
  const formData = new FormData();

  formData.append(
    "keep_file",
    String(keepFile),
  );

  const response = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/process`,
    {
      method: "POST",
      body: formData,
    },
  );

  return handleResponse<DocumentResponse>(
    response,
  );
}

export async function deleteDocument(
  documentId: number,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}`,
    {
      method: "DELETE",
    },
  );

  await handleResponse<unknown>(
    response,
  );
}

export async function downloadDocument(
  documentId: number,
): Promise<Blob> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/download`,
  );

  if (!response.ok) {
    const data =
      await parseResponse(response);

    let message =
      "Unable to download document.";

    if (
      typeof data === "string" &&
      data.trim()
    ) {
      message = data;
    } else if (
      typeof data === "object" &&
      data !== null &&
      "detail" in data
    ) {
      const detail = (
        data as {
          detail?: unknown;
        }
      ).detail;

      message =
        typeof detail === "string"
          ? detail
          : JSON.stringify(detail);
    }

    throw new Error(message);
  }

  return response.blob();
}

/* =========================================================
   Chat Sessions
========================================================= */

export async function createChatSession(
  title = "New Chat",
): Promise<ChatSession> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/sessions`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        title,
      }),
    },
  );

  return handleResponse<ChatSession>(
    response,
  );
}

export async function getChatSessions(): Promise<
  ChatSession[]
> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/sessions`,
  );

  return handleResponse<ChatSession[]>(
    response,
  );
}

export async function getChatHistory(
  sessionId: number,
): Promise<ChatHistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/sessions/${sessionId}`,
  );

  return handleResponse<ChatHistoryResponse>(
    response,
  );
}

export async function deleteChatSession(
  sessionId: number,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/sessions/${sessionId}`,
    {
      method: "DELETE",
    },
  );

  await handleResponse<unknown>(
    response,
  );
}

/* =========================================================
   Send AI Message
========================================================= */

export async function sendChatMessage(
  sessionId: number,
  message: string,
  documentIds: number[],
  options: SendChatMessageOptions = {},
): Promise<ChatResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        document_ids: documentIds,

        response_style:
          options.responseStyle ??
          "balanced",

        show_sources:
          options.showSources ??
          true,

        source_count:
          options.sourceCount ??
          5,

        use_general_knowledge:
          options.useGeneralKnowledge ??
          false,

        save_chat_history:
          options.saveChatHistory ??
          true,
      }),
    },
  );

  return handleResponse<ChatResponse>(
    response,
  );
}

/* =========================================================
   API Base URL
========================================================= */

export {
  API_BASE_URL,
};