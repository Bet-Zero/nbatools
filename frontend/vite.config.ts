import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { VITE_API_PROXY } from "./config/httpProxy";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    fs: {
      allow: [fileURLToPath(new URL("..", import.meta.url))],
    },
    port: 5173,
    // Public routes come from the cross-transport contract. Two operator
    // routes remain explicit local-development extensions in this exact map.
    proxy: VITE_API_PROXY,
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
    testTimeout: 15000,
  },
});
