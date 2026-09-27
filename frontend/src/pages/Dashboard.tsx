import {
  FileText,
  MessageSquare,
  Upload,
  File,
  CheckCircle2,
} from "lucide-react";

import "./Dashboard.css";

interface DocumentItem {
  id: number | string;
  filename: string;
  file_size?: number;
  file_type?: string;
  status?: string;
  created_at?: string;
  pages?: number;
}

interface DashboardStats {
  total_documents: number;
  total_pages: number;
  total_chunks: number;
}

interface DashboardProps {
  documents: DocumentItem[];
  stats: DashboardStats;
  loading: boolean;
  error: string | null;
  uploadError: string | null;
  uploadSuccess: string | null;
  selectedFile: File | null;
  isUploading: boolean;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelect: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onUpload: () => void;
  onChangePage: (
    page: "dashboard" | "documents" | "chat" | "settings"
  ) => void;
  onViewDocument: (document: DocumentItem) => void;
}

const formatDate = (date?: string) => {
  if (!date) return "Unknown date";

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "Unknown date";
  }

  return parsedDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const formatFileSize = (bytes?: number) => {
  if (!bytes || bytes <= 0) return "Unknown size";

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const getFileExtension = (filename: string) => {
  const parts = filename.split(".");

  if (parts.length < 2) {
    return "file";
  }

  return parts.pop()?.toLowerCase() || "file";
};

const getFileTypeLabel = (filename: string) => {
  const extension = getFileExtension(filename);

  const labels: Record<string, string> = {
    pdf: "PDF",
    doc: "DOC",
    docx: "DOCX",
    txt: "TXT",
    csv: "CSV",
    xls: "XLS",
    xlsx: "XLSX",
    ppt: "PPT",
    pptx: "PPTX",
  };

  return labels[extension] || extension.toUpperCase();
};

const getFileTypeClass = (filename: string) => {
  const extension = getFileExtension(filename);

  const classes: Record<string, string> = {
    pdf: "pdf",
    doc: "word",
    docx: "word",
    txt: "text",
    csv: "spreadsheet",
    xls: "spreadsheet",
    xlsx: "spreadsheet",
    ppt: "presentation",
    pptx: "presentation",
  };

  return classes[extension] || "default";
};

const Dashboard = ({
  documents,
  stats,
  loading,
  error,
  uploadError,
  uploadSuccess,
  selectedFile,
  isUploading,
  fileInputRef,
  onFileSelect,
  onUpload,
  onChangePage,
  onViewDocument,
}: DashboardProps) => {
  const fileTypeCount = new Set(
    documents
      .map((document) => getFileExtension(document.filename))
      .filter(Boolean)
  ).size;

  const recentDocuments = documents.slice(0, 5);

  return (
    <main className="dashboard-page">
      {/* ================================================================
          ERROR
      ================================================================= */}

      {error && (
        <div className="dashboard-alert dashboard-alert-error dashboard-animate">
          <span>{error}</span>
        </div>
      )}

      {/* ================================================================
          STAT CARDS
      ================================================================= */}

      <section className="dashboard-stats dashboard-animate dashboard-delay-1">
        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon blue">
            <FileText size={21} strokeWidth={2} />
          </div>

          <div className="dashboard-stat-content">
            <span className="dashboard-stat-label">Documents</span>

            <strong>
              {loading ? (
                <span className="dashboard-number-skeleton" />
              ) : (
                stats.total_documents
              )}
            </strong>

            <small>Files in your workspace</small>
          </div>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon purple">
            <File size={21} strokeWidth={2} />
          </div>

          <div className="dashboard-stat-content">
            <span className="dashboard-stat-label">Pages</span>

            <strong>
              {loading ? (
                <span className="dashboard-number-skeleton" />
              ) : (
                stats.total_pages
              )}
            </strong>

            <small>Total pages processed</small>
          </div>
        </div>

        <div className="dashboard-stat-card">
          <div className="dashboard-stat-icon green">
            <CheckCircle2 size={21} strokeWidth={2} />
          </div>

          <div className="dashboard-stat-content">
            <span className="dashboard-stat-label">File Types</span>

            <strong>
              {loading ? (
                <span className="dashboard-number-skeleton" />
              ) : (
                fileTypeCount
              )}
            </strong>

            <small>Different formats</small>
          </div>
        </div>
      </section>

      {/* ================================================================
          MAIN GRID
      ================================================================= */}

      <section className="dashboard-main-grid">
        {/* ============================================================
            UPLOAD
        ============================================================= */}

        <div className="dashboard-card dashboard-upload-card dashboard-animate dashboard-delay-2">
          <div className="dashboard-card-header">
            <div>
              <span className="dashboard-card-eyebrow">GET STARTED</span>

              <h2>Add a document</h2>

              <p>
                Upload a file to add it to your DocuMind knowledge base.
              </p>
            </div>

            <div className="dashboard-card-header-icon">
              <Upload size={20} />
            </div>
          </div>

          <div className="dashboard-upload-area">
            <div className="dashboard-upload-icon">
              <Upload size={26} strokeWidth={1.8} />
            </div>

            <div className="dashboard-upload-text">
              <strong>
                {selectedFile
                  ? selectedFile.name
                  : "Choose a document to upload"}
              </strong>

              <span>
                {selectedFile
                  ? `${formatFileSize(selectedFile.size)} selected`
                  : "PDF, DOCX, TXT, CSV and other supported files"}
              </span>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              className="dashboard-file-input"
              onChange={onFileSelect}
            />

            <button
              type="button"
              className="dashboard-secondary-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              Choose file
            </button>
          </div>

          <button
            type="button"
            className="dashboard-upload-button"
            onClick={onUpload}
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? (
              <>
                <span className="dashboard-spinner" />
                Uploading...
              </>
            ) : (
              <>
                <Upload size={17} />
                Upload document
              </>
            )}
          </button>

          {uploadError && (
            <div className="dashboard-upload-message error">
              {uploadError}
            </div>
          )}

          {uploadSuccess && (
            <div className="dashboard-upload-message success">
              <CheckCircle2 size={17} />
              {uploadSuccess}
            </div>
          )}
        </div>

        {/* ============================================================
            RECENT DOCUMENTS
        ============================================================= */}

        <div className="dashboard-card dashboard-recent-card dashboard-animate dashboard-delay-3">
          <div className="dashboard-card-header">
            <div>
              <span className="dashboard-card-eyebrow">YOUR LIBRARY</span>

              <h2>Recent documents</h2>

              <p>Your latest uploaded files.</p>
            </div>

            <button
              type="button"
              className="dashboard-card-link"
              onClick={() => onChangePage("documents")}
            >
              View all
              <span>→</span>
            </button>
          </div>

          <div className="dashboard-document-list">
            {loading ? (
              <>
                {[1, 2, 3].map((item) => (
                  <div
                    className="dashboard-document-skeleton"
                    key={item}
                  >
                    <span />
                    <div>
                      <span />
                      <span />
                    </div>
                  </div>
                ))}
              </>
            ) : recentDocuments.length > 0 ? (
              recentDocuments.map((document) => {
                const isPending =
                  document.status &&
                  !["processed", "completed", "ready"].includes(
                    document.status.toLowerCase()
                  );

                return (
                  <button
                    type="button"
                    key={document.id}
                    className={`dashboard-document-item ${
                      isPending ? "is-pending" : ""
                    }`}
                    onClick={() => {
                      if (!isPending) {
                        onViewDocument(document);
                      }
                    }}
                    disabled={Boolean(isPending)}
                  >
                    <div
                      className={`dashboard-document-icon ${getFileTypeClass(
                        document.filename
                      )}`}
                    >
                      <File size={18} />
                    </div>

                    <div className="dashboard-document-info">
                      <strong title={document.filename}>
                        {document.filename}
                      </strong>

                      <span>
                        {getFileTypeLabel(document.filename)} ·{" "}
                        {formatDate(document.created_at)}
                      </span>
                    </div>

                    <div className="dashboard-document-status">
                      {isPending ? (
                        <span className="dashboard-pending-badge">
                          Pending
                        </span>
                      ) : (
                        <span className="dashboard-document-arrow">
                          →
                        </span>
                      )}
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="dashboard-empty-state">
                <div className="dashboard-empty-icon">
                  <FileText size={24} />
                </div>

                <strong>No documents yet</strong>

                <span>
                  Upload your first document to start building your
                  knowledge base.
                </span>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ================================================================
          QUICK ACCESS
      ================================================================= */}

      <section className="dashboard-quick-section dashboard-animate dashboard-delay-4">
        <div className="dashboard-section-heading">
          <div>
            <span className="dashboard-card-eyebrow">QUICK ACCESS</span>

            <h2>What would you like to do?</h2>
          </div>
        </div>

        <div className="dashboard-quick-grid">
          <button
            type="button"
            className="dashboard-quick-card"
            onClick={() => onChangePage("documents")}
          >
            <div className="dashboard-quick-icon blue">
              <FileText size={22} />
            </div>

            <div className="dashboard-quick-content">
              <strong>Browse documents</strong>

              <span>
                View and manage everything in your knowledge base.
              </span>
            </div>

            <span className="dashboard-quick-arrow">→</span>
          </button>

          <button
            type="button"
            className="dashboard-quick-card"
            onClick={() => onChangePage("chat")}
          >
            <div className="dashboard-quick-icon purple">
              <MessageSquare size={22} />
            </div>

            <div className="dashboard-quick-content">
              <strong>Ask questions</strong>

              <span>
                Chat with your documents and find information quickly.
              </span>
            </div>

            <span className="dashboard-quick-arrow">→</span>
          </button>
        </div>
      </section>
    </main>
  );
};

export default Dashboard;