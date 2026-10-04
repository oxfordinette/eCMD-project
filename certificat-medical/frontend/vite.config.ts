import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Portail assuré « Certificat médical ». En dev, /api est redirigé vers le backend partagé.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      "/api": process.env.VITE_API_PROXY ?? "http://localhost:8000",
    },
  },
});
