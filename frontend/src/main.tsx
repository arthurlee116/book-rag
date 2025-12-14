import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ConfigProvider, theme } from "antd";
import App from "./App";
import { darkTheme } from "./theme";
import "./index.less";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConfigProvider theme={{ ...darkTheme, algorithm: theme.darkAlgorithm }}>
      <App />
    </ConfigProvider>
  </StrictMode>
);
