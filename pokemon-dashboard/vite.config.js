import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Root-level config used when Vercel runs `vite build` from pokemon-dashboard/.
// Sets root to frontend/ so vite finds index.html, src/, and CSS configs there.
export default defineConfig({
  root: "frontend",
  plugins: [react()],
  build: {
    outDir: "dist",
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
