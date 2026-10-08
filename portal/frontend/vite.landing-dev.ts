import type { Plugin } from "vite";

const LANDING_PATHS = new Set(["/", "/offer", "/privacy"]);

/** Dev-only: serve landing.html for marketing routes on the SPA Vite server (:5173). */
export function landingDevPlugin(): Plugin {
  return {
    name: "shop-claim-landing-dev",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (req.method !== "GET" && req.method !== "HEAD") {
          next();
          return;
        }
        const raw = req.url ?? "/";
        const pathname = raw.split("?")[0]?.split("#")[0] ?? "/";
        if (!LANDING_PATHS.has(pathname)) {
          next();
          return;
        }
        const qs = raw.includes("?") ? raw.slice(raw.indexOf("?")) : "";
        req.url = `/landing.html${qs}`;
        next();
      });
    },
  };
}
