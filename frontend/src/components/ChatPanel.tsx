import { useEffect, useMemo, useRef, useState, ReactNode } from "react";
import { Button, Input, Select, Typography, Alert, Space } from "antd";
import { SendOutlined, DownloadOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";
import type { ChunkModel } from "@/lib/types";

const { Text } = Typography;

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
            padding: "1px 6px",
            margin: "0 2px",
            fontSize: 11,
            fontWeight: 500,
            borderRadius: 4,
            background: disabled ? "#3a3a3c" : "rgba(99, 102, 241, 0.2)",
            color: disabled ? "#6e6e73" : "#818cf8",
            cursor: disabled ? "not-allowed" : "pointer",
            transition: "all 0.15s",
          }}
        >
          [{n}]
        </span>
      );
    }
    return <span key={idx} style={{ whiteSpace: "pre-wrap" }}>{p}</span>;
  });
}

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
    <div style={{
      background: "#1c1c1e",
      borderRadius: 12,
      padding: 16,
      height: isDesktop ? "calc(100vh - 140px)" : "auto",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Text strong style={{ color: "#f5f5f7", fontSize: 13 }}>Chat</Text>
        <Space size={8}>
          <Button
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => setFastMode(!fastMode)}
            disabled={busy}
            style={{
              background: fastMode ? "rgba(245, 158, 11, 0.15)" : "#3a3a3c",
              borderColor: "transparent",
              color: fastMode ? "#f59e0b" : "#a1a1a6",
            }}
          >
            Fast
          </Button>
          <Select
            size="small"
            value={topK}
            onChange={setTopK}
            disabled={busy}
            style={{ width: 75 }}
            options={[
              { value: 5, label: "Top 5" },
              { value: 8, label: "Top 8" },
              { value: 10, label: "Top 10" },
            ]}
          />
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={onExport}
            disabled={!sessionId}
            style={{ background: "#3a3a3c", borderColor: "transparent" }}
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
          height: isDesktop ? undefined : 280,
          overflow: "auto",
          marginBottom: 16,
          padding: 16,
          background: "#2c2c2e",
          borderRadius: 10,
        }}
      >
        {messages.length === 0 ? (
          <Text style={{ color: "#6e6e73" }}>
            Upload a document, wait for "ready", then ask a question.
          </Text>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  maxWidth: "85%",
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: 12,
                    background: m.role === "user" ? "#6366f1" : "#2c2c2e",
                    color: "#f5f5f7",
                    fontSize: 14,
                    lineHeight: 1.6,
                  }}
                >
                  {m.role === "assistant"
                    ? renderWithCitationButtons(m.content, m.citations, (n) => onCitationClick(idx, n))
                    : m.content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <Alert type="error" message={error} style={{ marginBottom: 12 }} showIcon />}

      {/* Input */}
      <div style={{ display: "flex", gap: 10 }}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={onSend}
          placeholder={uploadStatus !== "ready" ? "Upload and wait..." : "Ask a question..."}
          disabled={!canChat}
          style={{ flex: 1 }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={onSend}
          disabled={!canChat}
        >
          Send
        </Button>
      </div>
    </div>
  );
}
