import { Button, Typography } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";

const { Text } = Typography;

export function DocumentPanel() {
  const activeChunk = useErrStore((s) => s.activeChunk);
  const closeRightPanel = useErrStore((s) => s.closeRightPanel);
  const isDesktop = useErrStore((s) => s.isDesktop);

  return (
    <div
      style={{
        background: "#1c1c1e",
        borderRadius: 12,
        overflow: "hidden",
        height: isDesktop ? "calc(100vh - 140px)" : "auto",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 20px",
          borderBottom: "1px solid #2c2c2e",
        }}
      >
        <Text strong style={{ color: "#f5f5f7", fontSize: 13 }}>Document</Text>
        <Button
          type="text"
          icon={<CloseOutlined />}
          onClick={closeRightPanel}
          size="small"
          style={{ color: "#6e6e73" }}
        />
      </div>

      {/* Content */}
      <div style={{ padding: 20, flex: 1, overflow: "auto" }}>
        {!activeChunk ? (
          <Text style={{ color: "#6e6e73" }}>
            Click a citation to view context.
          </Text>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Previous context */}
            {activeChunk.prev_content && (
              <div
                style={{
                  padding: 14,
                  background: "#2c2c2e",
                  borderRadius: 10,
                  color: "#6e6e73",
                  fontSize: 13,
                  lineHeight: 1.7,
                }}
              >
                {activeChunk.prev_content}
              </div>
            )}

            {/* Current chunk - highlighted */}
            <div
              style={{
                padding: 14,
                background: "rgba(99, 102, 241, 0.1)",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                borderRadius: 10,
              }}
            >
              <Text
                style={{
                  display: "block",
                  color: "#818cf8",
                  fontSize: 11,
                  fontWeight: 500,
                  marginBottom: 8,
                  textTransform: "uppercase",
                  letterSpacing: 0.5,
                }}
              >
                Retrieved Passage
              </Text>
              <div style={{ color: "#f5f5f7", fontSize: 14, lineHeight: 1.7 }}>
                {activeChunk.content}
              </div>
            </div>

            {/* Next context */}
            {activeChunk.next_content && (
              <div
                style={{
                  padding: 14,
                  background: "#2c2c2e",
                  borderRadius: 10,
                  color: "#6e6e73",
                  fontSize: 13,
                  lineHeight: 1.7,
                }}
              >
                {activeChunk.next_content}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
