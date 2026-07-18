import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        ws: true,
      },
      "/health": "http://127.0.0.1:8000",
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("antd") || id.includes("@ant-design")) return "antd";
          if (id.includes("recharts") || id.includes("d3-")) return "charts";
          if (id.includes("react-markdown") || id.includes("remark"))
            return "markdown";
          if (id.includes("@tanstack") || id.includes("zustand")) return "data";
          if (id.includes("react-router") || id.includes("react-dom") || id.includes("/react/"))
            return "react-vendor";
        },
      },
    },
    chunkSizeWarningLimit: 900,
  },
});
