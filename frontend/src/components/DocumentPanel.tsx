import { Button, Typography } from "antd";
import { CloseOutlined, FileTextOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";

const { Text } = Typography;

/**
 * Document Panel Component - Displays retrieved passage context
 *
 * Shows previous context, the retrieved chunk (highlighted),
 * and next context for better understanding of cited content.
 */
export function DocumentPanel() {
  const activeChunk = useErrStore((s) => s.activeChunk);
  const closeRightPanel = useErrStore((s) => s.closeRightPanel);
  const isDesktop = useErrStore((s) => s.isDesktop);

  return (
    <div
      className="glass-panel"
      style={{
        padding: 0,
        overflow: "hidden",
        height: isDesktop ? "calc(100vh - 120px)" : "auto",
        display: "flex",
        flexDirection: "column",
        border: "1px solid #1f2937",
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
          padding: "16px 20px",
          borderBottom: "1px solid #1f2937",
          background: "rgba(20, 20, 26, 0.5)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <FileTextOutlined style={{ color: "#00d4ff", fontSize: "14px" }} />
          <Text strong style={{ color: "#e5e5e5", fontSize: "14px" }}>Document</Text>
        </div>
        <Button
          type="text"
          icon={<CloseOutlined />}
          onClick={closeRightPanel}
          size="small"
          style={{ color: "#9ca3af" }}
        />
      </div>

      {/* Content */}
      <div style={{ padding: "20px", flex: 1, overflow: "auto" }}>
        {!activeChunk ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              minHeight: "200px",
              gap: "12px",
            }}
          >
            <FileTextOutlined style={{ fontSize: "32px", color: "#3a3a3c" }} />
            <Text style={{ color: "#6b7280", fontSize: "13px", textAlign: "center" }}>
              Click a citation to view context.
            </Text>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12" }}>
            {/* Previous context */}
            {activeChunk.prev_content && (
              <div
                style={{
                  padding: "14px",
                  background: "rgba(20, 20, 26, 0.5)",
                  borderRadius: "10px",
                  border: "1px solid #1f2937",
                  color: "#6b7280",
                  fontSize: "13px",
                  lineHeight: "1.7",
                }}
              >
                <Text
                  style={{
                    display: "block",
                    color: "#6b7280",
                    fontSize: "10px",
                    fontWeight: 500,
                    marginBottom: "8px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Previous Context
                </Text>
                {activeChunk.prev_content}
              </div>
            )}

            {/* Current chunk - highlighted */}
            <div
              style={{
                padding: "16px",
                background: "rgba(0, 212, 255, 0.08)",
                border: "1px solid rgba(0, 212, 255, 0.25)",
                borderRadius: "10px",
                boxShadow: "0 0 20px rgba(0, 212, 255, 0.1)",
              }}
            >
              <Text
                style={{
                  display: "block",
                  color: "#00d4ff",
                  fontSize: "11px",
                  fontWeight: 600,
                  marginBottom: "10px",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Retrieved Passage
              </Text>
              <div style={{ color: "#e5e5e5", fontSize: "14px", lineHeight: "1.7" }}>
                {activeChunk.content}
              </div>
            </div>

            {/* Next context */}
            {activeChunk.next_content && (
              <div
                style={{
                  padding: "14px",
                  background: "rgba(20, 20, 26, 0.5)",
                  borderRadius: "10px",
                  border: "1px solid #1f2937",
                  color: "#6b7280",
                  fontSize: "13px",
                  lineHeight: "1.7",
                }}
              >
                <Text
                  style={{
                    display: "block",
                    color: "#6b7280",
                    fontSize: "10px",
                    fontWeight: 500,
                    marginBottom: "8px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Next Context
                </Text>
                {activeChunk.next_content}
              </div>
            )}

            {/* Metadata */}
            {activeChunk.metadata && Object.keys(activeChunk.metadata).length > 0 && (
              <div
                style={{
                  padding: "12px",
                  background: "rgba(20, 20, 26, 0.5)",
                  borderRadius: "8px",
                  border: "1px solid #1f2937",
                }}
              >
                <Text
                  style={{
                    display: "block",
                    color: "#6b7280",
                    fontSize: "10px",
                    fontWeight: 500,
                    marginBottom: "8px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Metadata
                </Text>
                {Object.entries(activeChunk.metadata).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: "4px" }}>
                    <Text style={{ color: "#6b7280", fontSize: "11px" }}>{key}: </Text>
                    <Text style={{ color: "#9ca3af", fontSize: "11px" }}>
                      {String(value)}
                    </Text>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
