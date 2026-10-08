const ALLOWED = new Set(["example.com", "www.example.com", "127.0.0.1", "localhost"]);

function resolveLandingOrigin(): string {
  const raw = import.meta.env.VITE_LANDING_URL?.replace(/\/$/, "");
  if (raw) {
    const host = new URL(raw).hostname;
    if (!ALLOWED.has(host)) {
      throw new Error(`VITE_LANDING_URL host not allowed: ${host}`);
    }
    return raw;
  }
  return import.meta.env.DEV ? "" : "https://example.com";
}

export const LANDING_ORIGIN = resolveLandingOrigin();

/** Portal home (local dev → landing `/`; prod lk `/` may be redirected by reverse proxy). */
export function portalHomeUrl(): string {
  return LANDING_ORIGIN ? `${LANDING_ORIGIN}/` : "/";
}

export function landingUrl(path = "/"): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!LANDING_ORIGIN) return p;
  return `${LANDING_ORIGIN}${p}`;
}
