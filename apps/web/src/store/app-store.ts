import { create } from "zustand";
import { devtools } from "zustand/middleware";

export interface AppState {
  // Connection status
  isConnected: boolean;
  connectionStatus: "connecting" | "connected" | "disconnected" | "error";

  // Authentication
  isAuthenticated: boolean;
  user: {
    username: string;
    role: string;
  } | null;

  // UI state
  sidebarOpen: boolean;
  darkMode: boolean;

  // Actions
  setConnectionStatus: (status: AppState["connectionStatus"]) => void;
  setAuthenticated: (authenticated: boolean, user?: AppState["user"]) => void;
  toggleSidebar: () => void;
  toggleDarkMode: () => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    (set) => ({
      // Initial state
      isConnected: false,
      connectionStatus: "disconnected",
      isAuthenticated: false,
      user: null,
      sidebarOpen: true,
      darkMode: true,

      // Actions
      setConnectionStatus: (status) =>
        set(
          (state) => ({
            ...state,
            connectionStatus: status,
            isConnected: status === "connected",
          }),
          false,
          "setConnectionStatus",
        ),

      setAuthenticated: (authenticated, user = null) =>
        set(
          (state) => ({
            ...state,
            isAuthenticated: authenticated,
            user: authenticated ? user : null,
          }),
          false,
          "setAuthenticated",
        ),

      toggleSidebar: () =>
        set(
          (state) => ({ ...state, sidebarOpen: !state.sidebarOpen }),
          false,
          "toggleSidebar",
        ),

      toggleDarkMode: () =>
        set(
          (state) => ({ ...state, darkMode: !state.darkMode }),
          false,
          "toggleDarkMode",
        ),
    }),
    {
      name: "app-store",
    },
  ),
);
