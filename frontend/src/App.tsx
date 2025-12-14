import { useEffect } from "react";
import { Layout, Typography, Alert, Row, Col } from "antd";
import { UploadPanel } from "@/components/UploadPanel";
import { ChatPanel } from "@/components/ChatPanel";
import { TerminalWindow } from "@/components/TerminalWindow";
import { DocumentPanel } from "@/components/DocumentPanel";
import { useErrStore } from "@/lib/store";

const { Content } = Layout;
const { Title, Text } = Typography;

function useIsDesktop() {
  const setIsDesktop = useErrStore((s) => s.setIsDesktop);

  useEffect(() => {
    const check = () => setIsDesktop(window.innerWidth >= 900);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, [setIsDesktop]);

  return useErrStore((s) => s.isDesktop);
}

export default function App() {
  const isDesktop = useIsDesktop();
  const rightPanelOpen = useErrStore((s) => s.rightPanelOpen);

  return (
    <Layout style={{ minHeight: "100vh", background: "#000" }}>
      <Content style={{ padding: isDesktop ? "24px 32px" : "16px" }}>
        {/* Header */}
        <div style={{ marginBottom: isDesktop ? 20 : 16 }}>
          <Title level={4} style={{ margin: 0, color: "#f5f5f7", fontWeight: 600, fontSize: isDesktop ? 20 : 18 }}>
            Ephemeral RAG Reader
          </Title>
          <Text style={{ color: "#6e6e73", fontSize: 13 }}>
            Session-based, in-memory only. Strict RAG.
          </Text>
        </div>

        {isDesktop ? (
          /* Desktop: 横向三栏布局 */
          <Row gutter={20}>
            <Col span={rightPanelOpen ? 6 : 8}>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <UploadPanel />
                <TerminalWindow />
              </div>
            </Col>
            <Col span={rightPanelOpen ? 10 : 16}>
              <ChatPanel />
            </Col>
            {rightPanelOpen && (
              <Col span={8}>
                <DocumentPanel />
              </Col>
            )}
          </Row>
        ) : (
          /* Mobile: 竖向单栏布局 */
          <div
            style={{
              background: "#1c1c1e",
              borderRadius: 16,
              overflow: "hidden",
            }}
          >
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
              <UploadPanel />
              <TerminalWindow />
              <ChatPanel />
            </div>
          </div>
        )}

        {/* Mobile Document Panel - 作为底部抽屉 */}
        {!isDesktop && rightPanelOpen && (
          <div style={{ marginTop: 16 }}>
            <DocumentPanel />
          </div>
        )}
      </Content>
    </Layout>
  );
}
