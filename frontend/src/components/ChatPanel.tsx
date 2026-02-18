import { useEffect, useMemo, useRef, useState, ReactNode } from "react";
import { Button, Input, Select, Typography, Alert, Space, Modal } from "antd";
import { SendOutlined, DownloadOutlined, ThunderboltOutlined, MessageOutlined, ClearOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";
import type { ChunkModel } from "@/lib/types";

const { Text } = Typography;

/**
 * Render text with clickable citation buttons
 */
function renderWithCitationButtons(
  text: string,
  citations: ChunkModel[] | undefined,
  onClick: (n: number) => void
): ReactNode[] {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((p, idx) => {
    const m = p.match(/^\[(\d+)\]$/);
    if (m) {
      const n = parseInt(m[1], 10);
      const disabled = !citations || n < 1 || n > citations.length;
      return (
        <span
          key={idx}
          onClick={() => !disabled && onClick(n)}
          style={{
            display: "inline-block",
            padding: "2px 6px",
            margin: "0 2px",
            fontSize: "11px",
            fontWeight: 500,
            borderRadius: "4px",
            background: disabled ? "#1f2937" : "rgba(0, 212, 255, 0.15)",
            color: disabled ? "#6b7280" : "#00d4ff",
            cursor: disabled ? "not-allowed" : "pointer",
            transition: "all 0.15s",
            border: disabled ? "1px solid #1f2937" : "1px solid rgba(0, 212, 255, 0.3)",
          }}
        >
          [{n}]
        </span>
      );
    }
    return <span key={idx} style={{ whiteSpace: "pre-wrap" }}>{p}</span>;
  });
}

/**
 * Chat Panel Component - Enhanced with new styling
 */
export function ChatPanel() {
  const backendUrl = useErrStore((s) => s.backendUrl);
  const sessionId = useErrStore((s) => s.sessionId);
  const topK = useErrStore((s) => s.topK);
  const setTopK = useErrStore((s) => s.setTopK);
  const fastMode = useErrStore((s) => s.fastMode);
  const setFastMode = useErrStore((s) => s.setFastMode);
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const messages = useErrStore((s) => s.messages);
  const addUserMessage = useErrStore((s) => s.addUserMessage);
  const addAssistantMessage = useErrStore((s) => s.addAssistantMessage);
  const openRightPanel = useErrStore((s) => s.openRightPanel);
  const setActiveChunk = useErrStore((s) => s.setActiveChunk);
  const isDesktop = useErrStore((s) => s.isDesktop);
  const clearChat = useErrStore((s) => s.clearChat);

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scrollAreaRef = useRef<HTMLDivElement | null>(null);
  const prevMessageCountRef = useRef(0);

  const canChat = useMemo(
    () => !!sessionId && uploadStatus === "ready" && !busy,
    [busy, sessionId, uploadStatus]
  );

  useEffect(() => {
    if (messages.length === 0) {
      prevMessageCountRef.current = 0;
      return;
    }
    if (messages.length === prevMessageCountRef.current) return;
    prevMessageCountRef.current = messages.length;

    const last = messages[messages.length - 1];
    if (last?.role !== "assistant") return;

    requestAnimationFrame(() => {
      const el = scrollAreaRef.current;
      if (!el) return;
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    });
  }, [messages]);

  const onSend = async () => {
    if (!canChat) return;
    const q = input.trim();
    if (!q) return;

    setError(null);
    setBusy(true);
    setInput("");
    addUserMessage(q);

    try {
      const resp = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: q, top_k: topK, fast_mode: fastMode }),
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
    } catch (err) {
      setBusy(false);
      setError(err instanceof Error ? err.message : "Chat failed");
    }
  };

  const onExport = async () => {
    if (!sessionId) return;
    try {
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
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  const onClear = () => {
    Modal.confirm({
      title: "清除聊天记录",
      content: "确定要清除聊天记录吗？检索数据将保留。",
      okText: "确定",
      cancelText: "取消",
      onOk: async () => {
        try {
          await clearChat();
        } catch (err) {
          setError(err instanceof Error ? err.message : "清除失败");
        }
      },
    });
  };

  const onCitationClick = (msgIndex: number, n: number) => {
    const msg = messages[msgIndex];
    const chunk = msg.citations?.[n - 1] ?? null;
    if (!chunk) return;
    setActiveChunk(chunk);
    openRightPanel();
  };

  return (
    <div
      className="glass-panel"
      style={{
        padding: "20px",
        height: isDesktop ? "calc(100vh - 120px)" : "auto",
        display: "flex",
        flexDirection: "column",
        background: "rgba(13, 13, 18, 0.7)",
        backdropFilter: "blur(12px)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          paddingBottom: "12px",
          borderBottom: "1px solid #1f2937",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <MessageOutlined style={{ color: "#00d4ff", fontSize: "16px" }} />
          <Text strong style={{ color: "#e5e5e5", fontSize: "14px" }}>
            Chat
          </Text>
        </div>
        <Space size={8}>
          <Button
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => setFastMode(!fastMode)}
            disabled={busy}
            style={{
              background: fastMode ? "rgba(245, 158, 11, 0.15)" : "#14141a",
              borderColor: fastMode ? "#f59e0b" : "#1f2937",
              color: fastMode ? "#f59e0b" : "#9ca3af",
              height: "32px",
            }}
          >
            Fast
          </Button>
          <Select
            size="small"
            value={topK}
            onChange={setTopK}
            disabled={busy}
            aria-label="Top K"
            style={{ width: 75 }}
            options={[
              { value: 5, label: "Top 5" },
              { value: 8, label: "Top 8" },
              { value: 10, label: "Top 10" },
            ]}
          />
          <Button
            size="small"
            icon={<ClearOutlined />}
            onClick={onClear}
            disabled={!sessionId || busy || uploadStatus !== "ready"}
            style={{
              background: "#14141a",
              borderColor: "#1f2937",
              color: "#9ca3af",
              height: "32px",
            }}
          >
            Clear
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={onExport}
            disabled={!sessionId}
            style={{
              background: "#14141a",
              borderColor: "#1f2937",
              color: "#9ca3af",
              height: "32px",
            }}
          >
            Export
          </Button>
        </Space>
      </div>

      {/* Messages */}
      <div
        ref={scrollAreaRef}
        style={{
          flex: isDesktop ? 1 : undefined,
          height: isDesktop ? undefined : 320,
          overflow: "auto",
          marginBottom: "16px",
          padding: "16px",
          background: "rgba(13, 13, 18, 0.5)",
          borderRadius: "10px",
          border: "1px solid #1f2937",
          minHeight: "200px",
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              minHeight: "150px",
              gap: "12px",
            }}
          >
            <div
              style={{
                fontSize: "40px",
                opacity: 0.5,
              }}
            >
              💬
            </div>
            <Text style={{ color: "#6b7280", fontSize: "13px", textAlign: "center" }}>
              Upload a document, wait for "ready", then ask a question.
            </Text>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  maxWidth: "85%",
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  animation: "fadeInUp 0.3s ease",
                }}
              >
                <div
                  style={{
                    padding: "12px 16px",
                    borderRadius: "12px",
                    background: m.role === "user"
                      ? "linear-gradient(135deg, #00d4ff 0%, #3b82f6 100%)"
                      : "#14141a",
                    color: "#e5e5e5",
                    fontSize: "14px",
                    lineHeight: "1.6",
                    boxShadow: m.role === "user"
                      ? "0 2px 8px rgba(0, 212, 255, 0.2)"
                      : "0 2px 8px rgba(0, 0, 0, 0.2)",
                  }}
                >
                  {m.role === "assistant"
                    ? renderWithCitationButtons(m.content, m.citations, (n) => onCitationClick(idx, n))
                    : m.content}
                </div>
                <Text
                  style={{
                    display: "block",
                    marginTop: "4px",
                    fontSize: "11px",
                    color: "#6b7280",
                    marginLeft: m.role === "user" ? "0" : "4px",
                    marginRight: m.role === "user" ? "4px" : "0",
                    textAlign: m.role === "user" ? "right" : "left",
                  }}
                >
                  {m.role === "user" ? "You" : "ERR"}
                </Text>
              </div>
            ))}
            {busy && (
              <div
                style={{
                  maxWidth: "85%",
                  alignSelf: "flex-start",
                  animation: "fadeIn 0.3s ease",
                }}
              >
                <div
                  style={{
                    padding: "12px 16px",
                    borderRadius: "12px",
                    background: "#14141a",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <span
                    className="status-dot processing"
                    style={{ margin: 0 }}
                  />
                  <Text style={{ color: "#6b7280", fontSize: "13px" }}>
                    Thinking…
                  </Text>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <Alert
          type="error"
          message={error}
          style={{
            marginBottom: "12px",
            background: "rgba(239, 68, 68, 0.1)",
            borderColor: "rgba(239, 68, 68, 0.3)",
          }}
          showIcon
        />
      )}

      {/* Input */}
      <div style={{ display: "flex", gap: "10px" }}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={onSend}
          placeholder={uploadStatus !== "ready" ? "Upload and wait..." : "Ask a question..."}
          disabled={!canChat}
          style={{
            flex: 1,
            background: "#0d0d12",
            border: "1px solid #1f2937",
            color: "#e5e5e5",
          }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={onSend}
          disabled={!canChat}
          style={{
            height: "42px",
            background: canChat ? "linear-gradient(135deg, #00d4ff 0%, #3b82f6 100%)" : undefined,
            border: "none",
          }}
        >
          Send
        </Button>
      </div>
    </div>
  );
}
