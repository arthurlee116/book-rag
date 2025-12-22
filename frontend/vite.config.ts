import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_BACKEND_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: true,
      port: 3000,
      proxy: {
        "/backend": {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/backend/, ""),
        },
      },
    },
    build: {
      manifest: true,
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (id.includes("node_modules/react")) {
              return "react-vendor";
            }
            if (id.includes("node_modules/antd") || id.includes("node_modules/@ant-design")) {
              return "antd-vendor";
            }
          },
        },
      },
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
  };
});
