"use client";

import { useEffect, useRef } from "react";
import { Terminal } from "lucide-react";

import { useErrStore } from "@/lib/store";

export function TerminalWindow() {
  const backendUrl = useErrStore((s) => s.backendUrl);
  const sessionId = useErrStore((s) => s.sessionId);
  const logs = useErrStore((s) => s.logs);
  const appendLog = useErrStore((s) => s.appendLog);
  const setUploadStatus = useErrStore((s) => s.setUploadStatus);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  useEffect(() => {
    if (!sessionId) return;

    const es = new EventSource(`${backendUrl}/api/logs/${sessionId}`);
    es.addEventListener("log", (evt) => {
      const line = (evt as MessageEvent).data as string;
      appendLog(line);
      if (line.includes("Ready.")) setUploadStatus("ready");
      if (line.includes("ERROR")) setUploadStatus("error");
    });
    es.addEventListener("error", () => {
      appendLog("[LOG] (SSE disconnected)");
    });
    return () => es.close();
  }, [appendLog, backendUrl, sessionId, setUploadStatus]);

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-800 bg-black">
      <div className="flex items-center gap-2 border-b border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-200">
        <Terminal className="h-4 w-4" />
        <span className="font-medium">Processing Logs</span>
      </div>
      <div className="max-h-64 overflow-auto px-3 py-2 font-mono text-xs leading-5 text-zinc-100">
        {logs.length === 0 ? (
          <div className="text-zinc-500">Waiting for logs…</div>
        ) : (
          logs.map((l, idx) => (
            <div key={idx} className="whitespace-pre-wrap">
              {"> "} {l}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

