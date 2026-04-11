import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to the FastAPI backend during development
      "/health": "http://127.0.0.1:8000",
      "/routes": "http://127.0.0.1:8000",
      "/query": "http://127.0.0.1:8000",
      "/structured-query": "http://127.0.0.1:8000",
    },
  },
  build: {
    // Output built assets to src/nbatools/ui/dist for FastAPI to serve
    outDir: "../src/nbatools/ui/dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
