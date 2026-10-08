import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type SubscriptionVariant = "active" | "expiring" | "inactive";
type DeployVariant = "synced" | "pending" | "error";

const SUB_LABELS: Record<SubscriptionVariant, string> = {
  active: "Подписка активна",
  expiring: "Истекает скоро",
  inactive: "Подписка неактивна",
};

const DEPLOY_LABELS: Record<DeployVariant, string> = {
  synced: "Синхронизировано",
  pending: "Ожидает sync",
  error: "Ошибка sync",
};

export function subscriptionVariant(active: boolean, until: string): SubscriptionVariant {
  if (!active) return "inactive";
  const days = (new Date(until).getTime() - Date.now()) / (86400 * 1000);
  if (days <= 7) return "expiring";
  return "active";
}

export function deployVariant(status: string | null): DeployVariant {
  if (status === "synced") return "synced";
  if (status === "error") return "error";
  return "pending";
}

const subClass: Record<SubscriptionVariant, string> = {
  active: "border-success/50 text-success bg-success/10",
  expiring: "border-warning/50 text-warning bg-warning/10",
  inactive: "border-destructive/50 text-destructive bg-destructive/10",
};

const deployClass: Record<DeployVariant, string> = {
  synced: "border-success/50 text-success bg-success/10",
  pending: "border-warning/50 text-warning bg-warning/10",
  error: "border-destructive/50 text-destructive bg-destructive/10",
};

export function SubscriptionBadge({ active, until }: { active: boolean; until: string }) {
  const v = subscriptionVariant(active, until);
  return (
    <Badge variant="outline" className={cn("font-normal", subClass[v])}>
      {SUB_LABELS[v]}
    </Badge>
  );
}

export function DeployBadge({ status }: { status: string | null }) {
  const v = deployVariant(status);
  return (
    <Badge variant="outline" className={cn("font-normal", deployClass[v])}>
      {DEPLOY_LABELS[v]}
    </Badge>
  );
}
