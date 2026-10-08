import { defineConfig, mergeConfig } from "vite";
import { landingDevPlugin } from "./vite.landing-dev";
import { sharedViteConfig } from "./vite.shared";

export default defineConfig(
  mergeConfig(
    sharedViteConfig({
      build: {
        outDir: "dist",
        sourcemap: false,
      },
      server: {
        host: "127.0.0.1",
        port: 5173,
        proxy: {
          "/api": "http://127.0.0.1:8790",
        },
      },
    }),
    {
      plugins: [landingDevPlugin()],
    },
  ),
);
