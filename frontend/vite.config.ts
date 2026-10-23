/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// The API port is configurable: put SPEQULATOR_API_PORT=8001 in frontend/.env.local
// if port 8000 is taken on your machine (D-022: everything stays on 127.0.0.1).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const port = env.SPEQULATOR_API_PORT || "8000";
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      proxy: { "/api": `http://127.0.0.1:${port}` },
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test-setup.ts"],
    },
  };
});
