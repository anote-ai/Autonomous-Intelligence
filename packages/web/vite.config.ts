import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { transform } from "esbuild";

// The landing page is written as plain .js files containing JSX (matching the
// Anote marketing site's component style). Vite/rolldown only auto-enables
// JSX parsing for .jsx/.tsx files, so pre-compile JSX out of these .js files
// before they reach the bundler's native parser.
function jsxInJs(): Plugin {
  return {
    name: "jsx-in-js",
    enforce: "pre",
    async transform(code, id) {
      if (!id.includes("/landing_page/") || !id.endsWith(".js")) return null;
      const result = await transform(code, {
        loader: "jsx",
        jsx: "automatic",
        sourcefile: id,
      });
      return { code: result.code, map: result.map };
    },
  };
}

export default defineConfig({
  plugins: [jsxInJs(), react()],
  server: {
    port: 3000,
    proxy: {
      "/api": "http://localhost:5000",
      "/auth": "http://localhost:5000",
      "/health": "http://localhost:5000",
    },
  },
});
