import {
  FileText,
  MessageSquare,
  LayoutDashboard,
  Settings,
  Sparkles,
} from "lucide-react";

import "./Sidebar.css";

export type Page =
  | "dashboard"
  | "documents"
  | "chat"
  | "settings";

interface SidebarProps {
  activePage: Page;
  onPageChange: (page: Page) => void;
  apiStatus: string;
}

function Sidebar({
  activePage,
  onPageChange,
}: SidebarProps) {
  const getNavClass = (page: Page) => {
    return activePage === page
      ? "nav-item active"
      : "nav-item";
  };

  return (
    <aside className="sidebar">

      {/* =====================================================
          BRAND
      ====================================================== */}

      <div className="brand">

        {/*
          CURRENT LOGO

          When you are ready to use your own image,
          replace this entire div with:

          <div className="brand-logo">
            <img
              src="/logo.png"
              alt="DocuMind Logo"
            />
          </div>
        */}

        <div className="brand-logo">
          <img
            src="/logo.png"
            alt="DocuMind Logo"
          />
        </div>

        <div className="brand-text">
          <h1>DocuMind</h1>
        </div>

      </div>


      {/* =====================================================
          NAVIGATION
      ====================================================== */}

      <nav
        className="navigation"
        aria-label="Main navigation"
      >

        {/* DASHBOARD */}

        <button
          type="button"
          className={getNavClass("dashboard")}
          onClick={() => onPageChange("dashboard")}
          aria-current={
            activePage === "dashboard"
              ? "page"
              : undefined
          }
          title="Dashboard"
        >
          <span className="nav-icon">
            <LayoutDashboard
              size={19}
              strokeWidth={2}
            />
          </span>

          <span className="nav-label">
            Dashboard
          </span>

          <span className="nav-active-indicator" />
        </button>


        {/* DOCUMENTS */}

        <button
          type="button"
          className={getNavClass("documents")}
          onClick={() => onPageChange("documents")}
          aria-current={
            activePage === "documents"
              ? "page"
              : undefined
          }
          title="Documents"
        >
          <span className="nav-icon">
            <FileText
              size={19}
              strokeWidth={2}
            />
          </span>

          <span className="nav-label">
            Documents
          </span>

          <span className="nav-active-indicator" />
        </button>


        {/* AI CHAT */}

        <button
          type="button"
          className={getNavClass("chat")}
          onClick={() => onPageChange("chat")}
          aria-current={
            activePage === "chat"
              ? "page"
              : undefined
          }
          title="AI Chat"
        >
          <span className="nav-icon">
            <MessageSquare
              size={19}
              strokeWidth={2}
            />
          </span>

          <span className="nav-label">
            AI Chat
          </span>

          <span className="nav-active-indicator" />
        </button>


        {/* SETTINGS */}

        <button
          type="button"
          className={getNavClass("settings")}
          onClick={() => onPageChange("settings")}
          aria-current={
            activePage === "settings"
              ? "page"
              : undefined
          }
          title="Settings"
        >
          <span className="nav-icon">
            <Settings
              size={19}
              strokeWidth={2}
            />
          </span>

          <span className="nav-label">
            Settings
          </span>

          <span className="nav-active-indicator" />
        </button>

      </nav>

    </aside>
  );
}

export default Sidebar;