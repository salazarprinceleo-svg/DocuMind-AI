import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import type {
  KeyboardEvent,
  MouseEvent,
} from "react";

import {
  Bot,
  FileText,
  MessageSquare,
  Plus,
  Send,
  Trash2,
  User,
} from "lucide-react";

import {
  createChatSession,
  deleteChatSession,
  getChatHistory,
  getChatSessions,
  getDocuments,
  sendChatMessage,
  type ChatMessageResponse,
  type ChatSession,
  type DocumentResponse,
} from "../services/api";

import {
  getSettings,
  SETTINGS_CHANGED_EVENT,
  type AppSettings,
} from "../services/settings";

import "./AIChat.css";

type AIChatProps = {
  onOpenDocument?: (documentId: number) => void;
};

/* =========================================================
   HELPERS
========================================================= */

const formatDate = (value: string): string => {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

const isProcessedDocument = (
  document: DocumentResponse,
): boolean => {
  return (
    document.processing_status !== "pending" &&
    (document.page_count ?? 0) > 0
  );
};

/* =========================================================
   COMPONENT
========================================================= */

export default function AIChat({
  onOpenDocument,
}: AIChatProps) {
  /* =======================================================
     STATE
  ======================================================= */

  const [documents, setDocuments] =
    useState<DocumentResponse[]>([]);

  const [selectedDocuments, setSelectedDocuments] =
    useState<number[]>([]);

  const [sessions, setSessions] =
    useState<ChatSession[]>([]);

  const [sessionId, setSessionId] =
    useState<number | null>(null);

  const [messages, setMessages] =
    useState<ChatMessageResponse[]>([]);

  const [message, setMessage] =
    useState("");

  const [sending, setSending] =
    useState(false);

  const [loading, setLoading] =
    useState(true);

  const [loadingHistory, setLoadingHistory] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [settings, setSettings] =
    useState<AppSettings>(getSettings());

  const messagesEndRef =
    useRef<HTMLDivElement | null>(null);

  /* =======================================================
     SETTINGS
  ======================================================= */

  useEffect(() => {
    const handleSettingsChange = () => {
      setSettings(getSettings());
    };

    window.addEventListener(
      SETTINGS_CHANGED_EVENT,
      handleSettingsChange,
    );

    return () => {
      window.removeEventListener(
        SETTINGS_CHANGED_EVENT,
        handleSettingsChange,
      );
    };
  }, []);

  /* =======================================================
     LOAD DOCUMENTS
  ======================================================= */

  const loadDocuments = useCallback(async () => {
    try {
      const result = await getDocuments();

      setDocuments(
        result.filter(isProcessedDocument),
      );
    } catch (err) {
      console.error(
        "Unable to load documents:",
        err,
      );
    }
  }, []);

  /* =======================================================
     LOAD CHAT SESSIONS
  ======================================================= */

  const loadSessions = useCallback(async () => {
    try {
      const result = await getChatSessions();

      setSessions(result);
    } catch (err) {
      console.error(
        "Unable to load chat sessions:",
        err,
      );
    }
  }, []);

  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {
    const initialize = async () => {
      setLoading(true);

      try {
        await Promise.all([
          loadDocuments(),
          loadSessions(),
        ]);
      } finally {
        setLoading(false);
      }
    };

    void initialize();
  }, [
    loadDocuments,
    loadSessions,
  ]);

  /* =======================================================
     AUTO REFRESH DOCUMENTS
  ======================================================= */

  useEffect(() => {
    if (!settings.autoRefresh) {
      return;
    }

    const interval = window.setInterval(() => {
      void loadDocuments();
    }, 30000);

    return () => {
      window.clearInterval(interval);
    };
  }, [
    settings.autoRefresh,
    loadDocuments,
  ]);

  /* =======================================================
     SCROLL TO BOTTOM
  ======================================================= */

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, sending]);

  /* =======================================================
     CREATE NEW CHAT
  ======================================================= */

  const createNewChat = useCallback(async () => {
    try {
      setError(null);

      const session =
        await createChatSession("New Chat");

      setSessions((previous) => [
        session,
        ...previous,
      ]);

      setSessionId(session.id);
      setMessages([]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to create a new chat.",
      );
    }
  }, []);

  /* =======================================================
     CREATE INITIAL SESSION
  ======================================================= */

  useEffect(() => {
    if (
      loading ||
      sessionId !== null
    ) {
      return;
    }

    void createNewChat();
  }, [
    loading,
    sessionId,
    createNewChat,
  ]);

  /* =======================================================
     LOAD HISTORY
  ======================================================= */

  const loadHistory = useCallback(
    async (selectedSessionId: number) => {
      setLoadingHistory(true);
      setError(null);

      try {
        const result =
          await getChatHistory(
            selectedSessionId,
          );

        setSessionId(
          selectedSessionId,
        );

        setMessages(
          result.messages,
        );
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load chat history.",
        );
      } finally {
        setLoadingHistory(false);
      }
    },
    [],
  );

  /* =======================================================
     DOCUMENT SELECTION
  ======================================================= */

  const toggleDocument = (
    documentId: number,
  ) => {
    setSelectedDocuments(
      (previous) => {
        if (
          previous.includes(
            documentId,
          )
        ) {
          return previous.filter(
            (id) =>
              id !== documentId,
          );
        }

        return [
          ...previous,
          documentId,
        ];
      },
    );
  };

  const selectAllDocuments = () => {
    setSelectedDocuments(
      documents.map(
        (document) =>
          document.id,
      ),
    );
  };

  const clearSelectedDocuments = () => {
    setSelectedDocuments([]);
  };

  /* =======================================================
     SEND MESSAGE
  ======================================================= */

  const handleSend = async () => {
    const trimmedMessage =
      message.trim();

    if (
      !trimmedMessage ||
      sending ||
      sessionId === null
    ) {
      return;
    }

    const currentSettings =
      getSettings();

    setError(null);

    if (
      selectedDocuments.length === 0 &&
      !currentSettings.useGeneralKnowledge
    ) {
      setError(
        "Please select at least one document, or enable Use general knowledge in Settings.",
      );

      return;
    }

    setSending(true);

    const temporaryUserMessage:
      ChatMessageResponse = {
      id: Date.now(),
      role: "user",
      content: trimmedMessage,
      created_at:
        new Date().toISOString(),
    };

    setMessages(
      (previous) => [
        ...previous,
        temporaryUserMessage,
      ],
    );

    setMessage("");

    try {
      const result =
        await sendChatMessage(
          sessionId,
          trimmedMessage,
          selectedDocuments,
          {
            responseStyle:
              currentSettings.responseStyle,

            showSources:
              currentSettings.showSources,

            sourceCount:
              Number(
                currentSettings.sourceCount,
              ),

            useGeneralKnowledge:
              currentSettings.useGeneralKnowledge,

            saveChatHistory:
              currentSettings.saveChatHistory,
          },
        );

      setMessages(
        (previous) => [
          ...previous,
          result.message,
        ],
      );

      if (
        currentSettings.saveChatHistory
      ) {
        await loadSessions();
      }
    } catch (err) {
      setMessages(
        (previous) =>
          previous.filter(
            (item) =>
              item.id !==
              temporaryUserMessage.id,
          ),
      );

      setError(
        err instanceof Error
          ? err.message
          : "Unable to send your message.",
      );
    } finally {
      setSending(false);
    }
  };

  /* =======================================================
     KEYBOARD HANDLING
  ======================================================= */

  const handleKeyDown = (
    event: KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      settings.enterToSend
    ) {
      event.preventDefault();

      if (!sending) {
        void handleSend();
      }
    }
  };

  /* =======================================================
     DELETE CHAT
  ======================================================= */

  const handleDeleteChat = async (
    event: MouseEvent,
    selectedSessionId: number,
  ) => {
    event.stopPropagation();

    if (
      settings.confirmClearChat
    ) {
      const confirmed =
        window.confirm(
          "Delete this chat?",
        );

      if (!confirmed) {
        return;
      }
    }

    try {
      await deleteChatSession(
        selectedSessionId,
      );

      const remaining =
        sessions.filter(
          (session) =>
            session.id !==
            selectedSessionId,
        );

      setSessions(
        remaining,
      );

      if (
        selectedSessionId ===
        sessionId
      ) {
        if (
          remaining.length > 0
        ) {
          await loadHistory(
            remaining[0].id,
          );
        } else {
          await createNewChat();
        }
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to delete chat.",
      );
    }
  };

  /* =======================================================
     SELECTED DOCUMENT COUNT
  ======================================================= */

  const selectedDocumentCount =
    selectedDocuments.length;

  /* =======================================================
     EMPTY STATE
  ======================================================= */

  const emptyStateTitle =
    selectedDocumentCount === 0
      ? settings.useGeneralKnowledge
        ? "Ask a general question"
        : "Select a document"
      : "Start a conversation";

  const emptyStateText =
    selectedDocumentCount === 0
      ? settings.useGeneralKnowledge
        ? "You can ask DocuMind a general question, or select documents if you want document-based answers."
        : "Choose one or more documents from the panel before asking a question."
      : "Ask something about your selected documents.";

  /* =======================================================
     LOADING
  ======================================================= */

  if (loading) {
    return (
      <div className="ai-chat-page">
        <div className="ai-chat-loading">
          <div className="loading-spinner" />

          <span>
            Loading AI Assistant...
          </span>
        </div>
      </div>
    );
  }

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="ai-chat-page">

      {/* ==================================================
          CHAT HISTORY
      ================================================== */}

      <aside className="ai-chat-sidebar">
        <div className="ai-chat-sidebar-header">
          <div>
            <h2>
              Chat History
            </h2>

            <span>
              {sessions.length}{" "}
              {sessions.length === 1
                ? "conversation"
                : "conversations"}
            </span>
          </div>

          <button
            type="button"
            className="new-chat-button"
            onClick={() =>
              void createNewChat()
            }
            title="New chat"
            aria-label="Create new chat"
          >
            <Plus size={17} />
          </button>
        </div>

        <div className="chat-session-list">
          {sessions.length === 0 ? (
            <div className="chat-sidebar-empty">
              <MessageSquare
                size={24}
              />

              <span>
                No conversations yet.
              </span>
            </div>
          ) : (
            sessions.map(
              (session) => (
                <div
                  key={session.id}
                  className={`chat-session ${
                    session.id ===
                    sessionId
                      ? "active"
                      : ""
                  }`}
                  role="button"
                  tabIndex={0}
                  onClick={() =>
                    void loadHistory(
                      session.id,
                    )
                  }
                  onKeyDown={(
                    event,
                  ) => {
                    if (
                      event.key ===
                        "Enter" ||
                      event.key ===
                        " "
                    ) {
                      event.preventDefault();

                      void loadHistory(
                        session.id,
                      );
                    }
                  }}
                >
                  <div className="chat-session-main">
                    <MessageSquare
                      size={15}
                    />

                    <div>
                      <strong>
                        {session.title}
                      </strong>

                      <small>
                        {formatDate(
                          session.updated_at,
                        )}
                      </small>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="chat-session-delete"
                    onClick={(
                      event,
                    ) =>
                      void handleDeleteChat(
                        event,
                        session.id,
                      )
                    }
                    title="Delete chat"
                    aria-label={`Delete ${session.title}`}
                  >
                    <Trash2
                      size={14}
                    />
                  </button>
                </div>
              ),
            )
          )}
        </div>
      </aside>

      {/* ==================================================
          MAIN CHAT
      ================================================== */}

      <main className="ai-chat-main">

        <header className="ai-chat-header">
          <div>
            <h1>
              Your Personal Assistant
            </h1>

            <p>
              Ask questions about your
              documents
            </p>
          </div>
        </header>

        {error && (
          <div className="ai-chat-error">
            <span>
              {error}
            </span>

            <button
              type="button"
              onClick={() =>
                setError(null)
              }
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        )}

        <div className="ai-chat-workspace">

          {/* ==================================================
              CHAT AREA
          ================================================== */}

          <section className="chat-area">

            {/* ONLY THIS AREA SCROLLS */}
            <div className="messages">
              {loadingHistory ? (
                <div className="messages-empty">
                  <div className="loading-spinner" />

                  <span>
                    Loading conversation...
                  </span>
                </div>
              ) : messages.length === 0 ? (
                <div className="messages-empty">
                  <div className="empty-icon">
                    <Bot size={30} />
                  </div>

                  <h3>
                    {emptyStateTitle}
                  </h3>

                  <p>
                    {emptyStateText}
                  </p>
                </div>
              ) : (
                messages.map(
                  (chatMessage) => {
                    const isUser =
                      chatMessage.role ===
                      "user";

                    return (
                      <div
                        key={`${chatMessage.id}-${chatMessage.created_at}`}
                        className={`message-row ${
                          isUser
                            ? "user"
                            : "assistant"
                        }`}
                      >
                        <div className="message-avatar">
                          {isUser ? (
                            <User
                              size={16}
                            />
                          ) : (
                            <Bot
                              size={16}
                            />
                          )}
                        </div>

                        <div className="message-content">
                          <div className="message-bubble">
                            <div className="message-text">
                              {chatMessage.content}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  },
                )
              )}

              {sending && (
                <div className="message-row assistant">
                  <div className="message-avatar">
                    <Bot size={16} />
                  </div>

                  <div className="message-content">
                    <div className="message-bubble typing">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </div>
              )}

              <div
                ref={messagesEndRef}
              />
            </div>

            {/* ==================================================
                STICKY CHAT INPUT
            ================================================== */}

            <div className="chat-input-area">
              <textarea
                value={message}
                onChange={(
                  event,
                ) =>
                  setMessage(
                    event.target.value,
                  )
                }
                onKeyDown={
                  handleKeyDown
                }
                disabled={
                  sending ||
                  (
                    selectedDocuments.length ===
                      0 &&
                    !settings.useGeneralKnowledge
                  )
                }
                placeholder={
                  selectedDocuments.length ===
                  0
                    ? settings.useGeneralKnowledge
                      ? "Ask a general question..."
                      : "Select a document first..."
                    : "Ask something about your documents..."
                }
                rows={3}
              />

              <div className="chat-input-footer">
                <div className="input-status">
                  {sending
                    ? "AI is thinking..."
                    : selectedDocuments.length > 0
                      ? `${selectedDocumentCount} document${
                          selectedDocumentCount === 1
                            ? ""
                            : "s"
                        } selected`
                      : settings.useGeneralKnowledge
                        ? "General knowledge enabled"
                        : "Select a document"}
                </div>

                <button
                  type="button"
                  className="send-message-button"
                  onClick={() =>
                    void handleSend()
                  }
                  disabled={
                    sending ||
                    !message.trim() ||
                    (
                      selectedDocuments.length ===
                        0 &&
                      !settings.useGeneralKnowledge
                    )
                  }
                >
                  <Send size={16} />

                  <span>
                    {sending
                      ? "Sending..."
                      : "Send"}
                  </span>
                </button>
              </div>
            </div>
          </section>

          {/* ==================================================
              DOCUMENT SELECTOR
          ================================================== */}

          <aside className="document-selector">

            <div className="document-selector-header">
              <div>
                <h3>
                  Documents
                </h3>

                <span>
                  Select files for context
                </span>
              </div>
            </div>

            <div className="document-selector-actions">
              <button
                type="button"
                onClick={
                  selectAllDocuments
                }
                disabled={
                  documents.length === 0
                }
              >
                Select all
              </button>

              <button
                type="button"
                onClick={
                  clearSelectedDocuments
                }
                disabled={
                  selectedDocuments.length ===
                  0
                }
              >
                Clear
              </button>
            </div>

            <div className="selected-document-count">
              <strong>
                {selectedDocumentCount}
              </strong>

              <span>
                selected
              </span>
            </div>

            <div className="document-selector-list">
              {documents.length === 0 ? (
                <div className="document-selector-empty">
                  <FileText
                    size={28}
                  />

                  <strong>
                    No processed documents
                  </strong>

                  <span>
                    Upload and process a document
                    before using it for context.
                  </span>
                </div>
              ) : (
                documents.map(
                  (document) => {
                    const selected =
                      selectedDocuments.includes(
                        document.id,
                      );

                    return (
                      <label
                        key={document.id}
                        className={`document-selector-item ${
                          selected
                            ? "selected"
                            : ""
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={
                            selected
                          }
                          onChange={() =>
                            toggleDocument(
                              document.id,
                            )
                          }
                        />

                        <div className="document-checkbox">
                          {selected
                            ? "✓"
                            : ""}
                        </div>

                        <div className="document-selector-info">
                          <strong>
                            {document.filename}
                          </strong>

                          <span>
                            {document.page_count}{" "}
                            {document.page_count ===
                            1
                              ? "page"
                              : "pages"}
                          </span>
                        </div>

                        {onOpenDocument && (
                          <button
                            type="button"
                            className="document-open-button"
                            onClick={(
                              event,
                            ) => {
                              event.preventDefault();
                              event.stopPropagation();

                              onOpenDocument(
                                document.id,
                              );
                            }}
                          >
                            Open
                          </button>
                        )}
                      </label>
                    );
                  },
                )
              )}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
