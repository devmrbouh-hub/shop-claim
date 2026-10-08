import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api/client";
import PageHeader from "@/components/PageHeader";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

type BillingSettings = {
  price_per_server_rub: number;
  billing_enabled: boolean;
  yookassa_configured: boolean;
};

export default function AdminBillingPage() {
  const [settings, setSettings] = useState<BillingSettings | null>(null);
  const [price, setPrice] = useState(299);
  const [billingEnabled, setBillingEnabled] = useState(true);

  const reload = () => {
    api.admin.getBillingSettings().then((d) => {
      const s = d as BillingSettings;
      setSettings(s);
      setPrice(s.price_per_server_rub);
      setBillingEnabled(s.billing_enabled);
    });
  };

  useEffect(() => {
    reload();
  }, []);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.admin.updateBillingSettings({
        price_per_server_rub: price,
        billing_enabled: billingEnabled,
      });
      toast.success("Настройки биллинга сохранены");
      reload();
    } catch (err) {
      toast.error(String(err));
    }
  };

  if (!settings) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <nav className="text-sm text-muted-foreground">
        <Link to="/admin" className="hover:text-foreground">
          Обзор
        </Link>
        {" / "}
        <span className="text-foreground">Биллинг</span>
      </nav>

      <PageHeader
        title="Биллинг"
        description="Глобальная цена подписки и приём платежей ЮKassa"
      />

      {!settings.yookassa_configured && (
        <Alert>
          <AlertDescription>
            ЮKassa не настроена на сервере (PORTAL_YOOKASSA_SHOP_ID / SECRET_KEY). Checkout в ЛК
            недоступен до настройки env.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Тариф</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={save} className="grid max-w-md gap-4">
            <div className="space-y-2">
              <Label htmlFor="price">Цена 1 карты, ₽/мес (не выше 699)</Label>
              <Input
                id="price"
                type="number"
                min={1}
                max={699}
                required
                value={price}
                onChange={(e) => setPrice(Number(e.target.value))}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                id="billing_enabled"
                type="checkbox"
                checked={billingEnabled}
                onChange={(e) => setBillingEnabled(e.target.checked)}
                className="size-4 rounded border border-input accent-primary"
              />
              <Label htmlFor="billing_enabled" className="font-normal">
                Оплата в ЛК включена
              </Label>
            </div>
            <Button type="submit">Сохранить</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Формулы</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>1 карта: {price} ₽/мес · сеть до 3: 699 ₽/мес · безлимит (до 50): 1490 ₽/мес</p>
          <p>Продление: monthly_fee(текущий лимит) × месяцы (1 / 3 / 12)</p>
          <p>
            Добавить слот: переход 1→2/3 по 699; с 3 карт — сразу безлимит 50 слотов за 1490 ₽/мес ×
            месяцы
          </p>
          <p>Webhook: https://lk.example.com/api/billing/yookassa/webhook</p>
        </CardContent>
      </Card>
    </div>
  );
}
