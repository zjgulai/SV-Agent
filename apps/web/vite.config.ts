import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: { "/api": "http://localhost:8000", "/health": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    exclude: [...configDefaults.exclude, "tests/e2e/**"],
    setupFiles: ["./src/test/setup.ts"],
  },
});
