"use client";

import { useMemo, useState } from "react";
import { Download, Send } from "lucide-react";

import { useErrStore } from "@/lib/store";
import type { ChunkModel } from "@/lib/types";

function renderWithCitationButtons(
  text: string,
  citations: ChunkModel[] | undefined,
  onClick: (n: number) => void
) {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((p, idx) => {
    const m = p.match(/^\[(\d+)\]$/);
    if (m) {
      const n = parseInt(m[1], 10);
      const disabled = !citations || n < 1 || n > citations.length;
      return (
        <button
          key={idx}
          type="button"
          disabled={disabled}
          onClick={() => onClick(n)}
          className="mx-0.5 inline-flex items-center rounded border border-indigo-500/60 bg-indigo-500/10 px-1.5 py-0.5 text-xs text-indigo-200 hover:bg-indigo-500/20 disabled:opacity-40"
        >
          [{n}]
        </button>
      );
    }
    return (
      <span key={idx} className="whitespace-pre-wrap">
        {p}
      </span>
    );
  });
}

export function ChatPanel() {
  const backendUrl = useErrStore((s) => s.backendUrl);
  const sessionId = useErrStore((s) => s.sessionId);
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const messages = useErrStore((s) => s.messages);
  const addUserMessage = useErrStore((s) => s.addUserMessage);
  const addAssistantMessage = useErrStore((s) => s.addAssistantMessage);
  const openRightPanel = useErrStore((s) => s.openRightPanel);
  const setActiveChunk = useErrStore((s) => s.setActiveChunk);

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canChat = useMemo(
    () => !!sessionId && uploadStatus === "ready" && !busy,
    [busy, sessionId, uploadStatus]
  );

  const onSend = async () => {
    if (!canChat) return;
    const q = input.trim();
    if (!q) return;

    setError(null);
    setBusy(true);
    setInput("");
    addUserMessage(q);

    const resp = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: q, top_k: 5 })
    });

    if (!resp.ok) {
      const msg = await resp.text();
      setBusy(false);
      setError(msg || `Chat failed (${resp.status})`);
      return;
    }

    const data = (await resp.json()) as { answer: string; citations: ChunkModel[] };
    addAssistantMessage(data.answer, data.citations || []);
    setBusy(false);
  };

  const onExport = async () => {
    if (!sessionId) return;
    const resp = await fetch(`${backendUrl}/export/${sessionId}`);
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "err_export.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const onCitationClick = (msgIndex: number, n: number) => {
    const msg = messages[msgIndex];
    const chunk = msg.citations?.[n - 1] ?? null;
    if (!chunk) return;
    setActiveChunk(chunk);
    openRightPanel();
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/30 p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-zinc-200">Chat</div>
        <button
          type="button"
          onClick={onExport}
          disabled={!sessionId}
          className="inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/30 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-900 disabled:opacity-50"
        >
          <Download className="h-4 w-4" />
          Export
        </button>
      </div>

      <div className="mt-3 max-h-[420px] overflow-auto rounded-md border border-zinc-800 bg-zinc-950/40 p-3">
        {messages.length === 0 ? (
          <div className="text-sm text-zinc-500">
            Upload a document, wait for “Ready.”, then ask a question.
          </div>
        ) : (
          <div className="space-y-4 text-sm">
            {messages.map((m, idx) => (
              <div key={idx} className="rounded-md border border-zinc-800 bg-zinc-950/30 p-3">
                <div className="text-xs font-medium text-zinc-400">
                  {m.role === "user" ? "User" : "Assistant"}
                </div>
                <div className="mt-2 text-zinc-100">
                  {m.role === "assistant"
                    ? renderWithCitationButtons(m.content, m.citations, (n) => onCitationClick(idx, n))
                    : m.content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error ? (
        <div className="mt-3 rounded-md border border-red-900/60 bg-red-950/30 p-2 text-xs text-red-200">
          {error}
        </div>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSend();
          }}
          placeholder={
            uploadStatus !== "ready"
              ? "Upload and wait until Ready…"
              : "Ask a question (strictly from the document)…"
          }
          disabled={!canChat}
          className="w-full rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={!canChat}
          className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          Send
        </button>
      </div>
    </div>
  );
}

