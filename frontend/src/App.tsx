import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import type { ChangeEvent } from "react";

import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import AIChat from "./pages/AIChat";
import Settings from "./pages/Settings";

import Sidebar from "./components/Sidebar";

import {
  getDocumentStats,
  getDocuments,
  uploadDocument,
  downloadDocument,
  type DocumentResponse,
} from "./services/api";

import {
  getSettings,
  SETTINGS_CHANGED_EVENT,
  type AppSettings,
} from "./services/settings";

import type { Page } from "./types/pages";

import "./App.css";

/* =========================================================
   APP
========================================================= */

export default function App() {
  /* =======================================================
     NAVIGATION
  ======================================================= */

  const [currentPage, setCurrentPage] =
    useState<Page>("dashboard");

  /* =======================================================
     DOCUMENTS
  ======================================================= */

  const [documents, setDocuments] =
    useState<DocumentResponse[]>([]);

  const [stats, setStats] = useState({
    total_documents: 0,
    total_pages: 0,
    total_chunks: 0,
  });

  const [isLoading, setIsLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  /* =======================================================
     DOCUMENT SEARCH
  ======================================================= */

  const [documentSearch, setDocumentSearch] =
    useState("");

  /* =======================================================
     UPLOAD STATE
  ======================================================= */

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [isUploading, setIsUploading] =
    useState(false);

  const [uploadError, setUploadError] =
    useState<string | null>(null);

  const [uploadSuccess, setUploadSuccess] =
    useState<string | null>(null);

  const fileInputRef =
    useRef<HTMLInputElement | null>(null);

  /* =======================================================
     UPLOAD PROGRESS
  ======================================================= */

  const [uploadProgress, setUploadProgress] =
    useState(0);

  /* =======================================================
     DOCUMENT VIEWER
  ======================================================= */

  const [viewingDocumentId, setViewingDocumentId] =
    useState<number | null>(null);

  const [viewingDocument, setViewingDocument] =
    useState<DocumentResponse | null>(null);

  /* =======================================================
     SETTINGS
  ======================================================= */

  const [settings, setSettings] =
    useState<AppSettings>(getSettings());

  /* =======================================================
     THEME
  ======================================================= */

  useEffect(() => {
    const applyTheme = () => {
      const currentSettings = getSettings();

      setSettings(currentSettings);

      const theme = currentSettings.theme;

      let resolvedTheme: "light" | "dark";

      if (theme === "system") {
        resolvedTheme =
          window.matchMedia(
            "(prefers-color-scheme: dark)",
          ).matches
            ? "dark"
            : "light";
      } else {
        resolvedTheme = theme;
      }

      document.documentElement.setAttribute(
        "data-theme",
        resolvedTheme,
      );
    };

    applyTheme();

    const handleSettingsChange = () => {
      applyTheme();
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

  const loadDocuments = useCallback(
    async () => {
      try {
        const result = await getDocuments();

        setDocuments(result);
      } catch (err) {
        console.error(
          "Unable to load documents:",
          err,
        );

        throw err;
      }
    },
    [],
  );

  /* =======================================================
     LOAD DASHBOARD STATS
  ======================================================= */

  const loadStats = useCallback(
    async () => {
      try {
        const result =
          await getDocumentStats();

        setStats(result);
      } catch (err) {
        console.error(
          "Unable to load document stats:",
          err,
        );

        throw err;
      }
    },
    [],
  );

  /* =======================================================
     REFRESH EVERYTHING
  ======================================================= */

  const refreshDocuments = useCallback(
    async () => {
      try {
        await Promise.all([
          loadDocuments(),
          loadStats(),
        ]);
      } catch (err) {
        console.error(
          "Unable to refresh documents:",
          err,
        );
      }
    },
    [
      loadDocuments,
      loadStats,
    ],
  );

  /* =======================================================
     INITIAL DATA LOAD
  ======================================================= */

  useEffect(() => {
    const loadInitialData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        await Promise.all([
          loadDocuments(),
          loadStats(),
        ]);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load application data.",
        );
      } finally {
        setIsLoading(false);
      }
    };

    void loadInitialData();
  }, [
    loadDocuments,
    loadStats,
  ]);

  /* =======================================================
     AUTO REFRESH
  ======================================================= */

  useEffect(() => {
    if (!settings.autoRefresh) {
      return;
    }

    const interval =
      window.setInterval(
        () => {
          void refreshDocuments();
        },
        30000,
      );

    return () => {
      window.clearInterval(interval);
    };
  }, [
    settings.autoRefresh,
    refreshDocuments,
  ]);

  /* =======================================================
     FILE SELECTION
  ======================================================= */

  const onFileSelect = (
    event: ChangeEvent<HTMLInputElement>,
  ) => {
    const file =
      event.target.files?.[0] ?? null;

    setUploadError(null);
    setUploadSuccess(null);
    setSelectedFile(file);

    /*
     * Allow selecting the same file again.
     */
    event.target.value = "";
  };

  /* =======================================================
     OPEN FILE PICKER
  ======================================================= */

  const openFilePicker = () => {
    setUploadError(null);
    setUploadSuccess(null);

    fileInputRef.current?.click();
  };

  /* =======================================================
     UPLOAD DOCUMENT
  ======================================================= */

  const handleUpload = async () => {
    if (!selectedFile) {
      /*
       * If the user clicked Upload Document
       * without selecting a file, open the picker.
       */
      openFilePicker();
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const currentSettings =
        getSettings();

      /*
       * The current API does not expose
       * XMLHttpRequest-style upload progress.
       *
       * We still show progress so the user
       * receives visual feedback while the
       * backend is processing the document.
       */
      setUploadProgress(20);

      const result =
        await uploadDocument(
          selectedFile,
          currentSettings.autoProcessUploads,
          currentSettings.keepUploadedFiles,
        );

      setUploadProgress(100);

      if (
        currentSettings.autoProcessUploads
      ) {
        setUploadSuccess(
          `"${result.filename}" uploaded and processed successfully.`,
        );
      } else {
        setUploadSuccess(
          `"${result.filename}" uploaded successfully and is waiting to be processed.`,
        );
      }

      setSelectedFile(null);

      await refreshDocuments();
    } catch (err) {
      console.error(
        "Upload failed:",
        err,
      );

      setUploadError(
        err instanceof Error
          ? err.message
          : "Unable to upload document.",
      );
    } finally {
      setIsUploading(false);

      window.setTimeout(() => {
        setUploadProgress(0);
      }, 500);
    }
  };

  /* =======================================================
     VIEW DOCUMENT
  ======================================================= */

  const handleViewDocument = async (
    documentId: number,
  ) => {
    try {
      setUploadError(null);

      setViewingDocumentId(documentId);
      setViewingDocument(null);

      /*
       * Use the document already stored in state first.
       */
      let found =
        documents.find(
          (item) =>
            item.id === documentId,
        );

      /*
       * If it isn't in the current state,
       * refresh the document list.
       */
      if (!found) {
        const latestDocuments =
          await getDocuments();

        setDocuments(
          latestDocuments,
        );

        found =
          latestDocuments.find(
            (item) =>
              item.id === documentId,
          );
      }

      if (!found) {
        throw new Error(
          "Document could not be found.",
        );
      }

      setViewingDocument(found);
    } catch (err) {
      console.error(
        "Unable to open document:",
        err,
      );

      setViewingDocumentId(null);
      setViewingDocument(null);

      setUploadError(
        err instanceof Error
          ? err.message
          : "Unable to open document.",
      );
    }
  };

  /* =======================================================
     DOWNLOAD DOCUMENT
  ======================================================= */

  const handleDownloadDocument = async (
    documentId: number,
    filename: string,
  ) => {
    try {
      setUploadError(null);

      const blob =
        await downloadDocument(
          documentId,
        );

      const url =
        window.URL.createObjectURL(
          blob,
        );

      const link =
        document.createElement("a");

      link.href = url;
      link.download = filename;

      document.body.appendChild(link);

      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(
        "Unable to download document:",
        err,
      );

      setUploadError(
        err instanceof Error
          ? err.message
          : "Unable to download document.",
      );
    }
  };

  /* =======================================================
     CLOSE DOCUMENT VIEWER
  ======================================================= */

  const closeDocumentViewer = () => {
    setViewingDocumentId(null);
    setViewingDocument(null);
  };

  /* =======================================================
     NAVIGATION
  ======================================================= */

  const handleChangePage = (
    page: Page,
  ) => {
    setCurrentPage(page);

    setUploadError(null);
    setUploadSuccess(null);
  };

  /* =======================================================
     RENDER CURRENT PAGE
  ======================================================= */

  const renderPage = () => {
    switch (currentPage) {
      /* ===================================================
         DASHBOARD
      =================================================== */

      case "dashboard":
        return (
          <Dashboard
            documents={documents}
            stats={stats}
            isLoading={isLoading}
            error={error}
            uploadError={uploadError}
            uploadSuccess={uploadSuccess}
            selectedFile={selectedFile}
            isUploading={isUploading}
            fileInputRef={fileInputRef}
            onFileSelect={onFileSelect}
            onUpload={handleUpload}
            onChangePage={handleChangePage}
            onViewDocument={handleViewDocument}
          />
        );

      /* ===================================================
         DOCUMENTS
      =================================================== */

      case "documents":
        return (
          <Documents
            documents={documents}
            loading={isLoading}
            search={documentSearch}
            onSearch={setDocumentSearch}
            onRefresh={refreshDocuments}
            onViewDocument={handleViewDocument}
            onDownloadDocument={
              handleDownloadDocument
            }
            onUpload={openFilePicker}
          />
        );

      /* ===================================================
         AI CHAT
      =================================================== */

      case "chat":
        return (
          <AIChat
            onOpenDocument={
              handleViewDocument
            }
          />
        );

      /* ===================================================
         SETTINGS
      =================================================== */

      case "settings":
        return (
          <Settings
            apiStatus="Local API"
          />
        );

      default:
        return null;
    }
  };

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="app">

      {/* ==================================================
          SIDEBAR
      ================================================== */}

      <Sidebar
        activePage={currentPage}
        onPageChange={handleChangePage}
        apiStatus="Local"
      />

      {/* ==================================================
          MAIN CONTENT
      ================================================== */}

      <main className="main-content">

        <div className="page-content">

          {/* =================================================
              DASHBOARD INTRO ONLY
              
              Documents, Chat, and Settings no longer
              use the generic page intro.
          ================================================= */}

          {currentPage === "dashboard" && (
            <header className="page-intro">
              <span className="page-eyebrow">
                WORKSPACE OVERVIEW
              </span>

              <h1>
                Your Workspace
              </h1>

              <p>
                Manage your documents, explore
                your knowledge base, and work
                with DocuMind AI in one place.
              </p>
            </header>
          )}

          {/* ================================================
              CURRENT PAGE
          ================================================ */}

          {renderPage()}

        </div>

      </main>

      {/* ==================================================
          UPLOAD OVERLAY
      ================================================== */}

      {isUploading && (
        <div className="upload-overlay">

          <div className="upload-modal">

            <div className="upload-spinner" />

            <h3>
              {settings.autoProcessUploads
                ? "Processing document"
                : "Uploading document"}
            </h3>

            <p>
              {settings.autoProcessUploads
                ? "Extracting text and preparing the document for local AI..."
                : "Saving your document..."}
            </p>

            <div className="upload-progress">

              <div
                className="upload-progress-bar"
                style={{
                  width: `${uploadProgress}%`,
                }}
              />

            </div>

            <span>
              {uploadProgress}%
            </span>

          </div>

        </div>
      )}

      {/* ==================================================
          DOCUMENT VIEWER
      ================================================== */}

      {viewingDocumentId !== null && (
        <div
          className="document-viewer-overlay"
          onClick={(event) => {
            /*
             * Clicking the dark background closes
             * the viewer, but clicking inside the
             * viewer does not.
             */
            if (
              event.target ===
              event.currentTarget
            ) {
              closeDocumentViewer();
            }
          }}
        >

          <div className="document-viewer">

            {/* ============================================
                VIEWER HEADER
            ============================================ */}

            <div className="document-viewer-header">

              <div>

                <h2>
                  {
                    viewingDocument?.filename ??
                    "Document"
                  }
                </h2>

                {viewingDocument && (
                  <div className="document-viewer-meta">

                    {viewingDocument.page_count}{" "}
                    {
                      viewingDocument.page_count ===
                      1
                        ? "page"
                        : "pages"
                    }

                    {" · "}

                    {viewingDocument.chunk_count}{" "}
                    chunks

                  </div>
                )}

              </div>

              <div className="document-viewer-actions">

                {viewingDocument &&
                  viewingDocument.file_available !==
                    false && (
                    <button
                      type="button"
                      className="viewer-download-button"
                      onClick={() =>
                        void handleDownloadDocument(
                          viewingDocument.id,
                          viewingDocument.filename,
                        )
                      }
                    >
                      Download
                    </button>
                  )}

                <button
                  type="button"
                  className="document-viewer-close"
                  onClick={
                    closeDocumentViewer
                  }
                >
                  Close
                </button>

              </div>

            </div>

            {/* ============================================
                VIEWER BODY
            ============================================ */}

            <div className="document-viewer-body">

              {viewingDocument ? (

                <div className="empty-viewer">

                  <FileDocumentIcon />

                  <h3>
                    {
                      viewingDocument.filename
                    }
                  </h3>

                  <p>
                    This document has been
                    processed and is available
                    to DocuMind's local AI for
                    question answering.
                  </p>

                  <div className="viewer-document-info">

                    <div>
                      <span>
                        Pages
                      </span>

                      <strong>
                        {
                          viewingDocument.page_count
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Text
                      </span>

                      <strong>
                        {
                          viewingDocument.text_length
                        }{" "}
                        characters
                      </strong>
                    </div>

                    <div>
                      <span>
                        Chunks
                      </span>

                      <strong>
                        {
                          viewingDocument.chunk_count
                        }
                      </strong>
                    </div>

                  </div>

                  {viewingDocument.file_available ===
                    false && (
                    <p className="viewer-file-unavailable">
                      The original file has been
                      removed, but its processed
                      content is still available
                      to the AI.
                    </p>
                  )}

                </div>

              ) : (

                <div className="empty-viewer">
                  Loading document...
                </div>

              )}

            </div>

          </div>

        </div>
      )}

      {/* ==================================================
          HIDDEN FILE INPUT
      ================================================== */}

      <input
        ref={fileInputRef}
        type="file"
        hidden
        accept=".pdf,.docx,.xlsx,.pptx,.txt"
        onChange={onFileSelect}
      />

    </div>
  );
}

/* =========================================================
   SIMPLE DOCUMENT ICON
========================================================= */

function FileDocumentIcon() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />

      <polyline points="14 2 14 8 20 8" />

      <line
        x1="8"
        y1="13"
        x2="16"
        y2="13"
      />

      <line
        x1="8"
        y1="17"
        x2="16"
        y2="17"
      />

      <line
        x1="8"
        y1="9"
        x2="10"
        y2="9"
      />
    </svg>
  );
}