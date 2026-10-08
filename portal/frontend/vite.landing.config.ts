import { defineConfig } from "vite";
import { sharedViteConfig } from "./vite.shared";

export default defineConfig(
  sharedViteConfig({
    build: {
      outDir: "dist-landing",
      sourcemap: false,
      rollupOptions: {
        input: "landing.html",
      },
    },
  }),
);
