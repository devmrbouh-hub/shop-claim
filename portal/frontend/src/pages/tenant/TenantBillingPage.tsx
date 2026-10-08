import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, CreditCard, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/api/client";
import PageHeader from "@/components/PageHeader";
import { SubscriptionBadge } from "@/components/StatusBadge";
import { useTenant } from "@/context/TenantContext";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";

const MONTH_OPTIONS = [1, 3, 12] as const;
type PaymentKind = "renewal" | "renewal_and_add_server";

const TIER_LABELS: Record<string, string> = {
  single: "1 карта",
  network3: "сеть до 3 карт",
  unlimited: "безлимит (до 50)",
};

function CheckoutBlock({
  title,
  description,
  kind,
  monthlyFee,
  feeHint,
  checkoutAvailable,
  disabled,
  disabledReason,
}: {
  title: string;
  description: string;
  kind: PaymentKind;
  monthlyFee: number;
  feeHint: string;
  checkoutAvailable: boolean;
  disabled?: boolean;
  disabledReason?: string;
}) {
  const [months, setMonths] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const amount = monthlyFee * months;

  const pay = async () => {
    setLoading(true);
    try {
      const r = await api.tenant.billingCheckout({
        payment_kind: kind,
        months: months as 1 | 3 | 12,
      });
      window.location.href = r.confirmation_url;
    } catch (err) {
      toast.error(formatApiError(err));
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {MONTH_OPTIONS.map((m) => (
            <Button
              key={m}
              type="button"
              variant={months === m ? "default" : "outline"}
              size="sm"
              onClick={() => setMonths(m)}
            >
              {m} мес.
            </Button>
          ))}
        </div>
        <p className="text-lg font-semibold">
          {amount.toLocaleString("ru-RU")} ₽
          <span className="text-sm font-normal text-muted-foreground ml-2">
            ({monthlyFee.toLocaleString("ru-RU")} ₽/мес × {months}; {feeHint})
          </span>
        </p>
        {disabled && disabledReason && (
          <p className="text-sm text-muted-foreground">{disabledReason}</p>
        )}
        {checkoutAvailable ? (
          <Button type="button" disabled={loading || disabled} onClick={pay}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Оплатить
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">
            Онлайн-оплата временно недоступна.{" "}
            <Link to="/app/support/new?subject=Продление+подписки" className="text-primary hover:underline">
              Написать в поддержку
            </Link>
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function ReduceLimitCard({
  serverCount,
  maxServers,
  onReduced,
}: {
  serverCount: number;
  maxServers: number;
  onReduced: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const newMax = maxServers - 1;
  const canReduce = maxServers > serverCount && maxServers > 1;

  const confirm = async () => {
    setLoading(true);
    try {
      await api.tenant.billingReduceLimit({ max_servers: newMax });
      toast.success(`Лимит уменьшен до ${newMax} инстанс(ов).`);
      setOpen(false);
      await onReduced();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Лимит инстансов</CardTitle>
        <CardDescription>
          Месячная цена считается по тарифу лимита ({maxServers} слот(ов)), не по числу заведённых
          серверов. Уменьшение лимита без возврата денег.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Заведено серверов: {serverCount} / лимит {maxServers}
        </p>
        {!canReduce && (
          <p className="text-sm text-muted-foreground">
            {maxServers <= 1
              ? "Минимальный лимит — 1 инстанс."
              : "Сначала удалите лишний инстанс на странице «Серверы», затем уменьшите лимит."}
          </p>
        )}
        <Button type="button" variant="outline" disabled={!canReduce} onClick={() => setOpen(true)}>
          Уменьшить лимит на 1 (до {newMax})
        </Button>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Уменьшить лимит до {newMax}?</DialogTitle>
              <DialogDescription>
                Деньги за уже оплаченный период не возвращаются. Следующее продление будет по тарифу
                нового лимита (1 карта / сеть до 3 / безлимит).
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Отмена
              </Button>
              <Button type="button" disabled={loading} onClick={confirm}>
                {loading && <Loader2 className="size-4 animate-spin" />}
                Подтвердить
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}

export default function TenantBillingPage() {
  const { subscription: sub, isLoading, reload } = useTenant();
  const [searchParams, setSearchParams] = useSearchParams();
  const reconcileStarted = useRef(false);

  useEffect(() => {
    const payment = searchParams.get("payment");
    const paymentId = searchParams.get("payment_id");
    if (payment !== "success") return;
    if (reconcileStarted.current) return;
    reconcileStarted.current = true;

    let cancelled = false;
    (async () => {
      try {
        if (!paymentId) {
          toast.success("Проверяем статус оплаты…");
          await reload();
          return;
        }
        const r = await api.tenant.billingReconcile({ payment_id: paymentId });
        if (cancelled) return;
        if (r.applied) {
          toast.success("Оплата зачислена. Подписка обновлена.");
        } else {
          toast.success("Оплата уже была зачислена ранее.");
        }
        await reload();
      } catch (err) {
        if (!cancelled) {
          const msg = formatApiError(err);
          if (msg.includes("уже обработан") || msg.includes("уже была зачислена")) {
            toast.success("Оплата уже была зачислена ранее.");
          } else {
            toast.error(msg);
          }
          await reload();
        }
      } finally {
        if (!cancelled) {
          searchParams.delete("payment");
          searchParams.delete("payment_id");
          setSearchParams(searchParams, { replace: true });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [searchParams, setSearchParams, reload]);

  const atServerCap = useMemo(() => (sub ? sub.max_servers >= 50 : false), [sub]);
  const slotsAvailable = sub ? sub.max_servers - sub.server_count : 0;
  const tierLabel = sub ? TIER_LABELS[sub.tier] ?? sub.tier : "";
  const addTarget = sub?.next_add_target_max ?? null;
  const addFee = sub?.next_add_monthly_fee_rub ?? null;
  const addIsUnlimited = addTarget != null && addTarget >= 50;

  if (isLoading && !sub) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Подписка и оплата" description="Статус подписки и продление автовыдачи" />

      {sub && (
        <>
          {sub.plan === "free_year" && sub.active && (
            <Alert>
              <AlertDescription>
                1 инстанс бесплатно до {sub.subscription_until}. Доп. карты и сети — по тарифам 699 /
                1490 ₽/мес после оплаты в ЛК.
              </AlertDescription>
            </Alert>
          )}

          {sub.active && sub.days_remaining <= 30 && sub.days_remaining >= 0 && (
            <Alert>
              <AlertTriangle className="size-4" />
              <AlertTitle>
                {sub.days_remaining === 0
                  ? "Подписка заканчивается сегодня"
                  : `Осталось ${sub.days_remaining} дн.`}
              </AlertTitle>
              <AlertDescription>
                {sub.plan === "free_year"
                  ? "После окончания срока автовыдача остановится до продления подписки."
                  : "Продлите подписку, чтобы Bridge продолжал выдачу покупок."}
              </AlertDescription>
            </Alert>
          )}

          {!sub.active && (
            <Alert variant="destructive">
              <AlertTriangle className="size-4" />
              <AlertTitle>Выдача остановлена</AlertTitle>
              <AlertDescription>
                Subscription gate активен. Продлите подписку для восстановления автовыдачи.
              </AlertDescription>
            </Alert>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CreditCard className="size-4" />
                Статус
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <SubscriptionBadge active={sub.active} until={sub.subscription_until} />
              <p className="text-sm">Действует до: {sub.subscription_until}</p>
              <p className="text-sm text-muted-foreground">
                Инстансов: {sub.server_count} / {sub.max_servers} · Тариф: {tierLabel} ·{" "}
                {sub.monthly_fee_rub.toLocaleString("ru-RU")} ₽/мес
              </p>
              <p className="text-sm">
                <a
                  href="https://example.com/offer"
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary hover:underline"
                >
                  Публичная оферта
                </a>
              </p>
            </CardContent>
          </Card>

          <CheckoutBlock
            title="Продление подписки"
            description={`Продлевает доступ (${tierLabel}, лимит ${sub.max_servers}) на выбранный срок.`}
            kind="renewal"
            monthlyFee={sub.monthly_fee_rub}
            feeHint={tierLabel}
            checkoutAvailable={sub.checkout_available}
          />

          {slotsAvailable > 0 && (
            <Alert>
              <AlertDescription>
                Свободных слотов: {slotsAvailable}.{" "}
                <Link to="/app/servers" className="text-primary hover:underline">
                  Добавьте сервер
                </Link>{" "}
                без дополнительной оплаты.
              </AlertDescription>
            </Alert>
          )}

          {sub.server_count >= sub.max_servers && !atServerCap && addFee != null && addTarget != null && (
            <CheckoutBlock
              title={addIsUnlimited ? "Перейти на безлимит и продлить" : "Добавить слот и продлить"}
              description={
                addIsUnlimited
                  ? `Один платёж: лимит ${sub.max_servers} → ${addTarget} (безлимит до 50 карт) и продление на выбранный срок.`
                  : `Один платёж: лимит ${sub.max_servers} → ${addTarget} и продление на выбранный срок.`
              }
              kind="renewal_and_add_server"
              monthlyFee={addFee}
              feeHint={
                addIsUnlimited
                  ? "безлимит"
                  : addTarget <= 3
                    ? "сеть до 3 карт"
                    : "безлимит"
              }
              checkoutAvailable={sub.checkout_available}
            />
          )}

          <ReduceLimitCard
            serverCount={sub.server_count}
            maxServers={sub.max_servers}
            onReduced={reload}
          />

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Нужна помощь?</CardTitle>
            </CardHeader>
            <CardContent>
              <Button asChild variant="secondary">
                <Link to="/app/support/new?subject=Продление+подписки">Написать в поддержку</Link>
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
