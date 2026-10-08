import { Outlet } from "react-router-dom";
import { LayoutDashboard, Ticket, CreditCard } from "lucide-react";
import { User } from "@/api/client";
import AppShell from "@/components/AppShell";

type Props = {
  user: User;
  onLogout: () => void;
};

const NAV = [
  { to: "/admin", label: "Обзор", icon: LayoutDashboard, end: true },
  { to: "/admin/billing", label: "Биллинг", icon: CreditCard, end: false },
  { to: "/admin/tickets", label: "Тикеты", icon: Ticket, end: false },
];

export default function AdminLayout({ user, onLogout }: Props) {
  return (
    <AppShell
      brand="ShopClaim"
      brandHint="Админка провайдера"
      nav={NAV}
      userEmail={user.email}
      onLogout={onLogout}
    >
      <Outlet />
    </AppShell>
  );
}
