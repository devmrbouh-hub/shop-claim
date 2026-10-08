import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api/client";
import { inviteSetPasswordUrl } from "@/utils/invite";
import CopyField from "@/components/CopyField";
import PageHeader from "@/components/PageHeader";
import { DeployBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type TenantUser = { id: number; email: string; is_active: boolean; has_password: boolean };
type Server = {
  server_id: string;
  shop_server_id: number;
  api_token_masked: string;
  enabled: boolean;
};
type TenantDetail = {
  tenant_id: string;
  enabled: boolean;
  subscription_until: string;
  max_servers: number;
  server_count: number;
  deploy_status: string | null;
  wargm_configured: boolean;
  wargm_shop_id: string;
  servers: Server[];
  users: TenantUser[];
};

type BillingPayment = {
  id: string;
  payment_kind: string;
  months: number;
  amount_rub: number;
  status: string;
  created_at: string;
  paid_at: string | null;
};

export default function AdminTenantPage() {
  const { slug } = useParams<{ slug: string }>();
  const [tenant, setTenant] = useState<TenantDetail | null>(null);
  const [payments, setPayments] = useState<BillingPayment[]>([]);
  const [billingPrice, setBillingPrice] = useState(299);
  const [inviteCode, setInviteCode] = useState("");
  const [subscriptionUntil, setSubscriptionUntil] = useState("");
  const [maxServers, setMaxServers] = useState(1);
  const [enabled, setEnabled] = useState(true);

  const reload = () => {
    if (!slug) return;
    api.admin.getTenant(slug).then((d) => {
      const t = d as TenantDetail;
      setTenant(t);
      setSubscriptionUntil(t.subscription_until);
      setMaxServers(t.max_servers);
      setEnabled(t.enabled);
    });
    api.admin.getTenantPayments(slug).then((d) => setPayments(d as BillingPayment[])).catch(() => {});
    api.admin.getBillingSettings().then((d) => {
      const s = d as { price_per_server_rub: number };
      setBillingPrice(s.price_per_server_rub);
    }).catch(() => {});
  };

  useEffect(() => {
    reload();
  }, [slug]);

  const saveSettings = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!slug) return;
    const fd = new FormData(e.currentTarget);
    const nextEnabled = fd.get("enabled") === "on";
    if (!nextEnabled && tenant?.enabled) {
      const ok = window.confirm(
        "Отключить tenant? Арендатор сразу потеряет доступ к личному кабинету.",
      );
      if (!ok) return;
    }
    try {
      await api.admin.updateTenant(slug, {
        subscription_until: String(fd.get("subscription_until")),
        max_servers: Number(fd.get("max_servers")),
        enabled: nextEnabled,
      });
      toast.success("Настройки сохранены");
      reload();
    } catch (err) {
      toast.error(String(err));
    }
  };

  const addServer = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!slug) return;
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await api.admin.addServer(slug, {
        server_id: fd.get("server_id"),
        shop_server_id: Number(fd.get("shop_server_id")),
      });
      toast.success("Сервер добавлен");
      reload();
      form.reset();
    } catch (err) {
      toast.error(String(err));
    }
  };

  const extendDays = async (days: 30 | 365) => {
    if (!slug) return;
    try {
      const r = await api.admin.extendTenant(slug, days);
      toast.success(`Подписка до ${r.subscription_until}`);
      reload();
    } catch (err) {
      toast.error(String(err));
    }
  };

  const sendInvite = async (userId: number) => {
    try {
      const r = await api.admin.invite(userId);
      setInviteCode(r.invite_code);
      toast.success(
        r.email_sent === "true" ? "Приглашение отправлено на email" : "Скопируйте код приглашения ниже",
      );
    } catch (err) {
      toast.error(String(err));
    }
  };

  if (!tenant) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  const quotaFull = tenant.server_count >= tenant.max_servers;

  return (
    <div className="space-y-6">
      <nav className="text-sm text-muted-foreground">
        <Link to="/admin" className="hover:text-foreground">
          Обзор
        </Link>
        {" / "}
        <span className="text-foreground">{tenant.tenant_id}</span>
        {" · "}
        <Link to={`/admin/tenants/${slug}/catalog`} className="hover:text-foreground">
          Каталог
        </Link>
      </nav>

      <PageHeader title={`Tenant: ${tenant.tenant_id}`} />

      {!tenant.enabled && (
        <Alert variant="destructive">
          <AlertDescription>Tenant отключён — арендатор не может войти в ЛК</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Обзор</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>
            Серверы:{" "}
            <span className="font-medium">
              {tenant.server_count} / {tenant.max_servers}
            </span>
            {" · "}
            Deploy: <DeployBadge status={tenant.deploy_status} />
          </p>
          <p className="text-muted-foreground">
            Wargm:{" "}
            {tenant.wargm_configured ? (
              <>
                настроен (<span className="font-mono">{tenant.wargm_shop_id}</span>)
              </>
            ) : (
              "заполнит арендатор в ЛК"
            )}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Настройки tenant</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={saveSettings} className="grid max-w-lg gap-4">
            <div className="space-y-2">
              <Label htmlFor="subscription_until">Подписка до</Label>
              <Input
                id="subscription_until"
                name="subscription_until"
                type="date"
                required
                value={subscriptionUntil}
                onChange={(e) => setSubscriptionUntil(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_servers">Лимит серверов</Label>
              <Input
                id="max_servers"
                name="max_servers"
                type="number"
                required
                min={Math.max(1, tenant.server_count)}
                max={50}
                value={maxServers}
                onChange={(e) => setMaxServers(Number(e.target.value))}
              />
              <p className="text-xs text-muted-foreground">
                Подсказка: {billingPrice} × {maxServers} = {billingPrice * maxServers} ₽/мес при продлении
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="secondary" size="sm" onClick={() => extendDays(30)}>
                +30 дней
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => extendDays(365)}>
                +365 дней
              </Button>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <input
                  id="enabled"
                  name="enabled"
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                  className="size-4 rounded border border-input accent-primary"
                />
                <Label htmlFor="enabled" className="font-normal">
                  Tenant активен
                </Label>
              </div>
              <p className="text-sm text-muted-foreground">Снятие галочки блокирует доступ арендатора к ЛК.</p>
            </div>
            <Button type="submit">Сохранить настройки</Button>
          </form>
        </CardContent>
      </Card>

      {payments.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Платежи</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Дата</TableHead>
                  <TableHead>Тип</TableHead>
                  <TableHead>Мес.</TableHead>
                  <TableHead>Сумма</TableHead>
                  <TableHead>Статус</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="text-sm">{p.created_at.slice(0, 10)}</TableCell>
                    <TableCell className="text-sm">{p.payment_kind}</TableCell>
                    <TableCell>{p.months}</TableCell>
                    <TableCell>{p.amount_rub} ₽</TableCell>
                    <TableCell>{p.status}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Пользователи</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {tenant.users.map((u) => (
            <div key={u.id} className="flex flex-wrap items-center justify-between gap-3 border-b pb-4 last:border-0 last:pb-0">
              <div>
                <p className="font-medium">{u.email}</p>
                <Badge variant="outline" className="mt-1 font-normal">
                  {u.is_active ? "активен" : "ожидает пароль"}
                </Badge>
              </div>
              <Button type="button" variant="secondary" size="sm" onClick={() => sendInvite(u.id)}>
                Отправить invite
              </Button>
            </div>
          ))}

          {inviteCode && (
            <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
              <p className="text-sm">
                Передайте арендатору ссылку (код подставится автоматически) или код для{" "}
                <Link to="/set-password" className="text-primary hover:underline">
                  /set-password
                </Link>
                :
              </p>
              <CopyField label="Ссылка для арендатора" value={inviteSetPasswordUrl(inviteCode)} />
              <CopyField label="Код приглашения" value={inviteCode} />
              <p className="text-sm text-muted-foreground">
                После установки пароля арендатор входит на /login своим email и новым паролем.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Серверы</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {tenant.servers.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>server_id</TableHead>
                    <TableHead>shop_server_id</TableHead>
                    <TableHead>Token</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenant.servers.map((s) => (
                    <TableRow key={s.server_id}>
                      <TableCell className="font-medium">{s.server_id}</TableCell>
                      <TableCell>{s.shop_server_id}</TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">{s.api_token_masked}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Серверов пока нет.</p>
          )}

          {!quotaFull ? (
            <form onSubmit={addServer} className="grid max-w-lg gap-4 border-t pt-4">
              <div className="space-y-2">
                <Label htmlFor="server_id">server_id</Label>
                <Input id="server_id" name="server_id" required pattern="[a-zA-Z0-9_]{3,64}" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="shop_server_id">shop_server_id</Label>
                <Input id="shop_server_id" name="shop_server_id" type="number" required min={1} />
              </div>
              <Button type="submit">Добавить сервер (оператор)</Button>
            </form>
          ) : (
            <p className="text-sm text-muted-foreground border-t pt-4">
              Квота исчерпана ({tenant.server_count} из {tenant.max_servers}). Увеличьте лимит серверов в настройках
              выше или попросите арендатора удалить неиспользуемый инстанс.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
