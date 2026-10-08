import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, User } from "@/api/client";
import AuthLayout from "@/layouts/AuthLayout";
import TenantLayout from "@/layouts/TenantLayout";
import AdminLayout from "@/layouts/AdminLayout";
import RedirectToLanding from "@/components/RedirectToLanding";
import { portalHomeUrl } from "@/lib/siteUrls";
import LoginPage from "@/pages/auth/LoginPage";
import SetPasswordPage from "@/pages/auth/SetPasswordPage";
import ConfirmEmailChangePage from "@/pages/auth/ConfirmEmailChangePage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/auth/ResetPasswordPage";
import AdminHomePage from "@/pages/admin/AdminHomePage";
import AdminTenantPage from "@/pages/admin/AdminTenantPage";
import AdminCatalogPage from "@/pages/admin/AdminCatalogPage";
import AdminTicketsPage from "@/pages/admin/AdminTicketsPage";
import AdminBillingPage from "@/pages/admin/AdminBillingPage";
import TenantHomePage from "@/pages/tenant/TenantHomePage";
import TenantWargmPage from "@/pages/tenant/TenantWargmPage";
import TenantServersPage from "@/pages/tenant/TenantServersPage";
import TenantCatalogPage from "@/pages/tenant/TenantCatalogPage";
import TenantSetupPage from "@/pages/tenant/TenantSetupPage";
import TenantTicketsPage from "@/pages/tenant/TenantTicketsPage";
import TenantTicketNewPage from "@/pages/tenant/TenantTicketNewPage";
import TenantTicketDetailPage from "@/pages/tenant/TenantTicketDetailPage";
import TenantBillingPage from "@/pages/tenant/TenantBillingPage";
import TenantAccountPage from "@/pages/tenant/TenantAccountPage";

function LoadingShell() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-8">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-64" />
      <Skeleton className="h-32 w-full max-w-md" />
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null));
  }, []);

  const onLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Still leave admin UI if cookie clear failed (e.g. stale session).
    }
    setUser(null);
    window.location.href = portalHomeUrl();
  };

  if (user === undefined) {
    return (
      <TooltipProvider>
        <LoadingShell />
        <Toaster richColors position="top-center" />
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <Routes>
        <Route path="/" element={<RedirectToLanding path="/" />} />
        <Route path="/offer" element={<RedirectToLanding path="/offer" />} />
        <Route path="/privacy" element={<RedirectToLanding path="/privacy" />} />

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage onLogin={setUser} />} />
          <Route path="/set-password" element={<SetPasswordPage onLogin={setUser} />} />
          <Route path="/confirm-email-change" element={<ConfirmEmailChangePage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>

        <Route
          path="/admin"
          element={
            user?.role === "provider" ? (
              <AdminLayout user={user} onLogout={onLogout} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        >
          <Route index element={<AdminHomePage user={user!} onUserUpdate={setUser} />} />
          <Route path="billing" element={<AdminBillingPage />} />
          <Route path="tenants/:slug" element={<AdminTenantPage />} />
          <Route path="tenants/:slug/catalog" element={<AdminCatalogPage />} />
          <Route path="tickets" element={<AdminTicketsPage />} />
          <Route path="tickets/:id" element={<AdminTicketsPage />} />
        </Route>

        <Route
          path="/app"
          element={
            user?.role === "subscriber" ? (
              <TenantLayout user={user} onLogout={onLogout} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        >
          <Route index element={<TenantHomePage />} />
          <Route path="wargm" element={<TenantWargmPage />} />
          <Route path="servers" element={<TenantServersPage />} />
          <Route path="catalog" element={<TenantCatalogPage tenantId={user?.tenant_id ?? null} />} />
          <Route path="setup" element={<TenantSetupPage />} />
          <Route path="support" element={<TenantTicketsPage />} />
          <Route path="support/new" element={<TenantTicketNewPage />} />
          <Route path="support/:id" element={<TenantTicketDetailPage />} />
          <Route path="billing" element={<TenantBillingPage />} />
          <Route path="account" element={<TenantAccountPage user={user!} onUserUpdate={setUser} />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      <Toaster richColors position="top-center" />
    </TooltipProvider>
  );
}
