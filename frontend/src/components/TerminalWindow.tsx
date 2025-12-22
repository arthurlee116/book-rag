import { useEffect, useRef } from "react";
import { Typography } from "antd";
import { useErrStore } from "@/lib/store";

const { Text } = Typography;

const statusConfig: Record<string, { color: string; bg: string }> = {
  idle: { color: "#8e8e93", bg: "#3a3a3c" },
  processing: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)" },
  ready: { color: "#22c55e", bg: "rgba(34, 197, 94, 0.15)" },
  error: { color: "#ef4444", bg: "rgba(239, 68, 68, 0.15)" },
};

export function TerminalWindow() {
  const backendUrl = useErrStore((s) => s.backendUrl);
  const sessionId = useErrStore((s) => s.sessionId);
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const logs = useErrStore((s) => s.logs);
  const appendLog = useErrStore((s) => s.appendLog);
  const setUploadStatus = useErrStore((s) => s.setUploadStatus);
  const isDesktop = useErrStore((s) => s.isDesktop);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const status = statusConfig[uploadStatus] || statusConfig.idle;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  useEffect(() => {
    if (!sessionId) return;

    const es = new EventSource(`${backendUrl}/api/logs/${sessionId}`);
    es.addEventListener("message", (evt) => {
      const line = (evt as MessageEvent).data as string;
      if (line) appendLog(line);
    });
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
    <div
      style={{
        background: "#1c1c1e",
        borderRadius: 12,
        overflow: "hidden",
        border: "1px solid #2c2c2e",
      }}
    >
      {/* Title bar - macOS style */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "10px 14px",
          background: "#2c2c2e",
          borderBottom: "1px solid #3a3a3c",
        }}
      >
        {/* Traffic lights */}
        <div style={{ display: "flex", gap: 6, marginRight: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#febc2e" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28c840" }} />
        </div>
        <Text style={{ color: "#a1a1a6", fontSize: 12, flex: 1 }}>Session Logs</Text>
        <span
          style={{
            fontSize: 11,
            padding: "2px 8px",
            borderRadius: 4,
            color: status.color,
            background: status.bg,
            fontWeight: 500,
          }}
        >
          {uploadStatus}
        </span>
      </div>

      {/* Terminal content */}
      <div
        className="terminal-font"
        style={{
          height: isDesktop ? "calc(100vh - 340px)" : 160,
          minHeight: isDesktop ? 200 : 120,
          overflow: "auto",
          padding: 14,
          fontSize: 12,
          lineHeight: 1.7,
          color: "#a1a1a6",
        }}
      >
        {!sessionId ? (
          <Text style={{ color: "#8e8e93" }}>Upload a document to start...</Text>
        ) : logs.length === 0 ? (
          <Text style={{ color: "#8e8e93" }}>Waiting for logs...</Text>
        ) : (
          logs.map((l, idx) => (
            <div key={idx} style={{ color: l.includes("ERROR") ? "#ef4444" : "#a1a1a6" }}>
              <span style={{ color: "#8e8e93" }}>$</span> {l}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
