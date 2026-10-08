/** Normalize action code pasted as raw token or full URL with ?code= */
export function normalizeActionCode(raw: string): string {
  const t = raw.trim();
  try {
    const u = new URL(t);
    const fromQuery = u.searchParams.get("code");
    if (fromQuery) return fromQuery.trim();
  } catch {
    /* not a URL */
  }
  return t;
}

/** @deprecated use normalizeActionCode */
export const normalizeInviteCode = normalizeActionCode;

export function inviteSetPasswordUrl(code: string): string {
  return `${window.location.origin}/set-password?code=${encodeURIComponent(code)}`;
}
