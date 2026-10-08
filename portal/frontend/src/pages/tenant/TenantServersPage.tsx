import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Plus, Server, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import EmptyState from "@/components/EmptyState";
import ConfigInstallHint from "@/components/ConfigInstallHint";
import PageHeader from "@/components/PageHeader";
import QuotaMeter from "@/components/QuotaMeter";
import { useTenant } from "@/context/TenantContext";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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

export default function TenantServersPage() {
  const { subscription: sub, servers, reload } = useTenant();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const downloadConfig = (serverId: string) => {
    window.open(`/api/tenant/servers/${encodeURIComponent(serverId)}/config.json`, "_blank");
  };

  const addServer = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    setBusy(true);
    try {
      await api.tenant.createServer({
        server_id: String(fd.get("server_id")),
        shop_server_id: Number(fd.get("shop_server_id")),
      });
      toast.success("Сервер добавлен");
      await reload();
      form.reset();
      setDialogOpen(false);
    } catch (err) {
      toast.error(String(err));
    } finally {
      setBusy(false);
    }
  };

  const removeServer = async (serverId: string) => {
    if (!window.confirm(`Удалить сервер ${serverId}?`)) return;
    try {
      await api.tenant.deleteServer(serverId);
      toast.success("Сервер удалён");
      await reload();
    } catch (err) {
      toast.error(String(err));
    }
  };

  const slotsLeft = sub ? sub.max_servers - sub.server_count : 0;
  const canAdd = sub?.wargm_configured && slotsLeft > 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Мои серверы"
        actions={
          canAdd ? (
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="size-4" />
                  Добавить сервер
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Добавить сервер</DialogTitle>
                  <DialogDescription>
                    server_id — уникальное имя инстанса. shop_server_id — из мониторинга wargm.
                  </DialogDescription>
                </DialogHeader>
                <form id="add-server-form" onSubmit={addServer} className="grid gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="server_id">server_id (латиница)</Label>
                    <Input
                      id="server_id"
                      name="server_id"
                      required
                      pattern="[a-zA-Z0-9_]{3,64}"
                      placeholder="myserver_chernarus"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="shop_server_id">shop_server_id</Label>
                    <Input id="shop_server_id" name="shop_server_id" type="number" required min={1} />
                  </div>
                </form>
                <DialogFooter>
                  <Button type="submit" form="add-server-form" disabled={busy}>
                    {busy ? "Добавление…" : "Добавить сервер"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          ) : undefined
        }
      />

      {sub && <QuotaMeter count={sub.server_count} max={sub.max_servers} />}

      {sub && (
        <Alert>
          <AlertDescription>
            Чтобы сменить карту без оплаты — удалите инстанс и добавьте новый. Чтобы платить за меньше
            слотов — удалите лишние инстансы, затем уменьшите лимит в{" "}
            <Link to="/app/billing" className="text-primary hover:underline">
              «Подписка и оплата»
            </Link>
            .
          </AlertDescription>
        </Alert>
      )}

      {sub?.wargm_configured && (
        <Alert>
          <AlertDescription>
            <ConfigInstallHint variant="compact" />
          </AlertDescription>
        </Alert>
      )}

      {!sub?.wargm_configured && (
        <Alert>
          <AlertDescription>
            Сначала подключите wargm в{" "}
            <Link to="/app/wargm" className="font-medium underline underline-offset-4">
              разделе Wargm
            </Link>
            .
          </AlertDescription>
        </Alert>
      )}

      {servers.length === 0 && sub?.wargm_configured && (
        <EmptyState
          title="Нет серверов"
          hint="Добавьте первый DayZ-инстанс. shop_server_id — из мониторинга wargm."
          icon={<Server className="size-10" />}
          action={
            canAdd ? (
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="size-4" />
                Добавить сервер
              </Button>
            ) : undefined
          }
        />
      )}

      {servers.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>server_id</TableHead>
                  <TableHead>shop_server_id</TableHead>
                  <TableHead>token</TableHead>
                  <TableHead className="text-right">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {servers.map((s) => (
                  <TableRow key={s.server_id}>
                    <TableCell className="font-medium">{s.server_id}</TableCell>
                    <TableCell>{s.shop_server_id}</TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">
                      {s.api_token_masked}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => downloadConfig(s.server_id)}
                        >
                          <Download className="size-4" />
                          config.json
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => removeServer(s.server_id)}
                        >
                          <Trash2 className="size-4" />
                          Удалить
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {sub && slotsLeft === 0 && sub.server_count > 0 && (
        <Alert>
          <AlertDescription>
            Все слоты заняты ({sub.server_count} из {sub.max_servers}).{" "}
            <Link
              to="/app/support/new?subject=Запрос+дополнительного+слота"
              className="font-medium underline underline-offset-4"
            >
              Запросить слот через тикет
            </Link>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
