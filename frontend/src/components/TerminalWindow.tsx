import { useEffect, useRef } from "react";
import { Typography } from "antd";
import { CodeOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";
import { themeTokens } from "@/theme";

const { Text } = Typography;

const statusConfig: Record<string, { color: string; bg: string }> = {
  idle: { color: themeTokens.textTertiary, bg: "rgba(140, 133, 128, 0.12)" },
  processing: { color: themeTokens.colorWarning, bg: "rgba(232, 184, 75, 0.12)" },
  ready: { color: themeTokens.colorSuccess, bg: "rgba(107, 191, 122, 0.12)" },
  error: { color: themeTokens.colorError, bg: "rgba(217, 107, 107, 0.12)" },
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
        border: `1px solid ${themeTokens.border}`,
      }}
    >
      {/* Title bar - macOS style */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "12px 16px",
          background: "rgba(26, 25, 24, 0.8)",
          borderBottom: `1px solid ${themeTokens.border}`,
        }}
      >
        {/* Traffic lights */}
        <div style={{ display: "flex", gap: 6, marginRight: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#febc2e" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28c840" }} />
        </div>
        <CodeOutlined style={{ color: themeTokens.accentPrimary, fontSize: "14px", marginRight: 8 }} />
        <Text style={{ color: themeTokens.textSecondary, fontSize: 12, flex: 1 }}>Session Logs</Text>
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
          color: themeTokens.textSecondary,
          background: "rgba(17, 17, 16, 0.5)",
        }}
      >
        {!sessionId ? (
          <Text style={{ color: themeTokens.textTertiary }}>Upload a document to start...</Text>
        ) : logs.length === 0 ? (
          <Text style={{ color: themeTokens.textTertiary }}>Waiting for logs...</Text>
        ) : (
          logs.map((l, idx) => (
            <div key={idx} style={{ color: l.includes("ERROR") ? themeTokens.colorError : themeTokens.textSecondary, marginBottom: "2px" }}>
              <span style={{ color: themeTokens.textTertiary }}>$</span> {l}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
