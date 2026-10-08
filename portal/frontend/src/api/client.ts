const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export type User = {
  id: number;
  email: string;
  role: string;
  tenant_id: string | null;
  is_active: boolean;
  pending_email?: string | null;
};

export type ModArtifact = {
  id: string;
  name: string;
  description: string;
  kind: string;
  required: boolean;
  download_url: string;
  download_available: boolean;
  workshop_url: string | null;
  filename?: string | null;
  size_bytes?: number | null;
};

export type ModsManifest = {
  version: string;
  updated_at: string;
  status_page_url: string | null;
  artifacts: ModArtifact[];
};

type ValidationErrorItem = { msg?: string; loc?: (string | number)[] };

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const e = item as ValidationErrorItem;
        return e.msg ?? JSON.stringify(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object" && "msg" in detail) {
    return String((detail as ValidationErrorItem).msg);
  }
  return "Ошибка запроса";
}

export function formatApiError(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatDetail(err.detail) || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/api/public/health"),
  mods: () => request<ModsManifest>("/api/public/mods"),
  me: () => request<User | null>("/api/auth/me"),
  login: (email: string, password: string) =>
    request<User>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () =>
    request<{ status: string }>("/api/auth/logout", {
      method: "POST",
      body: "{}",
    }),
  setPassword: (code: string, password: string) =>
    request<User>("/api/auth/set-password", {
      method: "POST",
      body: JSON.stringify({ code, password }),
    }),
  changePassword: (current_password: string, new_password: string) =>
    request<User>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),
  changeEmail: (current_password: string, new_email: string) =>
    request<{ status: string; email: string; pending_email: string; email_sent: boolean }>(
      "/api/auth/change-email",
      {
        method: "POST",
        body: JSON.stringify({ current_password, new_email }),
      }
    ),
  cancelEmailChange: () =>
    request<{ status: string }>("/api/auth/cancel-email-change", {
      method: "POST",
      body: "{}",
    }),
  confirmEmailChange: (code: string) =>
    request<{ status: string; email: string }>("/api/auth/confirm-email-change", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  forgotPassword: (email: string, website?: string) =>
    request<{ status: string }>("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email, website: website ?? "" }),
    }),
  resetPassword: (code: string, password: string) =>
    request<{ status: string }>("/api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ code, password }),
    }),
  submitLead: (data: Record<string, unknown>) =>
    request<{ status: string; message: string }>("/api/public/leads", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  publicPricing: () =>
    request<{
      price_per_server_rub: number;
      network3_rub: number;
      unlimited_rub: number;
      billing_enabled: boolean;
      checkout_available: boolean;
    }>("/api/public/pricing"),
  admin: {
    leads: () => request<unknown[]>("/api/admin/leads"),
    rejectLead: (id: number) =>
      request<unknown>(`/api/admin/leads/${id}?status=rejected`, { method: "PATCH" }),
    tenants: () => request<unknown[]>("/api/admin/tenants"),
    getTenant: (slug: string) => request<unknown>(`/api/admin/tenants/${slug}`),
    createTenant: (body: unknown) =>
      request<unknown>("/api/admin/tenants", { method: "POST", body: JSON.stringify(body) }),
    updateTenant: (
      slug: string,
      body: {
        max_servers?: number;
        subscription_until?: string;
        enabled?: boolean;
        plan?: string;
      },
    ) =>
      request<unknown>(`/api/admin/tenants/${slug}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    syncBridge: (dryRun: boolean) =>
      request<unknown>(`/api/admin/bridge/sync?dry_run=${dryRun}`, {
        method: "POST",
        body: "{}",
      }),
    addServer: (tenantSlug: string, body: unknown) =>
      request<unknown>(`/api/admin/tenants/${tenantSlug}/servers`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    tickets: () => request<unknown[]>("/api/admin/tickets"),
    getTicket: (id: number) => request<unknown>(`/api/admin/tickets/${id}`),
    replyTicket: (id: number, body: string) =>
      request<unknown>(`/api/admin/tickets/${id}/messages`, {
        method: "POST",
        body: JSON.stringify({ body }),
      }),
    invite: (userId: number) =>
      request<{ status: string; email_sent: string; invite_code: string }>(
        `/api/admin/users/${userId}/invite`,
        { method: "POST", body: "{}" }
      ),
    getCatalog: (slug: string) => request<unknown>(`/api/admin/tenants/${slug}/catalog`),
    putCatalogOffer: (slug: string, offerId: string, body: unknown) =>
      request<unknown>(`/api/admin/tenants/${slug}/catalog/offers/${offerId}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    deleteCatalogOffer: (slug: string, offerId: string) =>
      request<unknown>(`/api/admin/tenants/${slug}/catalog/offers/${offerId}`, {
        method: "DELETE",
      }),
    publishCatalog: (slug: string, expectedPublishedAt?: string | null) =>
      request<unknown>(`/api/admin/tenants/${slug}/catalog/publish`, {
        method: "POST",
        body: JSON.stringify({ expected_published_at: expectedPublishedAt ?? null }),
      }),
    discardCatalog: (slug: string) =>
      request<unknown>(`/api/admin/tenants/${slug}/catalog/discard`, {
        method: "POST",
        body: "{}",
      }),
    importWargm: (slug: string, offerIds: string[]) =>
      request<unknown>(`/api/admin/tenants/${slug}/catalog/import-wargm`, {
        method: "POST",
        body: JSON.stringify({ offer_ids: offerIds }),
      }),
    putVehicleProfile: (slug: string, className: string, body: unknown) =>
      request<unknown>(
        `/api/admin/tenants/${slug}/catalog/vehicle-profiles/${encodeURIComponent(className)}`,
        { method: "PUT", body: JSON.stringify(body) }
      ),
    getBillingSettings: () => request<unknown>("/api/admin/billing/settings"),
    updateBillingSettings: (body: { price_per_server_rub?: number; billing_enabled?: boolean }) =>
      request<unknown>("/api/admin/billing/settings", {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    getTenantPayments: (slug: string) =>
      request<unknown[]>(`/api/admin/billing/tenants/${slug}/payments`),
    extendTenant: (slug: string, days: 30 | 365, reason?: string) =>
      request<{ status: string; subscription_until: string }>(
        `/api/admin/billing/tenants/${slug}/extend`,
        { method: "POST", body: JSON.stringify({ days, reason }) },
      ),
  },
  tenant: {
    billingCheckout: (body: { payment_kind: string; months: 1 | 3 | 12 }) =>
      request<{ confirmation_url: string; payment_id: string }>("/api/tenant/billing/checkout", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    billingReconcile: (body?: { payment_id?: string }) =>
      request<{ status: string; applied: boolean }>("/api/tenant/billing/reconcile", {
        method: "POST",
        body: JSON.stringify(body ?? {}),
      }),
    billingReduceLimit: (body: { max_servers: number }) =>
      request<{ max_servers: number }>("/api/tenant/billing/reduce-limit", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    billingPayments: () => request<unknown[]>("/api/tenant/billing/payments"),
    subscription: () => request<unknown>("/api/tenant/subscription"),
    putWargm: (body: { wargm_shop_id: string; wargm_api_key: string; current_password: string }) =>
      request<{ status: string }>("/api/tenant/wargm", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    createServer: (body: { server_id: string; shop_server_id: number }) =>
      request<unknown>("/api/tenant/servers", { method: "POST", body: JSON.stringify(body) }),
    deleteServer: (serverId: string) =>
      request<void>(`/api/tenant/servers/${encodeURIComponent(serverId)}`, { method: "DELETE" }),
    activate: () => request<unknown>("/api/tenant/activate", { method: "POST", body: "{}" }),
    servers: () => request<unknown[]>("/api/tenant/servers"),
    tickets: () => request<unknown[]>("/api/tenant/tickets"),
    getTicket: (id: number) => request<unknown>(`/api/tenant/tickets/${id}`),
    createTicket: (body: unknown) =>
      request<unknown>("/api/tenant/tickets", { method: "POST", body: JSON.stringify(body) }),
    replyTicket: (id: number, body: string) =>
      request<unknown>(`/api/tenant/tickets/${id}/messages`, {
        method: "POST",
        body: JSON.stringify({ body }),
      }),
    catalog: () => request<unknown>("/api/tenant/catalog"),
    catalogMeta: () => request<unknown>("/api/tenant/catalog/meta"),
    putCatalogOffer: (offerId: string, body: unknown) =>
      request<unknown>(`/api/tenant/catalog/offers/${offerId}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    deleteCatalogOffer: (offerId: string) =>
      request<unknown>(`/api/tenant/catalog/offers/${offerId}`, { method: "DELETE" }),
    publishCatalog: (expectedPublishedAt?: string | null, currentPassword?: string) =>
      request<unknown>("/api/tenant/catalog/publish", {
        method: "POST",
        body: JSON.stringify({
          expected_published_at: expectedPublishedAt ?? null,
          current_password: currentPassword ?? null,
        }),
      }),
    discardCatalog: () =>
      request<unknown>("/api/tenant/catalog/discard", { method: "POST", body: "{}" }),
    importWargm: (offerIds: string[], currentPassword?: string) =>
      request<unknown>("/api/tenant/catalog/import-wargm", {
        method: "POST",
        body: JSON.stringify({ offer_ids: offerIds, current_password: currentPassword ?? null }),
      }),
    previewWargm: (offerId: string) => request<unknown>(`/api/tenant/catalog/preview-wargm/${offerId}`),
    putVehicleProfile: (className: string, body: unknown) =>
      request<unknown>(`/api/tenant/catalog/vehicle-profiles/${encodeURIComponent(className)}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
  },
};
