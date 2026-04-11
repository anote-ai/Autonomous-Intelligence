import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  esbuild: {
    include: /\.[jt]sx?$/,
    exclude: [],
    loader: "jsx",
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["src/setupTests.js"],
    include: ["src/**/*.test.{js,jsx,ts,tsx}"],
    exclude: ["node_modules"],
  },
});
