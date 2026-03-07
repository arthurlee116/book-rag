import { Button, Typography } from "antd";
import { CloseOutlined, FileTextOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";
import { themeTokens } from "@/theme";

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
        border: `1px solid ${themeTokens.border}`,
        background: themeTokens.surfaceContainerSolid,
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
          borderBottom: `1px solid ${themeTokens.border}`,
          background: themeTokens.surfaceContainer,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <FileTextOutlined style={{ color: themeTokens.accentPrimary, fontSize: "14px" }} />
          <Text strong style={{ color: themeTokens.textPrimary, fontSize: "14px" }}>Document</Text>
        </div>
        <Button
          type="text"
          icon={<CloseOutlined />}
          onClick={closeRightPanel}
          size="small"
          style={{ color: themeTokens.textSecondary }}
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
            <FileTextOutlined style={{ fontSize: "32px", color: themeTokens.borderQuaternary }} />
            <Text style={{ color: themeTokens.textTertiary, fontSize: "13px", textAlign: "center" }}>
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
                  background: themeTokens.surfaceContainer,
                  borderRadius: "12px",
                  border: `1px solid ${themeTokens.border}`,
                  color: themeTokens.textTertiary,
                  fontSize: "13px",
                  lineHeight: "1.7",
                }}
              >
                <Text
                  style={{
                    display: "block",
                    color: themeTokens.textTertiary,
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
                background: themeTokens.surfaceAccentSubtle,
                border: "1px solid rgba(212, 145, 92, 0.2)",
                borderRadius: "12px",
                boxShadow: "0 0 20px rgba(212, 145, 92, 0.08)",
              }}
            >
              <Text
                style={{
                  display: "block",
                  color: themeTokens.accentPrimary,
                  fontSize: "11px",
                  fontWeight: 600,
                  marginBottom: "10px",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Retrieved Passage
              </Text>
              <div style={{ color: themeTokens.textPrimary, fontSize: "14px", lineHeight: "1.7" }}>
                {activeChunk.content}
              </div>
            </div>

            {/* Next context */}
            {activeChunk.next_content && (
              <div
                style={{
                  padding: "14px",
                  background: themeTokens.surfaceContainer,
                  borderRadius: "12px",
                  border: `1px solid ${themeTokens.border}`,
                  color: themeTokens.textTertiary,
                  fontSize: "13px",
                  lineHeight: "1.7",
                }}
              >
                <Text
                  style={{
                    display: "block",
                    color: themeTokens.textTertiary,
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
                  background: themeTokens.surfaceContainer,
                  borderRadius: "10px",
                  border: `1px solid ${themeTokens.border}`,
                }}
              >
                <Text
                  style={{
                    display: "block",
                    color: themeTokens.textTertiary,
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
                    <Text style={{ color: themeTokens.textTertiary, fontSize: "11px" }}>{key}: </Text>
                    <Text style={{ color: themeTokens.textSecondary, fontSize: "11px" }}>
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
