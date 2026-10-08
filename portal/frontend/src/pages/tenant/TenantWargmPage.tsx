import { FormEvent, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import CopyField from "@/components/CopyField";
import PageHeader from "@/components/PageHeader";
import { useTenant } from "@/context/TenantContext";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const WARGM_API_DOCS = "https://wargm.ru/shop/api";

export default function TenantWargmPage() {
  const { subscription: sub, reload } = useTenant();
  const [busy, setBusy] = useState(false);

  const saveWargm = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    try {
      await api.tenant.putWargm({
        wargm_shop_id: String(fd.get("wargm_shop_id")),
        wargm_api_key: String(fd.get("wargm_api_key")),
        current_password: String(fd.get("current_password")),
      });
      toast.success("Ключи wargm сохранены");
      await reload();
      e.currentTarget.reset();
    } catch (err) {
      toast.error(String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Подключение wargm"
        description="shop_id и API key из личного кабинета wargm.ru (магазин → API)."
      />

      {sub?.wargm_configured && (
        <Alert>
          <CheckCircle2 className="size-4" />
          <AlertDescription>
            Wargm настроен. Чтобы сменить ключ — заполните форму ниже.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Справка</CardTitle>
          <CardDescription>Где найти shop_id и API key в личном кабинете wargm</CardDescription>
        </CardHeader>
        <CardContent>
          <CopyField label="Документация API wargm" value={WARGM_API_DOCS} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{sub?.wargm_configured ? "Обновить ключи" : "Подключить wargm"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={saveWargm} className="grid gap-4 max-w-lg">
            <div className="space-y-2">
              <Label htmlFor="wargm_shop_id">wargm shop_id</Label>
              <Input id="wargm_shop_id" name="wargm_shop_id" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="wargm_api_key">wargm api_key</Label>
              <Input id="wargm_api_key" name="wargm_api_key" required type="password" autoComplete="off" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="current_password">Текущий пароль</Label>
              <Input
                id="current_password"
                name="current_password"
                required
                type="password"
                autoComplete="current-password"
              />
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? "Сохранение…" : sub?.wargm_configured ? "Обновить ключи" : "Сохранить"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
