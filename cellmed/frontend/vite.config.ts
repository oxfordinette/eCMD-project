import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En dev, les appels /api sont redirigés vers le backend FastAPI.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_PROXY ?? "http://localhost:8000",
    },
  },
});
