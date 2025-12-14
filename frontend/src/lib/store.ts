import { create } from "zustand";
import type { ChatMessage, ChunkModel } from "@/lib/types";

type UploadStatus = "idle" | "processing" | "ready" | "error";

type ErrState = {
  backendUrl: string;
  isDesktop: boolean;
  setIsDesktop: (v: boolean) => void;

  fastMode: boolean;
  setFastMode: (v: boolean) => void;

  sessionId: string | null;
  setSessionId: (id: string) => void;

  topK: number;
  setTopK: (k: number) => void;

  uploadStatus: UploadStatus;
  setUploadStatus: (s: UploadStatus) => void;

  logs: string[];
  appendLog: (line: string) => void;
  clearLogs: () => void;

  messages: ChatMessage[];
  addUserMessage: (content: string) => void;
  addAssistantMessage: (content: string, citations: ChunkModel[]) => void;

  rightPanelOpen: boolean;
  openRightPanel: () => void;
  closeRightPanel: () => void;

  activeChunk: ChunkModel | null;
  setActiveChunk: (c: ChunkModel | null) => void;
};

// Use /backend proxy path in Docker, or direct URL for local dev
const getBackendUrl = () => {
  const envUrl = import.meta.env.VITE_BACKEND_URL;
  // If URL contains docker internal hostname, use proxy path instead
  if (envUrl && envUrl.includes("backend:")) {
    return "/backend";
  }
  return envUrl || "http://localhost:8000";
};

export const useErrStore = create<ErrState>((set, get) => ({
  backendUrl: getBackendUrl(),
  isDesktop: true,
  setIsDesktop: (v) => set({ isDesktop: v }),

  fastMode: false,
  setFastMode: (v) => set({ fastMode: v }),

  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

  topK: 8,
  setTopK: (k) => {
    const kk = Math.max(1, Math.min(10, Math.floor(k)));
    set({ topK: kk });
  },

  uploadStatus: "idle",
  setUploadStatus: (s) => set({ uploadStatus: s }),

  logs: [],
  appendLog: (line) => set({ logs: [...get().logs, line].slice(-2000) }),
  clearLogs: () => set({ logs: [] }),

  messages: [],
  addUserMessage: (content) =>
    set({ messages: [...get().messages, { role: "user", content }] }),
  addAssistantMessage: (content, citations) =>
    set({ messages: [...get().messages, { role: "assistant", content, citations }] }),

  rightPanelOpen: false,
  openRightPanel: () => set({ rightPanelOpen: true }),
  closeRightPanel: () => set({ rightPanelOpen: false }),

  activeChunk: null,
  setActiveChunk: (c) => set({ activeChunk: c }),
}));
