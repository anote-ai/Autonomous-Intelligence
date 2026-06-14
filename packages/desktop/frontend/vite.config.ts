import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 3001,
    proxy: {
      "/api": "http://localhost:5099",
      "/auth": "http://localhost:5099",
      "/health": "http://localhost:5099",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
