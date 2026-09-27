export type AppSettings = {
  documentView: "list" | "grid";
  documentsPerPage: "10" | "20" | "50";
  confirmDelete: boolean;
  autoRefresh: boolean;

  autoProcessUploads: boolean;
  keepUploadedFiles: boolean;

  responseStyle: "concise" | "balanced" | "detailed";
  showSources: boolean;
  sourceCount: "3" | "5" | "8";
  useGeneralKnowledge: boolean;

  saveChatHistory: boolean;
  enterToSend: boolean;
  confirmClearChat: boolean;

  theme: "light" | "dark" | "system";
  compactMode: boolean;
};

export const SETTINGS_STORAGE_KEY = "documind-settings";

export const SETTINGS_CHANGED_EVENT =
  "documind-settings-changed";


// ============================================================
// DEFAULT SETTINGS
// ============================================================

export const DEFAULT_SETTINGS: AppSettings = {
  documentView: "list",
  documentsPerPage: "20",
  confirmDelete: true,
  autoRefresh: true,

  autoProcessUploads: true,
  keepUploadedFiles: true,

  responseStyle: "balanced",
  showSources: true,
  sourceCount: "5",

  // General AI knowledge is ON by default.
  useGeneralKnowledge: true,

  saveChatHistory: true,
  enterToSend: true,
  confirmClearChat: true,

  theme: "light",
  compactMode: false,
};


// ============================================================
// LOAD SETTINGS
// ============================================================

export function loadSettings(): AppSettings {
  try {
    const saved = localStorage.getItem(
      SETTINGS_STORAGE_KEY,
    );

    // No saved settings.
    // Use the defaults.
    if (!saved) {
      return {
        ...DEFAULT_SETTINGS,
      };
    }

    const parsed = JSON.parse(saved);

    // Invalid saved settings.
    if (
      !parsed ||
      typeof parsed !== "object" ||
      Array.isArray(parsed)
    ) {
      return {
        ...DEFAULT_SETTINGS,
      };
    }

    /*
     * Merge saved settings with defaults.
     *
     * This means new settings added later will still
     * automatically receive their default values.
     */
    const settings: AppSettings = {
      ...DEFAULT_SETTINGS,
      ...parsed,
    };

    /*
     * IMPORTANT:
     *
     * Older versions of DocuMind may have saved:
     *
     * useGeneralKnowledge: false
     *
     * If you want the new ChatGPT-like behavior enabled
     * for existing users, we force it ON here.
     *
     * The user can still turn it OFF later through
     * Settings, which will be saved normally.
     */
    if (
      typeof parsed.useGeneralKnowledge !== "boolean"
    ) {
      settings.useGeneralKnowledge = true;
    }

    return settings;
  } catch (error) {
    console.error(
      "Failed to load DocuMind settings:",
      error,
    );

    return {
      ...DEFAULT_SETTINGS,
    };
  }
}


// ============================================================
// GET SETTINGS
// ============================================================

export function getSettings(): AppSettings {
  return loadSettings();
}


// ============================================================
// SAVE SETTINGS
// ============================================================

export function saveSettings(
  settings: AppSettings,
): void {
  try {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify(settings),
    );

    window.dispatchEvent(
      new Event(
        SETTINGS_CHANGED_EVENT,
      ),
    );
  } catch (error) {
    console.error(
      "Failed to save DocuMind settings:",
      error,
    );
  }
}


// ============================================================
// RESET SETTINGS
// ============================================================

export function resetSettings(): AppSettings {
  const defaults: AppSettings = {
    ...DEFAULT_SETTINGS,
  };

  saveSettings(defaults);

  return defaults;
}


// ============================================================
// APPLY THEME
// ============================================================

export function applyTheme(
  theme: AppSettings["theme"],
): void {
  const html = document.documentElement;

  /*
   * DocuMind uses:
   *
   * html[data-theme="dark"]
   *
   * instead of body.dark-theme.
   *
   * This keeps the settings service consistent with
   * App.tsx and the rest of the CSS.
   */

  html.removeAttribute("data-theme");

  if (theme === "dark") {
    html.setAttribute(
      "data-theme",
      "dark",
    );

    return;
  }

  if (theme === "light") {
    html.setAttribute(
      "data-theme",
      "light",
    );

    return;
  }

  if (theme === "system") {
    const prefersDark =
      window.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;

    html.setAttribute(
      "data-theme",
      prefersDark
        ? "dark"
        : "light",
    );
  }
}