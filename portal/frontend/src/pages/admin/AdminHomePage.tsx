import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, User } from "@/api/client";
import AccountSettings from "@/pages/account/AccountSettings";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";

type Lead = {
  id: number;
  project_name: string;
  email: string;
  telegram: string | null;
  status: string;
  instance_count: number;
};

type Tenant = {
  id: number;
  tenant_id: string;
  enabled: boolean;
  subscription_until: string;
  deploy_status: string | null;
  server_count: number;
  max_servers: number;
};

type TenantPrefill = {
  lead_id: number;
  subscriber_email: string;
  max_servers: number;
  tenant_id: string;
};

function slugFromProject(name: string): string {
  const s = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 31);
  if (s.length >= 3 && /^[a-z]/.test(s)) return s;
  return `t_${Date.now().toString(36).slice(-8)}`;
}

export default function AdminHomePage({
  user,
  onUserUpdate,
}: {
  user: User;
  onUserUpdate: (user: User) => void;
}) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [syncMsg, setSyncMsg] = useState("");
  const [prefill, setPrefill] = useState<TenantPrefill | null>(null);

  const reload = () => {
    api.admin.leads().then((d) => setLeads(d as Lead[]));
    api.admin.tenants().then((d) => setTenants(d as Tenant[]));
  };

  useEffect(() => {
    reload();
  }, []);

  const startFromLead = (lead: Lead) => {
    setPrefill({
      lead_id: lead.id,
      subscriber_email: lead.email,
      max_servers: lead.instance_count,
      tenant_id: slugFromProject(lead.project_name),
    });
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  };

  const rejectLead = async (leadId: number) => {
    try {
      await api.admin.rejectLead(leadId);
      toast.success("Заявка отклонена");
      reload();
    } catch (err) {
      toast.error(String(err));
    }
  };

  const createTenant = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const wargmShop = String(fd.get("wargm_shop_id") || "").trim();
    const wargmKey = String(fd.get("wargm_api_key") || "").trim();
    try {
      await api.admin.createTenant({
        tenant_id: fd.get("tenant_id"),
        subscription_until: fd.get("subscription_until"),
        max_servers: Number(fd.get("max_servers") || 1),
        wargm_shop_id: wargmShop,
        wargm_api_key: wargmKey,
        lead_id: (() => {
          const lid = fd.get("lead_id");
          return lid && String(lid).trim() ? Number(lid) : null;
        })(),
        subscriber_email: fd.get("subscriber_email") || null,
        theme_prefix: fd.get("theme_prefix") || null,
      });
      toast.success("Tenant создан — откройте карточку и отправьте invite");
      setPrefill(null);
      reload();
      form.reset();
    } catch (err) {
      toast.error(String(err));
    }
  };

  const sync = async (dry: boolean) => {
    try {
      const r = (await api.admin.syncBridge(dry)) as { message: string };
      setSyncMsg(r.message);
      toast.success(r.message);
      reload();
    } catch (err) {
      setSyncMsg(String(err));
      toast.error(String(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Обзор" description="Заявки, tenants и синхронизация Bridge" />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Заявки</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Проект</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Инстансы</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {leads.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>{l.id}</TableCell>
                  <TableCell>{l.project_name}</TableCell>
                  <TableCell>{l.email}</TableCell>
                  <TableCell>{l.instance_count}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{l.status}</Badge>
                  </TableCell>
                  <TableCell>
                    {l.status === "new" && (
                      <div className="flex gap-2">
                        <Button type="button" variant="secondary" size="sm" onClick={() => startFromLead(l)}>
                          Создать tenant
                        </Button>
                        <Button type="button" variant="outline" size="sm" onClick={() => rejectLead(l.id)}>
                          Отклонить
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Создать tenant</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={createTenant} key={prefill?.lead_id ?? "new"} className="grid gap-4 max-w-lg">
            <div className="space-y-2">
              <Label htmlFor="tenant_id">tenant_id (slug)</Label>
              <Input id="tenant_id" name="tenant_id" required pattern="[a-z][a-z0-9_]{2,31}" defaultValue={prefill?.tenant_id} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="subscription_until">subscription_until</Label>
              <Input
                id="subscription_until"
                name="subscription_until"
                type="date"
                defaultValue={(() => {
                  const d = new Date();
                  d.setDate(d.getDate() + 365);
                  return d.toISOString().slice(0, 10);
                })()}
              />
              <p className="text-xs text-muted-foreground">По умолчанию +365 дн. (free year). Можно оставить пустым — API подставит сам.</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_servers">Лимит серверов</Label>
              <Input id="max_servers" name="max_servers" type="number" min={1} max={50} defaultValue={prefill?.max_servers ?? 1} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="wargm_shop_id">wargm shop_id (опц.)</Label>
              <Input id="wargm_shop_id" name="wargm_shop_id" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="wargm_api_key">wargm api_key (опц.)</Label>
              <Input id="wargm_api_key" name="wargm_api_key" type="password" />
            </div>
            <input type="hidden" name="lead_id" value={prefill?.lead_id ?? ""} />
            <div className="space-y-2">
              <Label htmlFor="subscriber_email">email арендатора</Label>
              <Input id="subscriber_email" name="subscriber_email" type="email" defaultValue={prefill?.subscriber_email} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="theme_prefix">theme_prefix</Label>
              <Input id="theme_prefix" name="theme_prefix" placeholder="ShopClaimTheme" />
            </div>
            <Button type="submit">Создать</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tenants</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Серверы</TableHead>
                  <TableHead>Deploy</TableHead>
                  <TableHead>До</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>
                      <Link to={`/admin/tenants/${t.tenant_id}`} className="text-primary hover:underline font-medium">
                        {t.tenant_id}
                      </Link>
                      {" · "}
                      <Link to={`/admin/tenants/${t.tenant_id}/catalog`} className="text-muted-foreground hover:underline text-sm">
                        каталог
                      </Link>
                    </TableCell>
                    <TableCell>
                      {t.server_count} / {t.max_servers}
                    </TableCell>
                    <TableCell>{t.deploy_status}</TableCell>
                    <TableCell>{t.subscription_until}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => sync(true)}>
              Dry-run sync
            </Button>
            <Button type="button" onClick={() => sync(false)}>
              Применить на Bridge
            </Button>
          </div>
          {syncMsg && (
            <Alert>
              <AlertDescription>{syncMsg}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <AccountSettings user={user} onUserUpdate={onUserUpdate} />
    </div>
  );
}
