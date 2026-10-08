import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import BrandLogo from "@/components/BrandLogo";
import { cn } from "@/lib/utils";

export type AppNavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
};

type Props = {
  brand: string;
  brandHint?: string;
  nav: AppNavItem[];
  headerExtra?: ReactNode;
  userEmail?: string;
  onLogout?: () => void;
  children: ReactNode;
};

export default function AppShell({
  brand,
  brandHint,
  nav,
  headerExtra,
  userEmail,
  onLogout,
  children,
}: Props) {
  return (
    <SidebarProvider>
      <Sidebar collapsible="icon" className="border-r border-sidebar-border">
        <SidebarHeader className="p-4">
          <div className="flex items-center gap-2 group-data-[collapsible=icon]:justify-center">
            <BrandLogo variant="icon" />
            <div className="flex min-w-0 flex-col gap-0.5 group-data-[collapsible=icon]:hidden">
              <span className="truncate font-semibold tracking-tight">{brand}</span>
              {brandHint && <span className="text-xs text-muted-foreground">{brandHint}</span>}
            </div>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Меню</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {nav.map((item) => (
                  <SidebarMenuItem key={item.to}>
                    <SidebarMenuButton asChild tooltip={item.label}>
                      <NavLink
                        to={item.to}
                        end={item.end}
                        className={({ isActive }) =>
                          cn(isActive && "bg-sidebar-accent text-sidebar-accent-foreground font-medium")
                        }
                      >
                        <item.icon className="size-4 shrink-0" />
                        <span>{item.label}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        {userEmail && onLogout && (
          <SidebarFooter className="p-2">
            <p className="truncate px-2 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
              {userEmail}
            </p>
            <Button variant="outline" size="sm" className="w-full" onClick={onLogout}>
              Выйти
            </Button>
          </SidebarFooter>
        )}
      </Sidebar>
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-4">
          <SidebarTrigger className="-ml-1" />
          {headerExtra}
        </header>
        <main className="flex-1 overflow-auto p-4 md:p-6 animate-fade-in">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}

export function AppShellDivider() {
  return <Separator orientation="vertical" className="mx-1 h-6" />;
}
