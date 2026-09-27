import {
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  File,
  FileSpreadsheet,
  FileText,
  FileType,
  Grid2X2,
  List,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type { DocumentItem } from "../types/document";

import {
  deleteDocument,
  processDocument,
} from "../services/api";

import {
  getSettings,
  saveSettings,
} from "../services/settings";

import "./Documents.css";

interface DocumentsProps {
  documents: DocumentItem[];
  loading: boolean;
  search: string;
  onSearch: (value: string) => void;
  onRefresh: () => void;
  onViewDocument: (documentId: number) => void;
  onDownloadDocument: (
    documentId: number,
    filename: string,
  ) => void;
}

type SortOption =
  | "newest"
  | "oldest"
  | "name-asc"
  | "name-desc"
  | "largest"
  | "smallest";

type FileTypeFilter =
  | "all"
  | "pdf"
  | "docx"
  | "xlsx"
  | "pptx"
  | "txt";

/* ============================================================
   FILE HELPERS
   ============================================================ */

const getFileExtension = (
  filename: string,
): string => {
  const parts = filename.toLowerCase().split(".");

  if (parts.length <= 1) {
    return "";
  }

  return parts.pop() || "";
};

const getFileIcon = (filename: string) => {
  const extension = getFileExtension(filename);

  switch (extension) {
    case "pdf":
      return FileType;

    case "docx":
      return FileText;

    case "xlsx":
      return FileSpreadsheet;

    case "pptx":
      return FileText;

    case "txt":
      return FileText;

    default:
      return File;
  }
};

const getFileIconClass = (
  filename: string,
): string => {
  const extension = getFileExtension(filename);

  switch (extension) {
    case "pdf":
      return "pdf";

    case "docx":
      return "docx";

    case "xlsx":
      return "xlsx";

    case "pptx":
      return "pptx";

    case "txt":
      return "txt";

    default:
      return "other";
  }
};

const getFileTypeLabel = (
  filename: string,
): string => {
  const extension = getFileExtension(filename);

  switch (extension) {
    case "pdf":
      return "PDF";

    case "docx":
      return "DOCX";

    case "xlsx":
      return "XLSX";

    case "pptx":
      return "PPTX";

    case "txt":
      return "TXT";

    default:
      return "FILE";
  }
};

/* ============================================================
   PROCESSING HELPERS
   ============================================================ */

const isDocumentPending = (
  document: DocumentItem,
): boolean => {
  if (
    "processing_status" in document &&
    document.processing_status === "pending"
  ) {
    return true;
  }

  if (
    "processing_status" in document &&
    document.processing_status === "processed"
  ) {
    return false;
  }

  return (
    (document.page_count ?? 0) === 0 &&
    (document.chunk_count ?? 0) === 0
  );
};

const isFileAvailable = (
  document: DocumentItem,
): boolean => {
  if (
    "file_available" in document &&
    typeof document.file_available === "boolean"
  ) {
    return document.file_available;
  }

  return (document.file_size ?? 0) > 0;
};

/* ============================================================
   FORMATTERS
   ============================================================ */

const formatFileSize = (
  bytes: number,
): string => {
  if (!bytes || bytes <= 0) {
    return "File unavailable";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  if (bytes < 1024 * 1024 * 1024) {
    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(1)} MB`;
  }

  return `${(
    bytes /
    (1024 * 1024 * 1024)
  ).toFixed(1)} GB`;
};

const formatDate = (
  dateValue?: string,
): string => {
  if (!dateValue) {
    return "Unknown date";
  }

  const date = new Date(dateValue);

  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const getDocumentSize = (
  document: DocumentItem,
): number => {
  return document.file_size ?? 0;
};

/* ============================================================
   COMPONENT
   ============================================================ */

export default function Documents({
  documents,
  loading,
  search,
  onSearch,
  onRefresh,
  onViewDocument,
  onDownloadDocument,
}: DocumentsProps) {
  const [sort, setSort] =
    useState<SortOption>("newest");

  const [
    selectedFileType,
    setSelectedFileType,
  ] = useState<FileTypeFilter>("all");

  const [deletingId, setDeletingId] =
    useState<number | null>(null);

  const [processingId, setProcessingId] =
    useState<number | null>(null);

  const [settings, setSettings] =
    useState(getSettings);

  const [currentPage, setCurrentPage] =
    useState(1);

  /* ============================================================
     SETTINGS SYNC
     ============================================================ */

  useEffect(() => {
    const loadCurrentSettings = () => {
      setSettings(getSettings());
    };

    loadCurrentSettings();

    window.addEventListener(
      "storage",
      loadCurrentSettings,
    );

    window.addEventListener(
      "documind-settings-changed",
      loadCurrentSettings,
    );

    return () => {
      window.removeEventListener(
        "storage",
        loadCurrentSettings,
      );

      window.removeEventListener(
        "documind-settings-changed",
        loadCurrentSettings,
      );
    };
  }, []);

  /* ============================================================
     AUTO REFRESH
     ============================================================ */

  useEffect(() => {
    if (!settings.autoRefresh) {
      return;
    }

    const refreshInterval =
      window.setInterval(() => {
        onRefresh();
      }, 30000);

    return () => {
      window.clearInterval(refreshInterval);
    };
  }, [
    settings.autoRefresh,
    onRefresh,
  ]);

  /* ============================================================
     FILTER + SEARCH + SORT
     ============================================================ */

  const filteredDocuments = useMemo(() => {
    let result = [...documents];

    if (selectedFileType !== "all") {
      result = result.filter(
        (document) =>
          getFileExtension(
            document.filename,
          ) === selectedFileType,
      );
    }

    if (search.trim()) {
      const searchValue =
        search.trim().toLowerCase();

      result = result.filter(
        (document) =>
          document.filename
            .toLowerCase()
            .includes(searchValue),
      );
    }

    result.sort((a, b) => {
      switch (sort) {
        case "oldest":
          return (
            new Date(a.uploaded_at).getTime() -
            new Date(b.uploaded_at).getTime()
          );

        case "name-asc":
          return a.filename.localeCompare(
            b.filename,
          );

        case "name-desc":
          return b.filename.localeCompare(
            a.filename,
          );

        case "largest":
          return (
            getDocumentSize(b) -
            getDocumentSize(a)
          );

        case "smallest":
          return (
            getDocumentSize(a) -
            getDocumentSize(b)
          );

        case "newest":
        default:
          return (
            new Date(b.uploaded_at).getTime() -
            new Date(a.uploaded_at).getTime()
          );
      }
    });

    return result;
  }, [
    documents,
    search,
    selectedFileType,
    sort,
  ]);

  /* ============================================================
     PAGINATION
     ============================================================ */

  const documentsPerPage =
    Number(settings.documentsPerPage) || 20;

  const totalPages = Math.max(
    1,
    Math.ceil(
      filteredDocuments.length /
        documentsPerPage,
    ),
  );

  useEffect(() => {
    setCurrentPage((page) =>
      Math.min(page, totalPages),
    );
  }, [totalPages]);

  const startIndex =
    (currentPage - 1) *
    documentsPerPage;

  const paginatedDocuments =
    filteredDocuments.slice(
      startIndex,
      startIndex + documentsPerPage,
    );

  const showingFrom =
    filteredDocuments.length === 0
      ? 0
      : startIndex + 1;

  const showingTo = Math.min(
    startIndex + documentsPerPage,
    filteredDocuments.length,
  );

  const goToPage = (page: number) => {
    const safePage = Math.max(
      1,
      Math.min(page, totalPages),
    );

    setCurrentPage(safePage);
  };

  useEffect(() => {
    setCurrentPage(1);
  }, [
    search,
    selectedFileType,
    sort,
    settings.documentsPerPage,
  ]);

  /* ============================================================
     FILE COUNTS
     ============================================================ */

  const pdfCount = documents.filter(
    (document) =>
      getFileExtension(
        document.filename,
      ) === "pdf",
  ).length;

  const docxCount = documents.filter(
    (document) =>
      getFileExtension(
        document.filename,
      ) === "docx",
  ).length;

  const xlsxCount = documents.filter(
    (document) =>
      getFileExtension(
        document.filename,
      ) === "xlsx",
  ).length;

  const pptxCount = documents.filter(
    (document) =>
      getFileExtension(
        document.filename,
      ) === "pptx",
  ).length;

  const txtCount = documents.filter(
    (document) =>
      getFileExtension(
        document.filename,
      ) === "txt",
  ).length;

  /* ============================================================
     FILE TYPE FILTER
     ============================================================ */

  const handleFileTypeFilter = (
    type: FileTypeFilter,
  ) => {
    if (type === "all") {
      setSelectedFileType("all");
      return;
    }

    setSelectedFileType(
      selectedFileType === type
        ? "all"
        : type,
    );
  };

  /* ============================================================
     DELETE
     ============================================================ */

  const handleDelete = async (
    document: DocumentItem,
  ) => {
    if (settings.confirmDelete) {
      const confirmed =
        window.confirm(
          `Are you sure you want to delete "${document.filename}"?\n\nThis action cannot be undone.`,
        );

      if (!confirmed) {
        return;
      }
    }

    try {
      setDeletingId(document.id);

      await deleteDocument(document.id);

      if (
        paginatedDocuments.length === 1 &&
        currentPage > 1
      ) {
        setCurrentPage(currentPage - 1);
      }

      onRefresh();
    } catch (error) {
      console.error(
        "Failed to delete document:",
        error,
      );

      window.alert(
        "Could not delete the document. Please try again.",
      );
    } finally {
      setDeletingId(null);
    }
  };

  /* ============================================================
     PROCESS DOCUMENT
     ============================================================ */

  const handleProcess = async (
    document: DocumentItem,
  ) => {
    if (!isDocumentPending(document)) {
      return;
    }

    try {
      setProcessingId(document.id);

      const currentSettings =
        getSettings();

      await processDocument(
        document.id,
        currentSettings.keepUploadedFiles,
      );

      onRefresh();
    } catch (error) {
      console.error(
        "Failed to process document:",
        error,
      );

      window.alert(
        "Could not process the document. Please make sure the original file is still available and try again.",
      );
    } finally {
      setProcessingId(null);
    }
  };

  /* ============================================================
     CHANGE VIEW
     ============================================================ */

  const handleViewChange = (
    view: "list" | "grid",
  ) => {
    const updated = getSettings();

    updated.documentView = view;

    saveSettings(updated);

    setSettings(updated);
  };

  /* ============================================================
     RENDER DOCUMENT CARD
     ============================================================ */

  const renderDocumentCard = (
    document: DocumentItem,
  ) => {
    const Icon = getFileIcon(
      document.filename,
    );

    const iconClass =
      getFileIconClass(
        document.filename,
      );

    const fileType =
      getFileTypeLabel(
        document.filename,
      );

    const isDeleting =
      deletingId === document.id;

    const isProcessing =
      processingId === document.id;

    const pending =
      isDocumentPending(document);

    const fileAvailable =
      isFileAvailable(document);

    return (
      <article
        key={document.id}
        className={`document-card ${
          settings.documentView === "list"
            ? "document-card-list"
            : "document-card-grid"
        } ${
          pending
            ? "document-card-pending"
            : ""
        }`}
      >
        <div className="document-card-main">
          <div className="document-card-header">
            <div
              className={`document-file-icon ${iconClass}`}
            >
              <Icon size={26} />
            </div>

            <div className="document-card-badges">
              <span className="document-file-badge">
                {fileType}
              </span>

              {pending ? (
                <span className="document-processing-badge">
                  Pending
                </span>
              ) : (
                <span className="document-processed-badge">
                  Ready
                </span>
              )}
            </div>
          </div>

          <div className="document-card-content">
            <h3 title={document.filename}>
              {document.filename}
            </h3>

            <div className="document-meta">
              <span>
                {formatFileSize(
                  getDocumentSize(document),
                )}
              </span>

              <span>•</span>

              {pending ? (
                <span>Not processed</span>
              ) : (
                <span>
                  {document.page_count ?? 0}{" "}
                  {(document.page_count ?? 0) === 1
                    ? "page"
                    : "pages"}
                </span>
              )}
            </div>

            <div className="document-uploaded">
              Uploaded{" "}
              {formatDate(
                document.uploaded_at,
              )}
            </div>

            {pending && (
              <div className="document-pending-message">
                This document is waiting to be
                processed before it can be used
                by the AI.
              </div>
            )}

            {!pending && !fileAvailable && (
              <div className="document-file-removed-message">
                Original file removed. Document
                data is still available to AI.
              </div>
            )}
          </div>
        </div>

        <div className="document-card-actions">
          {pending ? (
            <button
              type="button"
              className="document-process-button"
              onClick={() =>
                handleProcess(document)
              }
              disabled={
                isDeleting ||
                isProcessing
              }
            >
              {isProcessing ? (
                <Loader2
                  size={16}
                  className="spin"
                />
              ) : (
                <RefreshCw size={16} />
              )}

              <span>
                {isProcessing
                  ? "Processing..."
                  : "Process"}
              </span>
            </button>
          ) : (
            <button
              type="button"
              className="document-preview-button"
              onClick={() =>
                onViewDocument(document.id)
              }
              disabled={
                isDeleting ||
                isProcessing
              }
            >
              <Eye size={16} />

              <span>Preview</span>
            </button>
          )}

          <button
            type="button"
            className="document-download-button"
            onClick={() =>
              onDownloadDocument(
                document.id,
                document.filename,
              )
            }
            disabled={
              isDeleting ||
              isProcessing ||
              pending ||
              !fileAvailable
            }
            title={
              pending
                ? "Process the document first"
                : !fileAvailable
                  ? "Original file is no longer available"
                  : "Download document"
            }
          >
            <Download size={16} />

            <span>
              {!fileAvailable && !pending
                ? "Unavailable"
                : "Download"}
            </span>
          </button>

          <button
            type="button"
            className="document-delete-button"
            onClick={() =>
              handleDelete(document)
            }
            disabled={
              isDeleting ||
              isProcessing
            }
          >
            {isDeleting ? (
              <Loader2
                size={16}
                className="spin"
              />
            ) : (
              <Trash2 size={16} />
            )}

            <span>
              {isDeleting
                ? "Deleting..."
                : "Delete"}
            </span>
          </button>
        </div>
      </article>
    );
  };

  /* ============================================================
     RENDER
     ============================================================ */

  return (
    <div className="documents-page">
      {/* HEADER */}

      <header className="documents-header">
        <div className="documents-header-content">
          <p className="eyebrow">
            DOCUMENT LIBRARY
          </p>

          <h1>Your Documents</h1>

          <p className="subtitle">
            Keep your files organized in one
            place. Preview, download, process,
            or remove documents whenever you need.
          </p>
        </div>
      </header>

      {/* TOOLBAR */}

      <div className="documents-toolbar">
        <div className="documents-search">
          <Search size={18} />

          <input
            type="text"
            value={search}
            onChange={(event) =>
              onSearch(event.target.value)
            }
            placeholder="Search by file name..."
            aria-label="Search documents"
          />

          {search && (
            <button
              type="button"
              className="clear-search-button"
              onClick={() => onSearch("")}
              aria-label="Clear search"
              title="Clear search"
            >
              <X size={16} />
            </button>
          )}
        </div>

        <div className="documents-toolbar-actions">
          <select
            className="documents-sort-select"
            value={sort}
            onChange={(event) =>
              setSort(
                event.target
                  .value as SortOption,
              )
            }
            aria-label="Sort documents"
          >
            <option value="newest">
              Newest first
            </option>

            <option value="oldest">
              Oldest first
            </option>

            <option value="name-asc">
              Name A–Z
            </option>

            <option value="name-desc">
              Name Z–A
            </option>

            <option value="largest">
              Largest file
            </option>

            <option value="smallest">
              Smallest file
            </option>
          </select>

          <div
            className="documents-view-switch"
            aria-label="Document view"
          >
            <button
              type="button"
              className={
                settings.documentView ===
                "list"
                  ? "active"
                  : ""
              }
              onClick={() =>
                handleViewChange("list")
              }
              title="List view"
              aria-label="List view"
            >
              <List size={16} />
            </button>

            <button
              type="button"
              className={
                settings.documentView ===
                "grid"
                  ? "active"
                  : ""
              }
              onClick={() =>
                handleViewChange("grid")
              }
              title="Grid view"
              aria-label="Grid view"
            >
              <Grid2X2 size={16} />
            </button>
          </div>

          <button
            type="button"
            className="documents-refresh-button"
            onClick={onRefresh}
            disabled={loading}
            aria-label="Refresh documents"
            title="Refresh documents"
          >
            <RefreshCw
              size={17}
              className={
                loading ? "spin" : ""
              }
            />

            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* FILE FILTERS */}

      <div className="document-summary">
        <button
          type="button"
          className={`document-summary-card ${
            selectedFileType === "all"
              ? "active"
              : ""
          }`}
          onClick={() =>
            handleFileTypeFilter("all")
          }
        >
          <div className="summary-card-icon all">
            <File size={19} />
          </div>

          <div>
            <strong>
              {documents.length}
            </strong>

            <span>All files</span>
          </div>
        </button>

        <button
          type="button"
          className={`document-summary-card ${
            selectedFileType === "pdf"
              ? "active"
              : ""
          }`}
          onClick={() =>
            handleFileTypeFilter("pdf")
          }
        >
          <div className="summary-card-icon pdf">
            <FileType size={19} />
          </div>

          <div>
            <strong>{pdfCount}</strong>
            <span>PDF</span>
          </div>
        </button>

        <button
          type="button"
          className={`document-summary-card ${
            selectedFileType === "docx"
              ? "active"
              : ""
          }`}
          onClick={() =>
            handleFileTypeFilter("docx")
          }
        >
          <div className="summary-card-icon docx">
            <FileText size={19} />
          </div>

          <div>
            <strong>{docxCount}</strong>
            <span>Word</span>
          </div>
        </button>

        <button
          type="button"
          className={`document-summary-card ${
            selectedFileType === "xlsx"
              ? "active"
              : ""
          }`}
          onClick={() =>
            handleFileTypeFilter("xlsx")
          }
        >
          <div className="summary-card-icon xlsx">
            <FileSpreadsheet size={19} />
          </div>

          <div>
            <strong>{xlsxCount}</strong>
            <span>Excel</span>
          </div>
        </button>

        <button
          type="button"
          className={`document-summary-card ${
            selectedFileType === "pptx"
              ? "active"
              : ""
          }`}
          onClick={() =>
            handleFileTypeFilter("pptx")
          }
        >
          <div className="summary-card-icon pptx">
            <FileText size={19} />
          </div>

          <div>
            <strong>{pptxCount}</strong>
            <span>PowerPoint</span>
          </div>
        </button>

        <button
          type="button"
          className={`document-summary-card ${
            selectedFileType === "txt"
              ? "active"
              : ""
          }`}
          onClick={() =>
            handleFileTypeFilter("txt")
          }
        >
          <div className="summary-card-icon txt">
            <FileText size={19} />
          </div>

          <div>
            <strong>{txtCount}</strong>
            <span>Text files</span>
          </div>
        </button>
      </div>

      {/* LOADING */}

      {loading && (
        <div className="documents-loading">
          <Loader2
            size={27}
            className="spin"
          />

          <p>Loading documents...</p>
        </div>
      )}

      {/* EMPTY */}

      {!loading &&
        filteredDocuments.length === 0 && (
          <div className="documents-empty">
            <div className="documents-empty-icon">
              <FileText size={30} />
            </div>

            <h3>
              {search ||
              selectedFileType !== "all"
                ? "No matching documents"
                : "No documents yet"}
            </h3>

            <p>
              {search ||
              selectedFileType !== "all"
                ? "Try another search or select a different file type."
                : "Documents will appear here once they are added to your library."}
            </p>

            {(search ||
              selectedFileType !== "all") && (
              <button
                type="button"
                className="clear-filters-button"
                onClick={() => {
                  onSearch("");
                  setSelectedFileType("all");
                }}
              >
                Clear filters
              </button>
            )}
          </div>
        )}

      {/* DOCUMENTS */}

      {!loading &&
        paginatedDocuments.length > 0 && (
          <>
            <div
              className={`documents-grid ${
                settings.documentView ===
                "list"
                  ? "documents-list-view"
                  : "documents-grid-view"
              }`}
            >
              {paginatedDocuments.map(
                renderDocumentCard,
              )}
            </div>

            {/* PAGINATION */}

            <div className="documents-pagination">
              <div className="documents-pagination-info">
                Showing{" "}
                <strong>
                  {showingFrom}
                </strong>{" "}
                –{" "}
                <strong>
                  {showingTo}
                </strong>{" "}
                of{" "}
                <strong>
                  {filteredDocuments.length}
                </strong>{" "}
                documents
              </div>

              {totalPages > 1 && (
                <div className="documents-pagination-controls">
                  <button
                    type="button"
                    onClick={() =>
                      goToPage(
                        currentPage - 1,
                      )
                    }
                    disabled={
                      currentPage === 1
                    }
                    aria-label="Previous page"
                  >
                    <ChevronLeft size={17} />
                  </button>

                  <span>
                    Page{" "}
                    <strong>
                      {currentPage}
                    </strong>{" "}
                    of{" "}
                    <strong>
                      {totalPages}
                    </strong>
                  </span>

                  <button
                    type="button"
                    onClick={() =>
                      goToPage(
                        currentPage + 1,
                      )
                    }
                    disabled={
                      currentPage ===
                      totalPages
                    }
                    aria-label="Next page"
                  >
                    <ChevronRight size={17} />
                  </button>
                </div>
              )}
            </div>
          </>
        )}
    </div>
  );
}