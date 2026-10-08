import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { CatalogMeta, Subscription } from "@/types/tenant";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Step = {
  id: string;
  label: string;
  done: boolean;
  path: string;
};

function buildSteps(sub: Subscription | null, meta: CatalogMeta | null): Step[] {
  if (!sub) return [];
  return [
    { id: "wargm", label: "Подключение wargm", done: sub.wargm_configured, path: "/app/wargm" },
    { id: "servers", label: "Мои серверы", done: sub.server_count > 0, path: "/app/servers" },
    { id: "sync", label: "Синхронизация Bridge", done: sub.deploy_status === "synced", path: "/app" },
    {
      id: "config",
      label: "config.json и mod",
      done: sub.server_count > 0 && sub.deploy_status === "synced",
      path: "/app/setup",
    },
    {
      id: "catalog",
      label: "Каталог опубликован",
      done: (meta?.published_offer_count ?? 0) > 0,
      path: "/app/catalog",
    },
    { id: "test", label: "Тестовая покупка в игре", done: false, path: "/app/setup" },
  ];
}

type Props = { sub: Subscription | null; meta: CatalogMeta | null; compact?: boolean };

export default function SetupStepper({ sub, meta, compact = false }: Props) {
  const navigate = useNavigate();
  const steps = buildSteps(sub, meta);
  if (!steps.length) return null;

  const activeIdx = steps.findIndex((s) => !s.done);
  const onboardingDone = steps.slice(0, -1).every((s) => s.done);

  if (compact && onboardingDone) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{compact ? "Онбординг" : "Настройка сервиса"}</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-2">
          {steps.map((step, i) => {
            const isActive = activeIdx === i;
            const isDone = step.done;
            return (
              <li key={step.id}>
                <Button
                  type="button"
                  variant={isActive ? "secondary" : "ghost"}
                  className={cn(
                    "w-full justify-start gap-3 h-auto py-2",
                    isDone && "text-muted-foreground",
                  )}
                  disabled={!isDone && !isActive}
                  onClick={() => isDone && navigate(step.path)}
                >
                  <span
                    className={cn(
                      "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium border",
                      isDone && "bg-primary text-primary-foreground border-primary",
                      isActive && !isDone && "border-primary text-primary",
                    )}
                  >
                    {isDone ? <Check className="size-3.5" /> : i + 1}
                  </span>
                  <span className="text-left">{step.label}</span>
                </Button>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
