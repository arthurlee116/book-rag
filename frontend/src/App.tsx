import { Suspense, lazy, useEffect } from "react";
import { ConfigProvider, Layout, Typography, Row, Col, theme } from "antd";
import { useErrStore } from "@/lib/store";
import { darkTheme } from "./theme";

const { Content } = Layout;
const { Title, Text } = Typography;

const UploadPanel = lazy(() =>
  import("@/components/UploadPanel").then((module) => ({ default: module.UploadPanel })),
);
const ChatPanel = lazy(() =>
  import("@/components/ChatPanel").then((module) => ({ default: module.ChatPanel })),
);
const TerminalWindow = lazy(() =>
  import("@/components/TerminalWindow").then((module) => ({ default: module.TerminalWindow })),
);
const DocumentPanel = lazy(() =>
  import("@/components/DocumentPanel").then((module) => ({ default: module.DocumentPanel })),
);
const EvaluationPanel = lazy(() =>
  import("@/components/EvaluationPanel").then((module) => ({ default: module.EvaluationPanel })),
);

function PanelSkeleton({ isDesktop }: { isDesktop: boolean }) {
  return (
    <div style={{ display: "grid", gap: isDesktop ? 16 : 12 }}>
      <div
        style={{
          background: "#1c1c1e",
          height: isDesktop ? 220 : 180,
          borderRadius: 16,
          opacity: 0.65,
        }}
      />
      <div
        style={{
          background: "#1c1c1e",
          height: isDesktop ? 400 : 320,
          borderRadius: 16,
          opacity: 0.65,
        }}
      />
    </div>
  );
}

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
            <Text style={{ color: "#6e6e73", fontSize: 13 }}>
              Session-based, in-memory only. Strict RAG.
            </Text>
          </div>

          <Suspense fallback={<PanelSkeleton isDesktop={isDesktop} />}>
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
          </Suspense>
        </Content>
      </Layout>
    </ConfigProvider>
  );
}
