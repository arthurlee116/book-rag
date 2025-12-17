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
    const load = () => setShouldLoadApp(true);
    const idle = (window as Window & {
      requestIdleCallback?: (callback: IdleRequestCallback, options?: IdleRequestOptions) => number;
    }).requestIdleCallback;

    if (idle) {
      idle(load, { timeout: 1200 });
    } else {
      setTimeout(load, 300);
    }
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
