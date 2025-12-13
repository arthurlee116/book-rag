"use client";

import { useRef, useState } from "react";
import { FileUp, Trash2 } from "lucide-react";

import { useErrStore } from "@/lib/store";

export function UploadPanel() {
  const backendUrl = useErrStore((s) => s.backendUrl);
  const sessionId = useErrStore((s) => s.sessionId);
  const setSessionId = useErrStore((s) => s.setSessionId);
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const setUploadStatus = useErrStore((s) => s.setUploadStatus);
  const clearLogs = useErrStore((s) => s.clearLogs);
  const setActiveChunk = useErrStore((s) => s.setActiveChunk);
  const closeRightPanel = useErrStore((s) => s.closeRightPanel);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canUpload = uploadStatus !== "processing";

  const onUpload = async () => {
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    setError(null);
    clearLogs();
    setActiveChunk(null);
    closeRightPanel();
    setUploadStatus("processing");

    const fd = new FormData();
    fd.append("file", file);

    const resp = await fetch(`${backendUrl}/upload`, {
      method: "POST",
      headers: sessionId ? { "X-Session-Id": sessionId } : {},
      body: fd
    });

    if (!resp.ok) {
      const msg = await resp.text();
      setUploadStatus("error");
      setError(msg || `Upload failed (${resp.status})`);
      return;
    }

    const data = (await resp.json()) as { session_id: string };
    setSessionId(data.session_id);
    setFileName(file.name);
  };

  const onClear = () => {
    if (inputRef.current) inputRef.current.value = "";
    setFileName(null);
    setError(null);
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/30 p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-zinc-200">Single File Mode</div>
          <div className="mt-1 text-xs text-zinc-400">
            Uploading a new file overwrites the previous one for this session.
          </div>
        </div>

        <button
          type="button"
          onClick={onClear}
          className="inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/30 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-900"
        >
          <Trash2 className="h-4 w-4" />
          Clear
        </button>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          onChange={() => setFileName(inputRef.current?.files?.[0]?.name ?? null)}
          className="block w-full cursor-pointer rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-xs text-zinc-200 file:mr-4 file:rounded-md file:border-0 file:bg-zinc-800 file:px-3 file:py-2 file:text-xs file:text-zinc-100"
          accept=".txt,.md,.docx,.epub,.mobi"
          disabled={!canUpload}
        />

        <button
          type="button"
          onClick={onUpload}
          disabled={!canUpload}
          className="inline-flex shrink-0 items-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          <FileUp className="h-4 w-4" />
          Upload
        </button>
      </div>

      <div className="mt-2 text-xs text-zinc-400">
        {fileName ? <span>Selected: {fileName}</span> : <span>No file selected.</span>}
      </div>

      {error ? (
        <div className="mt-2 rounded-md border border-red-900/60 bg-red-950/30 p-2 text-xs text-red-200">
          {error}
        </div>
      ) : null}
    </div>
  );
}

