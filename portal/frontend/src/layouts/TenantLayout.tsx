import { Outlet } from "react-router-dom";
import {
  CreditCard,
  Download,
  LayoutDashboard,
  Package,
  Server,
  ShoppingBag,
  Ticket,
  User,
} from "lucide-react";
import { User as ApiUser } from "@/api/client";import AppShell, { AppShellDivider } from "@/components/AppShell";
import { SubscriptionBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { TenantProvider, useTenant } from "@/context/TenantContext";

type Props = {
  user: ApiUser;
  onLogout: () => void;
};

const NAV = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/servers", label: "Серверы", icon: Server, end: false },
  { to: "/app/wargm", label: "Wargm", icon: ShoppingBag, end: false },
  { to: "/app/catalog", label: "Каталог", icon: Package, end: false },
  { to: "/app/setup", label: "Установка", icon: Download, end: false },
  { to: "/app/support", label: "Поддержка", icon: Ticket, end: false },
  { to: "/app/billing", label: "Подписка", icon: CreditCard, end: false },
  { to: "/app/account", label: "Аккаунт", icon: User, end: false },
];

function TenantLayoutInner({ user, onLogout }: Props) {
  const { subscription, catalogMeta } = useTenant();

  return (
    <AppShell
      brand={subscription?.tenant_id ?? user.tenant_id ?? "ShopClaim"}
      brandHint="Личный кабинет"
      nav={NAV}
      userEmail={user.email}
      onLogout={onLogout}
      headerExtra={
        <>
          {subscription && (
            <SubscriptionBadge active={subscription.active} until={subscription.subscription_until} />
          )}
          {catalogMeta?.has_unpublished_changes && (
            <Badge variant="outline" className="border-warning text-warning">
              Черновик каталога
            </Badge>
          )}
          <AppShellDivider />
        </>
      }
    >
      <Outlet />
    </AppShell>
  );
}

export default function TenantLayout(props: Props) {
  return (
    <TenantProvider>
      <TenantLayoutInner {...props} />
    </TenantProvider>
  );
}
