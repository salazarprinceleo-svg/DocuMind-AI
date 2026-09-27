import {
  CheckCircle2,
  ChevronDown,
  Database,
  FileCheck2,
  Info,
  Monitor,
  RotateCcw,
  Save,
  Server,
} from "lucide-react";

import {
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  applyTheme,
  loadSettings,
  resetSettings as resetStoredSettings,
  saveSettings as saveStoredSettings,
  type AppSettings,
} from "../services/settings";

import "./Settings.css";

interface SettingsProps {
  apiStatus: string;
}

function Settings({
  apiStatus,
}: SettingsProps) {
  const [settings, setSettings] =
    useState<AppSettings>(
      loadSettings,
    );

  const [saved, setSaved] =
    useState(false);

  const [resetting, setResetting] =
    useState(false);

  const isConnected =
    apiStatus === "Connected";

  /* =====================================================
     SAVE SETTINGS
  ===================================================== */

  const handleSaveSettings = () => {
    saveStoredSettings(settings);

    applyTheme(settings.theme);

    setSaved(true);

    window.setTimeout(() => {
      setSaved(false);
    }, 1800);
  };

  /* =====================================================
     RESET SETTINGS
  ===================================================== */

  const handleResetSettings = () => {
    setResetting(true);

    const defaults =
      resetStoredSettings();

    setSettings(defaults);

    applyTheme(
      defaults.theme,
    );

    window.setTimeout(() => {
      setResetting(false);
    }, 400);
  };

  /* =====================================================
     UPDATE SETTING
  ===================================================== */

  const updateSetting = <
    K extends keyof AppSettings
  >(
    key: K,
    value: AppSettings[K],
  ) => {
    setSettings(
      (current) => ({
        ...current,
        [key]: value,
      }),
    );
  };

  /* =====================================================
     APPLY THEME
  ===================================================== */

  useEffect(() => {
    applyTheme(
      settings.theme,
    );
  }, [settings.theme]);

  /* =====================================================
     SYSTEM INFORMATION
  ===================================================== */

  const getThemeLabel =
    () => {
      if (
        settings.theme ===
        "light"
      ) {
        return "Light";
      }

      if (
        settings.theme ===
        "dark"
      ) {
        return "Dark";
      }

      return "System";
    };

  return (
    <section className="settings-page">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="settings-page-header">

        <div>

          <span className="settings-eyebrow">
            PREFERENCES
          </span>

          <h1>Settings</h1>

          <p>
            Manage how DocuMind looks,
            handles documents, and
            responds to your requests.
          </p>

        </div>

        <div className="settings-header-actions">

          <button
            type="button"
            className="settings-reset-button"
            onClick={
              handleResetSettings
            }
            disabled={resetting}
          >

            <RotateCcw
              size={15}
            />

            {resetting
              ? "Resetting..."
              : "Reset defaults"}

          </button>

          <button
            type="button"
            className={
              saved
                ? "settings-save-button saved"
                : "settings-save-button"
            }
            onClick={
              handleSaveSettings
            }
          >

            {saved ? (
              <CheckCircle2
                size={15}
              />
            ) : (
              <Save
                size={15}
              />
            )}

            {saved
              ? "Saved"
              : "Save changes"}

          </button>

        </div>

      </div>

      {/* =================================================
          GENERAL
      ================================================= */}

      <div className="settings-section">

        <div className="settings-section-heading">

          <h2>General</h2>

          <p>
            Basic preferences for how
            your documents are displayed
            and managed.
          </p>

        </div>

        <div className="settings-card">

          <div className="settings-option">

            <div className="settings-option-info">

              <strong>
                Document view
              </strong>

              <span>
                Choose how documents are
                displayed in your document
                library.
              </span>

            </div>

            <SelectControl
              value={
                settings.documentView
              }
              onChange={(value) =>
                updateSetting(
                  "documentView",
                  value as AppSettings[
                    "documentView"
                  ],
                )
              }
              options={[
                {
                  value: "list",
                  label: "List",
                },
                {
                  value: "grid",
                  label: "Grid",
                },
              ]}
            />

          </div>

          <div className="settings-divider" />

          <div className="settings-option">

            <div className="settings-option-info">

              <strong>
                Documents per page
              </strong>

              <span>
                Number of documents shown
                at once in the document
                library.
              </span>

            </div>

            <SelectControl
              value={
                settings.documentsPerPage
              }
              onChange={(value) =>
                updateSetting(
                  "documentsPerPage",
                  value as AppSettings[
                    "documentsPerPage"
                  ],
                )
              }
              options={[
                {
                  value: "10",
                  label: "10",
                },
                {
                  value: "20",
                  label: "20",
                },
                {
                  value: "50",
                  label: "50",
                },
              ]}
            />

          </div>

          <div className="settings-divider" />

          <SettingToggle
            title="Confirm before deleting"
            description="Ask for confirmation before permanently deleting a document."
            checked={
              settings.confirmDelete
            }
            onChange={(value) =>
              updateSetting(
                "confirmDelete",
                value,
              )
            }
          />

          <div className="settings-divider" />

          <SettingToggle
            title="Auto refresh documents"
            description="Automatically refresh the document list after changes."
            checked={
              settings.autoRefresh
            }
            onChange={(value) =>
              updateSetting(
                "autoRefresh",
                value,
              )
            }
          />

        </div>

      </div>

      {/* =================================================
          DOCUMENT HANDLING
      ================================================= */}

      <div className="settings-section">

        <div className="settings-section-heading">

          <h2>
            Document handling
          </h2>

          <p>
            Control what happens when
            you upload and process a
            document.
          </p>

        </div>

        <div className="settings-card">

          <SettingToggle
            title="Process uploads automatically"
            description="Start extracting and indexing a document immediately after upload."
            checked={
              settings.autoProcessUploads
            }
            onChange={(value) =>
              updateSetting(
                "autoProcessUploads",
                value,
              )
            }
          />

          <div className="settings-divider" />

          <SettingToggle
            title="Keep uploaded files"
            description="Keep the original uploaded file available for preview and download."
            checked={
              settings.keepUploadedFiles
            }
            onChange={(value) =>
              updateSetting(
                "keepUploadedFiles",
                value,
              )
            }
          />

        </div>

      </div>

      {/* =================================================
          AI PREFERENCES
      ================================================= */}

      <div className="settings-section">

        <div className="settings-section-heading">

          <h2>
            AI preferences
          </h2>

          <p>
            Adjust how document-based
            answers are generated and
            presented.
          </p>

        </div>

        <div className="settings-card">

          <div className="settings-option">

            <div className="settings-option-info">

              <strong>
                Response style
              </strong>

              <span>
                Choose how detailed
                responses should be.
              </span>

            </div>

            <SelectControl
              value={
                settings.responseStyle
              }
              onChange={(value) =>
                updateSetting(
                  "responseStyle",
                  value as AppSettings[
                    "responseStyle"
                  ],
                )
              }
              options={[
                {
                  value: "concise",
                  label: "Concise",
                },
                {
                  value: "balanced",
                  label: "Balanced",
                },
                {
                  value: "detailed",
                  label: "Detailed",
                },
              ]}
            />

          </div>

          <div className="settings-divider" />

          <SettingToggle
            title="Show document sources"
            description="Show the document and page used to support an answer."
            checked={
              settings.showSources
            }
            onChange={(value) =>
              updateSetting(
                "showSources",
                value,
              )
            }
          />

          <div className="settings-divider" />

          <div className="settings-option">

            <div className="settings-option-info">

              <strong>
                Sources per answer
              </strong>

              <span>
                Maximum number of
                document references shown
                with an answer.
              </span>

            </div>

            <SelectControl
              value={
                settings.sourceCount
              }
              onChange={(value) =>
                updateSetting(
                  "sourceCount",
                  value as AppSettings[
                    "sourceCount"
                  ],
                )
              }
              options={[
                {
                  value: "3",
                  label: "3",
                },
                {
                  value: "5",
                  label: "5",
                },
                {
                  value: "8",
                  label: "8",
                },
              ]}
            />

          </div>

          <div className="settings-divider" />

          <SettingToggle
            title="Use general knowledge"
            description="Allow answers from the language model when selected documents do not contain enough information."
            checked={
              settings.useGeneralKnowledge
            }
            onChange={(value) =>
              updateSetting(
                "useGeneralKnowledge",
                value,
              )
            }
          />

        </div>

      </div>

      {/* =================================================
          CHAT
      ================================================= */}

      <div className="settings-section">

        <div className="settings-section-heading">

          <h2>Chat</h2>

          <p>
            Preferences for your
            document conversations.
          </p>

        </div>

        <div className="settings-card">

          <SettingToggle
            title="Save chat history"
            description="Keep conversations available during your current application session."
            checked={
              settings.saveChatHistory
            }
            onChange={(value) =>
              updateSetting(
                "saveChatHistory",
                value,
              )
            }
          />

          <div className="settings-divider" />

          <SettingToggle
            title="Enter to send"
            description="Press Enter to send your message. Use Shift + Enter for a new line."
            checked={
              settings.enterToSend
            }
            onChange={(value) =>
              updateSetting(
                "enterToSend",
                value,
              )
            }
          />

          <div className="settings-divider" />

          <SettingToggle
            title="Confirm before clearing chat"
            description="Ask before removing the current conversation."
            checked={
              settings.confirmClearChat
            }
            onChange={(value) =>
              updateSetting(
                "confirmClearChat",
                value,
              )
            }
          />

        </div>

      </div>

      {/* =================================================
          APPEARANCE
      ================================================= */}

      <div className="settings-section">

        <div className="settings-section-heading">

          <h2>Appearance</h2>

          <p>
            Choose how DocuMind looks
            on your screen.
          </p>

        </div>

        <div className="settings-card">

          <div className="settings-option">

            <div className="settings-option-info">

              <strong>
                Theme
              </strong>

              <span>
                Current theme:{" "}
                {getThemeLabel()}
              </span>

            </div>

            <SelectControl
              value={
                settings.theme
              }
              onChange={(value) =>
                updateSetting(
                  "theme",
                  value as AppSettings[
                    "theme"
                  ],
                )
              }
              options={[
                {
                  value: "light",
                  label: "Light",
                },
                {
                  value: "dark",
                  label: "Dark",
                },
                {
                  value: "system",
                  label: "System",
                },
              ]}
            />

          </div>

          <div className="settings-divider" />

          <SettingToggle
            title="Compact interface"
            description="Reduce spacing in lists and controls to fit more content on screen."
            checked={
              settings.compactMode
            }
            onChange={(value) =>
              updateSetting(
                "compactMode",
                value,
              )
            }
          />

        </div>

      </div>

      {/* =================================================
          SYSTEM INFORMATION
      ================================================= */}

      <div className="settings-section">

        <div className="settings-section-heading">

          <h2>
            System information
          </h2>

          <p>
            Technical information about
            your current DocuMind setup.
          </p>

        </div>

        <div className="settings-card system-information">

          <SystemInfoRow
            icon={
              <Server size={17} />
            }
            label="Backend API"
            value={apiStatus}
            status={isConnected}
          />

          <div className="settings-divider" />

          <SystemInfoRow
            icon={
              <Database size={17} />
            }
            label="AI service"
            value="Ollama · Local"
            status
          />

          <div className="settings-divider" />

          <SystemInfoRow
            icon={
              <Monitor size={17} />
            }
            label="Language model"
            value="gemma3:1b"
          />

          <div className="settings-divider" />

          <SystemInfoRow
            icon={
              <Database size={17} />
            }
            label="Embedding model"
            value="nomic-embed-text"
          />

          <div className="settings-divider" />

          <SystemInfoRow
            icon={
              <FileCheck2 size={17} />
            }
            label="Document formats"
            value="PDF · DOCX · XLSX · PPTX · TXT"
          />

        </div>

      </div>

      {/* =================================================
          INFORMATION
      ================================================= */}

      <div className="settings-info">

        <div className="settings-info-icon">
          <Info size={17} />
        </div>

        <div>

          <strong>
            Your settings are stored locally
          </strong>

          <p>
            Preferences on this page are
            saved in your browser using
            local storage. They do not
            require an account or database.
            Resetting the settings restores
            the original DocuMind defaults.
          </p>

        </div>

      </div>

    </section>
  );
}

/* =========================================================
   TOGGLE COMPONENT
========================================================= */

interface SettingToggleProps {
  title: string;
  description: string;
  checked: boolean;
  onChange: (
    value: boolean,
  ) => void;
}

function SettingToggle({
  title,
  description,
  checked,
  onChange,
}: SettingToggleProps) {
  return (
    <div className="settings-option">

      <div className="settings-option-info">

        <strong>
          {title}
        </strong>

        <span>
          {description}
        </span>

      </div>

      <button
        type="button"
        className={
          checked
            ? "settings-toggle active"
            : "settings-toggle"
        }
        role="switch"
        aria-checked={checked}
        onClick={() =>
          onChange(!checked)
        }
      >

        <span className="settings-toggle-knob" />

      </button>

    </div>
  );
}

/* =========================================================
   SELECT COMPONENT
========================================================= */

interface SelectOption {
  value: string;
  label: string;
}

interface SelectControlProps {
  value: string;
  options: SelectOption[];
  onChange: (
    value: string,
  ) => void;
}

function SelectControl({
  value,
  options,
  onChange,
}: SelectControlProps) {
  return (
    <div className="theme-select-wrapper">

      <select
        value={value}
        onChange={(event) =>
          onChange(
            event.target.value,
          )
        }
        className="settings-select"
      >

        {options.map(
          (option) => (
            <option
              key={option.value}
              value={option.value}
            >
              {option.label}
            </option>
          ),
        )}

      </select>

      <ChevronDown
        size={15}
        className="select-chevron"
      />

    </div>
  );
}

/* =========================================================
   SYSTEM INFORMATION ROW
========================================================= */

interface SystemInfoRowProps {
  icon: ReactNode;
  label: string;
  value: string;
  status?: boolean;
}

function SystemInfoRow({
  icon,
  label,
  value,
  status,
}: SystemInfoRowProps) {
  return (
    <div className="system-info-row">

      <div className="system-info-left">

        <div className="system-info-icon">
          {icon}
        </div>

        <span>
          {label}
        </span>

      </div>

      <div
        className={
          status === true
            ? "system-info-value status"
            : "system-info-value"
        }
      >

        {status === true && (
          <span className="system-status-dot" />
        )}

        {value}

      </div>

    </div>
  );
}

export default Settings;