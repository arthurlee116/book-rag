import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import { ConfigProvider, Drawer, Layout, theme } from "antd";
import { useErrStore } from "@/lib/store";
import { darkTheme } from "./theme";
import { HeroSection } from "@/components/HeroSection";

const { Content } = Layout;

const DocumentPanel = lazy(() =>
  import("@/components/DocumentPanel").then((module) => ({ default: module.DocumentPanel })),
);
const UploadPanel = lazy(() =>
  import("@/components/UploadPanel").then((module) => ({ default: module.UploadPanel })),
);
const ChatPanel = lazy(() =>
  import("@/components/ChatPanel").then((module) => ({ default: module.ChatPanel })),
);
const TerminalWindow = lazy(() =>
  import("@/components/TerminalWindow").then((module) => ({ default: module.TerminalWindow })),
);
const EvaluationPanel = lazy(() =>
  import("@/components/EvaluationPanel").then((module) => ({ default: module.EvaluationPanel })),
);

const LEFT_PANEL_STORAGE_KEY = "err:leftPanelWidth";
const DEFAULT_LEFT_PANEL_WIDTH = 360;
const MIN_LEFT_PANEL_WIDTH = 300;
const MAX_LEFT_PANEL_WIDTH = 520;
const LEFT_RESIZER_WIDTH = 14;
const MIN_CHAT_WIDTH = 520;
const COMPACT_DESKTOP_MAX_WIDTH = 1200;
const APP_MAX_WIDTH = 1600;
const RIGHT_PANEL_WIDTH = 380;
const RIGHT_GAP_WIDTH = 20;

interface PanelFallbackProps {
  height?: number | string;
  label: string;
}

function PanelFallback({ height = 180, label }: PanelFallbackProps) {
  return (
    <div
      style={{
        background: "#0d0d12",
        borderRadius: "12px",
        border: "1px solid #1f2937",
        minHeight: typeof height === "number" ? `${height}px` : height,
        opacity: 0.5,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <span style={{ color: "#6b7280", fontSize: "13px" }}>{label}</span>
    </div>
  );
}

/**
 * Hook to detect desktop breakpoint
 */
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

function useWindowWidth() {
  const [width, setWidth] = useState(() => (typeof window === "undefined" ? 1024 : window.innerWidth));

  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth);
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return width;
}

/**
 * Animated transition component for hero → app state
 */
interface AppTransitionProps {
  show: boolean;
  children: React.ReactNode;
}

function AppTransition({ show, children }: AppTransitionProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (show) {
      setIsVisible(true);
    }
  }, [show]);

  if (!show) return null;

  return (
    <div
      className="animate-fade-in"
      style={{
        opacity: isVisible ? 1 : 0,
        transition: "opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      {children}
    </div>
  );
}

/**
 * Main App Component
 *
 * Displays HeroSection initially, then transitions to the app interface
 * after the first document upload completes.
 */
export default function App() {
  const isDesktop = useIsDesktop();
  const windowWidth = useWindowWidth();
  const rightPanelOpen = useErrStore((s) => s.rightPanelOpen);
  const closeRightPanel = useErrStore((s) => s.closeRightPanel);
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const sessionId = useErrStore((s) => s.sessionId);

  // Show hero section if no session exists or upload hasn't completed
  const showHero = !sessionId || uploadStatus === "idle";
  const showApp = !showHero;

  const [leftPanelWidth, setLeftPanelWidth] = useState(() => {
    if (typeof window === "undefined") return DEFAULT_LEFT_PANEL_WIDTH;
    const raw = window.localStorage.getItem(LEFT_PANEL_STORAGE_KEY);
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) ? Math.min(MAX_LEFT_PANEL_WIDTH, Math.max(MIN_LEFT_PANEL_WIDTH, n)) : DEFAULT_LEFT_PANEL_WIDTH;
  });
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const gridRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(LEFT_PANEL_STORAGE_KEY, String(leftPanelWidth));
  }, [leftPanelWidth]);

  const isCompactDesktop = isDesktop && windowWidth < COMPACT_DESKTOP_MAX_WIDTH;
  const showRightInGrid = rightPanelOpen && isDesktop && !isCompactDesktop;
  const showRightDrawer = rightPanelOpen && isCompactDesktop;

  const gridTemplateColumns = useMemo(() => {
    if (!isDesktop) return undefined;
    if (showRightInGrid) {
      return `${leftPanelWidth}px ${LEFT_RESIZER_WIDTH}px minmax(0, 1fr) ${RIGHT_GAP_WIDTH}px ${RIGHT_PANEL_WIDTH}px`;
    }
    return `${leftPanelWidth}px ${LEFT_RESIZER_WIDTH}px minmax(0, 1fr)`;
  }, [isDesktop, leftPanelWidth, showRightInGrid]);

  useEffect(() => {
    if (!isResizingLeft) return;

    const prevUserSelect = document.body.style.userSelect;
    const prevCursor = document.body.style.cursor;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";

    const onMove = (e: MouseEvent) => {
      const el = gridRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();

      const raw = e.clientX - rect.left;
      const rightReservation = showRightInGrid ? RIGHT_GAP_WIDTH + RIGHT_PANEL_WIDTH : 0;
      const maxByLayout = rect.width - LEFT_RESIZER_WIDTH - rightReservation - MIN_CHAT_WIDTH;
      const effectiveMax = Math.max(MIN_LEFT_PANEL_WIDTH, Math.min(MAX_LEFT_PANEL_WIDTH, maxByLayout));
      const next = Math.min(effectiveMax, Math.max(MIN_LEFT_PANEL_WIDTH, raw));
      setLeftPanelWidth(next);
    };

    const onUp = () => setIsResizingLeft(false);

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      document.body.style.userSelect = prevUserSelect;
      document.body.style.cursor = prevCursor;
    };
  }, [isResizingLeft, showRightInGrid]);

  return (
    <ConfigProvider theme={{ ...darkTheme, algorithm: theme.darkAlgorithm }}>
      <Layout
        style={{
          minHeight: "100vh",
          background: "#050507",
          position: "relative",
        }}
      >
        {/* Background Effects */}
        <div
          style={{
            position: "fixed",
            inset: 0,
            background:
              "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0, 212, 255, 0.05), transparent)",
            pointerEvents: "none",
            zIndex: 0,
          }}
        />

        <Content style={{ position: "relative", zIndex: 1 }}>
          {/* Hero Section - Landing Page */}
          {showHero && (
            <div style={{ position: "relative" }}>
              <HeroSection />
              {/* Upload Panel Overlay on Hero */}
              <div
                className="animate-scale-in"
                style={{
                  maxWidth: "600px",
                  margin: "0 auto",
                  padding: "0 20px",
                  marginTop: "-40px",
                  position: "relative",
                  zIndex: 10,
                }}
              >
                <Suspense fallback={<PanelFallback label="Loading upload…" height={220} />}>
                  <UploadPanel />
                </Suspense>
              </div>
            </div>
          )}

          {/* App Interface - After Upload */}
          <AppTransition show={showApp}>
            <div
              className="animate-fade-in"
              style={{
                padding: isDesktop ? "24px 32px" : "16px",
                minHeight: "100vh",
              }}
            >
              {/* App Header */}
              <div
                className="animate-fade-in-up"
                style={{
                  marginBottom: isDesktop ? "24px" : "16px",
                  opacity: 0,
                  animationDelay: "0.1s",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: isDesktop ? "center" : "flex-start",
                    flexWrap: "wrap",
                    gap: "12px",
                  }}
                >
                  <div>
                    <h1
                      style={{
                        margin: 0,
                        fontSize: isDesktop ? "22px" : "18px",
                        fontWeight: 600,
                        background: "linear-gradient(135deg, #00d4ff 0%, #3b82f6 100%)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                        backgroundClip: "text",
                      }}
                    >
                      ERR — Ephemeral RAG Reader
                    </h1>
                    <p
                      style={{
                        margin: "4px 0 0",
                        fontSize: "13px",
                        color: "#6b7280",
                      }}
                    >
                      Session: {sessionId?.slice(0, 8)}…
                    </p>
                  </div>

                  {uploadStatus === "ready" && (
                    <div className="badge">
                      <span className="status-dot ready" />
                      Ready for questions
                    </div>
                  )}
                </div>
              </div>

              {/* Main Layout */}
              {isDesktop ? (
                <div
                  className="animate-fade-in"
                  style={{
                    opacity: 0,
                    animationDelay: "0.2s",
                    display: "grid",
                    gridTemplateColumns,
                    gap: 0,
                    alignItems: "start",
                    maxWidth: APP_MAX_WIDTH,
                    margin: "0 auto",
                  }}
                  ref={gridRef}
                >
                  {/* Left Column */}
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "16px",
                      position: "sticky",
                      top: "24px",
                      gridColumn: 1,
                    }}
                  >
                    <Suspense fallback={<PanelFallback label="Loading upload…" height={220} />}>
                      <UploadPanel />
                    </Suspense>
                    <Suspense fallback={<PanelFallback label="Loading logs…" height={140} />}>
                      <TerminalWindow />
                    </Suspense>
                    <Suspense fallback={<PanelFallback label="Loading evaluation…" height={180} />}>
                      <EvaluationPanel />
                    </Suspense>
                  </div>

                  {/* Left Resizer */}
                  <div
                    role="separator"
                    aria-orientation="vertical"
                    aria-label="Resize sidebar"
                    onMouseDown={() => setIsResizingLeft(true)}
                    onDoubleClick={() => setLeftPanelWidth(DEFAULT_LEFT_PANEL_WIDTH)}
                    style={{
                      gridColumn: 2,
                      height: "calc(100vh - 48px)",
                      position: "sticky",
                      top: "24px",
                      cursor: "col-resize",
                      display: "flex",
                      alignItems: "stretch",
                      justifyContent: "center",
                      padding: "0 4px",
                    }}
                  >
                    <div
                      style={{
                        width: "2px",
                        borderRadius: "999px",
                        background: isResizingLeft ? "rgba(0, 212, 255, 0.7)" : "rgba(31, 41, 55, 0.9)",
                        boxShadow: isResizingLeft ? "0 0 12px rgba(0, 212, 255, 0.35)" : "none",
                        transition: "background 120ms ease, box-shadow 120ms ease",
                      }}
                    />
                  </div>

                  {/* Center Column - Chat */}
                  <div style={{ gridColumn: 3, minWidth: 0 }}>
                    <Suspense fallback={<PanelFallback label="Loading chat…" height="calc(100vh - 120px)" />}>
                      <ChatPanel />
                    </Suspense>
                  </div>

                  {/* Right Column - Document (conditional) */}
                  {showRightInGrid && (
                    <div style={{ gridColumn: 4 }} />
                  )}

                  {showRightInGrid && (
                    <div
                      style={{
                        gridColumn: 5,
                        position: "sticky",
                        top: "24px",
                        height: "calc(100vh - 48px)",
                      }}
                    >
                      <Suspense
                        fallback={
                          <div
                            style={{
                              background: "#0d0d12",
                              borderRadius: "12px",
                              height: "100%",
                              opacity: 0.5,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              border: "1px solid #1f2937",
                            }}
                          >
                            <span style={{ color: "#6b7280", fontSize: "13px" }}>Loading…</span>
                          </div>
                        }
                      >
                        <DocumentPanel />
                      </Suspense>
                    </div>
                  )}

                  {showRightDrawer && (
                    <Drawer
                      open
                      placement="right"
                      width={RIGHT_PANEL_WIDTH}
                      onClose={closeRightPanel}
                      closable={false}
                      styles={{
                        body: { padding: 0, background: "rgba(5, 5, 7, 0.8)" },
                        content: { background: "rgba(5, 5, 7, 0.8)" },
                        mask: { background: "rgba(0, 0, 0, 0.5)" },
                      }}
                    >
                      <Suspense
                        fallback={
                          <div
                            style={{
                              background: "#0d0d12",
                              borderRadius: "12px",
                              height: "100%",
                              opacity: 0.5,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              border: "1px solid #1f2937",
                              margin: "16px",
                            }}
                          >
                            <span style={{ color: "#6b7280", fontSize: "13px" }}>Loading…</span>
                          </div>
                        }
                      >
                        <div style={{ padding: "16px" }}>
                          <DocumentPanel />
                        </div>
                      </Suspense>
                    </Drawer>
                  )}
                </div>
              ) : (
                /* Mobile Layout */
                <div
                  className="animate-fade-in"
                  style={{
                    opacity: 0,
                    animationDelay: "0.2s",
                    display: "flex",
                    flexDirection: "column",
                    gap: "16px",
                  }}
                >
                  <div
                    style={{
                      background: "#0d0d12",
                      borderRadius: "12px",
                      overflow: "hidden",
                      border: "1px solid #1f2937",
                    }}
                  >
                    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
                      <Suspense fallback={<PanelFallback label="Loading upload…" height={220} />}>
                        <UploadPanel />
                      </Suspense>
                      <Suspense fallback={<PanelFallback label="Loading logs…" height={120} />}>
                        <TerminalWindow />
                      </Suspense>
                      <Suspense fallback={<PanelFallback label="Loading evaluation…" height={160} />}>
                        <EvaluationPanel />
                      </Suspense>
                      <Suspense fallback={<PanelFallback label="Loading chat…" height={300} />}>
                        <ChatPanel />
                      </Suspense>
                    </div>
                  </div>

                  {rightPanelOpen && (
                    <div style={{ marginTop: "8px" }}>
                      <Suspense
                        fallback={
                          <div
                            style={{
                              background: "#0d0d12",
                              borderRadius: "12px",
                              height: "360px",
                              opacity: 0.5,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              border: "1px solid #1f2937",
                            }}
                          >
                            <span style={{ color: "#6b7280", fontSize: "13px" }}>Loading…</span>
                          </div>
                        }
                      >
                        <DocumentPanel />
                      </Suspense>
                    </div>
                  )}
                </div>
              )}
            </div>
          </AppTransition>
        </Content>
      </Layout>
    </ConfigProvider>
  );
}
