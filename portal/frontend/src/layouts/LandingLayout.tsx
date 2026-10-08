import { ReactNode } from "react";
import { Link, Outlet } from "react-router-dom";
import { User } from "@/api/client";
import LandingHeader from "@/pages/landing/LandingHeader";
import LandingFooter from "@/pages/landing/LandingFooter";
import { Button } from "@/components/ui/button";

type Props = {
  user: User | null;
  onLogout?: () => void;
  standalone?: boolean;
  children?: ReactNode;
};

export default function LandingLayout({ user, onLogout, standalone, children }: Props) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {user && !standalone && (
        <div className="border-b border-border bg-card/80 backdrop-blur-sm">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-end gap-2 px-4 py-2">
            <span className="text-sm text-muted-foreground mr-auto truncate">{user.email}</span>
            {user.role === "subscriber" && (
              <Button variant="outline" size="sm" asChild>
                <Link to="/app">В личный кабинет</Link>
              </Button>
            )}
            {user.role === "provider" && (
              <Button variant="outline" size="sm" asChild>
                <Link to="/admin">Админка</Link>
              </Button>
            )}
            {onLogout && (
              <Button variant="ghost" size="sm" onClick={onLogout}>
                Выйти
              </Button>
            )}
          </div>
        </div>
      )}
      <LandingHeader standalone={standalone} />
      {children ?? <Outlet />}
      <LandingFooter standalone={standalone} />
    </div>
  );
}
