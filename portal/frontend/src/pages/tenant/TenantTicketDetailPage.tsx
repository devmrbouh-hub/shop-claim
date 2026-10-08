import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type TicketMessage = { id: number; body: string; is_provider: boolean; created_at: string };

type TicketDetail = {
  id: number;
  subject: string;
  status: string;
  server_id: string | null;
  messages: TicketMessage[];
};

function ticketStatusClass(status: string): string {
  if (status === "resolved") return "border-muted-foreground/30 text-muted-foreground";
  if (status === "open") return "border-primary/50 text-primary bg-primary/10";
  return "border-warning/50 text-warning bg-warning/10";
}

export default function TenantTicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    if (id) {
      api.tenant.getTicket(Number(id)).then((d) => setDetail(d as TicketDetail));
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const reply = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!detail) return;
    const form = e.currentTarget;
    const fd = new FormData(form);
    setBusy(true);
    try {
      await api.tenant.replyTicket(detail.id, String(fd.get("body")));
      toast.success("Ответ отправлен");
      form.reset();
      load();
    } catch (err) {
      toast.error(String(err));
    } finally {
      setBusy(false);
    }
  };

  if (!detail) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  const canReply = detail.status !== "resolved";

  return (
    <div className="space-y-6">
      <PageHeader title={`Тикет #${detail.id}`} />

      <Button variant="ghost" size="sm" asChild className="-mt-2">
        <Link to="/app/support">
          <ArrowLeft className="size-4" />
          К списку
        </Link>
      </Button>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-base">{detail.subject}</CardTitle>
            <Badge variant="outline" className={ticketStatusClass(detail.status)}>
              {detail.status}
            </Badge>
            {detail.server_id && (
              <span className="text-sm text-muted-foreground">· {detail.server_id}</span>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {detail.messages.map((m) => (
            <div
              key={m.id}
              className={cn(
                "rounded-lg border p-4",
                m.is_provider ? "border-primary/20 bg-primary/5" : "border-border bg-muted/30",
              )}
            >
              <div className="text-xs text-muted-foreground mb-2">
                {m.is_provider ? "Оператор" : "Вы"} · {new Date(m.created_at).toLocaleString()}
              </div>
              <pre className="whitespace-pre-wrap font-sans text-sm">{m.body}</pre>
            </div>
          ))}
        </CardContent>
      </Card>

      {canReply ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ответ</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={reply} className="grid gap-4">
              <div className="space-y-2">
                <Label htmlFor="body">Сообщение</Label>
                <Textarea id="body" name="body" rows={4} required />
              </div>
              <Button type="submit" disabled={busy}>
                {busy ? "Отправка…" : "Отправить"}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        <p className="text-sm text-muted-foreground">
          Тикет закрыт. Для нового вопроса{" "}
          <Link to="/app/support/new" className="text-primary hover:underline">
            создайте тикет
          </Link>
          .
        </p>
      )}
    </div>
  );
}
