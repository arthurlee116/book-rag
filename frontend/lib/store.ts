"use client";

import { create } from "zustand";
import type { ChatMessage, ChunkModel } from "@/lib/types";

type UploadStatus = "idle" | "processing" | "ready" | "error";

type ErrState = {
  backendUrl: string;
  isDesktop: boolean;
  setIsDesktop: (v: boolean) => void;

  sessionId: string | null;
  setSessionId: (id: string) => void;

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

export const useErrStore = create<ErrState>((set, get) => ({
  backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
  isDesktop: true,
  setIsDesktop: (v) => set({ isDesktop: v }),

  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

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
  setActiveChunk: (c) => set({ activeChunk: c })
}));

