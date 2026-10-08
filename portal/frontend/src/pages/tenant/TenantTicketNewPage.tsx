import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import PageHeader from "@/components/PageHeader";
import { useTenant } from "@/context/TenantContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

export default function TenantTicketNewPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { servers } = useTenant();
  const [busy, setBusy] = useState(false);
  const defaultSubject = useMemo(() => searchParams.get("subject") ?? "", [searchParams]);
  const defaultServer = useMemo(() => searchParams.get("server_id") ?? "", [searchParams]);
  const [serverId, setServerId] = useState(defaultServer);

  const createTicket = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    setBusy(true);
    try {
      const ticket = (await api.tenant.createTicket({
        subject: fd.get("subject"),
        body: fd.get("body"),
        server_id: serverId || null,
        operation_id: fd.get("operation_id") || null,
      })) as { id: number };
      toast.success("Тикет создан");
      navigate(`/app/support/${ticket.id}`);
    } catch (err) {
      toast.error(String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Новый тикет" />

      <Button variant="ghost" size="sm" asChild className="-mt-2">
        <Link to="/app/support">
          <ArrowLeft className="size-4" />
          К списку тикетов
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Описание проблемы</CardTitle>
          <CardDescription>Не прикладывайте api_token или полный config.json в текст тикета.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createTicket} className="grid gap-4 max-w-xl">
            <div className="space-y-2">
              <Label htmlFor="subject">Тема</Label>
              <Input id="subject" name="subject" required defaultValue={defaultSubject} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="server_id">server_id (опц.)</Label>
              <Select
                value={serverId || "__none__"}
                onValueChange={(v) => setServerId(v === "__none__" ? "" : v)}
              >
                <SelectTrigger id="server_id" className="w-full">
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">—</SelectItem>
                  {servers.map((s) => (
                    <SelectItem key={s.server_id} value={s.server_id}>
                      {s.server_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="operation_id">operation_id (опц., из ЛК wargm)</Label>
              <Input id="operation_id" name="operation_id" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="body">Описание</Label>
              <Textarea id="body" name="body" rows={5} required />
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? "Создание…" : "Создать тикет"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
