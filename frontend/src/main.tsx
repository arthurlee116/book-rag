import { StrictMode, Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.less";

const App = lazy(() => import("./App"));

function Shell() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#000",
        color: "#f5f5f7",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 15,
        letterSpacing: 0.2,
      }}
    >
      Loading ERR...
    </div>
  );
}

function Root() {
  const [shouldLoadApp, setShouldLoadApp] = useState(false);

  useEffect(() => {
    let idleId: number | null = null;
    let timeoutId: number | null = null;

    const load = () => setShouldLoadApp(true);
    const idle = (window as Window & {
      requestIdleCallback?: (callback: IdleRequestCallback, options?: IdleRequestOptions) => number;
      cancelIdleCallback?: (handle: number) => void;
    }).requestIdleCallback;
    const cancelIdle = (window as Window & {
      cancelIdleCallback?: (handle: number) => void;
    }).cancelIdleCallback;

    if (idle) {
      idleId = idle(load, { timeout: 1200 });
    } else {
      timeoutId = window.setTimeout(load, 300);
    }

    return () => {
      if (idleId !== null && cancelIdle) {
        cancelIdle(idleId);
      }
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, []);

  return (
    <StrictMode>
      {shouldLoadApp ? (
        <Suspense fallback={<Shell />}>
          <App />
        </Suspense>
      ) : (
        <Shell />
      )}
    </StrictMode>
  );
}

createRoot(document.getElementById("root")!).render(<Root />);

export { Shell, Root };
