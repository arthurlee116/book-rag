import { useEffect, useRef } from "react";
import { Typography } from "antd";
import { CodeOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";

const { Text } = Typography;

const statusConfig: Record<string, { color: string; bg: string }> = {
  idle: { color: "#6b7280", bg: "rgba(107, 114, 128, 0.15)" },
  processing: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)" },
  ready: { color: "#22c55e", bg: "rgba(34, 197, 94, 0.15)" },
  error: { color: "#ef4444", bg: "rgba(239, 68, 68, 0.15)" },
};

/**
 * Terminal Window Component - Displays ingestion logs
 *
 * Features macOS-style title bar with traffic lights
 * and auto-scrolling log output.
 */
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
      className="glass-panel"
      style={{
        padding: 0,
        overflow: "hidden",
        border: "1px solid #1f2937",
      }}
    >
      {/* Title bar - macOS style */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "12px 16px",
          background: "rgba(20, 20, 26, 0.8)",
          borderBottom: "1px solid #1f2937",
        }}
      >
        {/* Traffic lights */}
        <div style={{ display: "flex", gap: 6, marginRight: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#febc2e" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28c840" }} />
        </div>
        <CodeOutlined style={{ color: "#00d4ff", fontSize: "14px", marginRight: 8 }} />
        <Text style={{ color: "#9ca3af", fontSize: 12, flex: 1 }}>Session Logs</Text>
        <span
          className="badge"
          style={{
            fontSize: "10px",
            padding: "3px 8px",
            borderRadius: "4px",
            color: status.color,
            background: status.bg,
            fontWeight: 500,
            border: `1px solid ${status.color}30`,
          }}
        >
          {uploadStatus}
        </span>
      </div>

      {/* Terminal content */}
      <div
        className="terminal-font"
        style={{
          height: isDesktop ? "calc(100vh - 380px)" : 160,
          minHeight: isDesktop ? 180 : 120,
          maxHeight: 300,
          overflow: "auto",
          padding: "14px 16px",
          fontSize: "12px",
          lineHeight: "1.7",
          color: "#9ca3af",
          background: "rgba(5, 5, 7, 0.5)",
        }}
      >
        {!sessionId ? (
          <Text style={{ color: "#6b7280" }}>Upload a document to start...</Text>
        ) : logs.length === 0 ? (
          <Text style={{ color: "#6b7280" }}>Waiting for logs...</Text>
        ) : (
          logs.map((l, idx) => (
            <div key={idx} style={{ color: l.includes("ERROR") ? "#ef4444" : "#9ca3af", marginBottom: "2px" }}>
              <span style={{ color: "#6b7280" }}>$</span> {l}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
