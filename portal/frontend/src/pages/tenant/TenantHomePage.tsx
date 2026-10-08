import { useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import DiagnosticPanel from "@/components/DiagnosticPanel";
import PageHeader from "@/components/PageHeader";
import QuotaMeter from "@/components/QuotaMeter";
import SetupStepper from "@/components/SetupStepper";
import StatCard from "@/components/StatCard";
import { DeployBadge, SubscriptionBadge } from "@/components/StatusBadge";
import { useTenant } from "@/context/TenantContext";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function HomeSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

export default function TenantHomePage() {
  const { subscription: sub, catalogMeta, reload, isLoading } = useTenant();
  const [activating, setActivating] = useState(false);

  const activate = async () => {
    setActivating(true);
    try {
      const r = (await api.tenant.activate()) as { deploy_status: string };
      toast.success(`Активация: deploy ${r.deploy_status}`);
      await reload();
    } catch (err) {
      toast.error(String(err));
    } finally {
      setActivating(false);
    }
  };

  if (isLoading && !sub) {
    return <HomeSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" />

      {!sub?.active && sub && (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertTitle>Подписка неактивна</AlertTitle>
          <AlertDescription>
            Выдача в игре остановлена (subscription gate).{" "}
            <Link to="/app/billing" className="font-medium underline underline-offset-4">
              Продление
            </Link>
          </AlertDescription>
        </Alert>
      )}

      {sub && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Подписка">
            <SubscriptionBadge active={sub.active} until={sub.subscription_until} />
            <p className="text-sm text-muted-foreground mt-2">до {sub.subscription_until}</p>
          </StatCard>
          <StatCard title="Bridge">
            <DeployBadge status={sub.deploy_status} />
          </StatCard>
          <StatCard title="Серверы">
            <QuotaMeter count={sub.server_count} max={sub.max_servers} />
          </StatCard>
          <StatCard title="Каталог">
            <p className="text-2xl font-semibold">{catalogMeta?.published_offer_count ?? 0}</p>
            <p className="text-sm text-muted-foreground">опубликовано</p>
            {catalogMeta?.has_unpublished_changes && (
              <Badge variant="outline" className="mt-2 border-warning/50 text-warning bg-warning/10">
                Есть черновик
              </Badge>
            )}
          </StatCard>
        </div>
      )}

      <SetupStepper sub={sub} meta={catalogMeta} compact />

      {sub && sub.deploy_status !== "synced" && sub.wargm_configured && sub.server_count > 0 && (
        <Card>
          <CardContent className="flex flex-col gap-4 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm">Bridge ещё не синхронизирован.</p>
            <Button type="button" onClick={activate} disabled={activating}>
              {activating ? "Синхронизация…" : "Активировать (синхронизация Bridge)"}
            </Button>
          </CardContent>
        </Card>
      )}

      {sub && <DiagnosticPanel bridgeUrl={sub.bridge_url} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Быстрые действия</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="secondary" asChild>
            <Link to="/app/servers">Серверы</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link to="/app/catalog">Каталог</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link to="/app/support/new">Создать тикет</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
