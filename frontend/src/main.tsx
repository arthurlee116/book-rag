import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.less";

// PERF: Import `App` eagerly so the initial page load doesn't depend on a secondary
// dynamic chunk + idle/timeout gating. This reduces first-load waterfall / latency.
// Verify: `npm run build` and confirm `src/App.tsx` is no longer a dynamic entry in
// `dist/.vite/manifest.json`, then check Lighthouse (`npm run bench:tbt`).
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
