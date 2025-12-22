import { Suspense, lazy, useEffect } from "react";
import { ConfigProvider, Layout, Typography, Row, Col, theme } from "antd";
import { useErrStore } from "@/lib/store";
import { darkTheme } from "./theme";
import { UploadPanel } from "@/components/UploadPanel";
import { ChatPanel } from "@/components/ChatPanel";
import { TerminalWindow } from "@/components/TerminalWindow";
import { EvaluationPanel } from "@/components/EvaluationPanel";

const { Content } = Layout;
const { Title, Text } = Typography;

const DocumentPanel = lazy(() =>
  import("@/components/DocumentPanel").then((module) => ({ default: module.DocumentPanel })),
);

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
    <ConfigProvider theme={{ ...darkTheme, algorithm: theme.darkAlgorithm }}>
      <Layout style={{ minHeight: "100vh", background: "#000" }}>
        <Content style={{ padding: isDesktop ? "24px 32px" : "16px" }}>
          <div style={{ marginBottom: isDesktop ? 20 : 16 }}>
            <Title level={4} style={{ margin: 0, color: "#f5f5f7", fontWeight: 600, fontSize: isDesktop ? 20 : 18 }}>
              Ephemeral RAG Reader
            </Title>
            <Text style={{ color: "#8e8e93", fontSize: 13 }}>
              Session-based, in-memory only. Strict RAG.
            </Text>
          </div>

          {/* PERF: Keep above-the-fold panels eagerly loaded to avoid a first-load
              chunk waterfall (multiple React.lazy imports request immediately). */}
          {isDesktop ? (
            <Row gutter={20}>
              <Col span={rightPanelOpen ? 6 : 8}>
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <UploadPanel />
                  <TerminalWindow />
                  <EvaluationPanel />
                </div>
              </Col>
              <Col span={rightPanelOpen ? 10 : 16}>
                <ChatPanel />
              </Col>
              {rightPanelOpen && (
                <Col span={8}>
                  <Suspense
                    fallback={
                      <div
                        style={{
                          background: "#1c1c1e",
                          borderRadius: 16,
                          minHeight: 520,
                          opacity: 0.65,
                        }}
                      />
                    }
                  >
                    <DocumentPanel />
                  </Suspense>
                </Col>
              )}
            </Row>
          ) : (
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
                <EvaluationPanel />
                <ChatPanel />
              </div>
            </div>
          )}

          {!isDesktop && rightPanelOpen && (
            <div style={{ marginTop: 16 }}>
              <Suspense
                fallback={
                  <div
                    style={{
                      background: "#1c1c1e",
                      borderRadius: 16,
                      minHeight: 360,
                      opacity: 0.65,
                    }}
                  />
                }
              >
                <DocumentPanel />
              </Suspense>
            </div>
          )}
        </Content>
      </Layout>
    </ConfigProvider>
  );
}
