import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api/client";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";

type Ticket = {
  id: number;
  subject: string;
  status: string;
  server_id: string | null;
  created_at: string;
};

type TicketMessage = { id: number; body: string; is_provider: boolean; created_at: string };

type TicketDetail = Ticket & { messages: TicketMessage[] };

const STATUS_OPTIONS = [
  { value: "all", label: "Все статусы" },
  { value: "open", label: "open" },
  { value: "waiting_subscriber", label: "waiting_subscriber" },
  { value: "waiting_provider", label: "waiting_provider" },
  { value: "resolved", label: "resolved" },
] as const;

function statusBadgeVariant(status: string): "default" | "secondary" | "outline" {
  if (status === "resolved") return "secondary";
  if (status === "waiting_provider") return "default";
  return "outline";
}

export default function AdminTicketsPage() {
  const { id } = useParams<{ id: string }>();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [loadingList, setLoadingList] = useState(!id);
  const [loadingDetail, setLoadingDetail] = useState(!!id);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoadingList(true);
    api.admin
      .tickets()
      .then((d) => setTickets(d as Ticket[]))
      .catch((err) => toast.error(String(err)))
      .finally(() => setLoadingList(false));
  }, []);

  useEffect(() => {
    if (id) {
      setLoadingDetail(true);
      api.admin
        .getTicket(Number(id))
        .then((d) => setDetail(d as TicketDetail))
        .catch((err) => toast.error(String(err)))
        .finally(() => setLoadingDetail(false));
    } else {
      setDetail(null);
      setLoadingDetail(false);
    }
  }, [id]);

  const filteredTickets = useMemo(() => {
    const q = search.trim().toLowerCase();
    return tickets.filter((t) => {
      if (statusFilter !== "all" && t.status !== statusFilter) return false;
      if (!q) return true;
      return (
        t.subject.toLowerCase().includes(q) ||
        String(t.id).includes(q) ||
        (t.server_id?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [tickets, statusFilter, search]);

  const reply = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!detail) return;
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await api.admin.replyTicket(detail.id, String(fd.get("body")));
      toast.success("Ответ отправлен");
      const d = await api.admin.getTicket(detail.id);
      setDetail(d as TicketDetail);
      form.reset();
    } catch (err) {
      toast.error(String(err));
    }
  };

  if (id) {
    if (loadingDetail || !detail) {
      return (
        <div className="space-y-6">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-96" />
          <Skeleton className="h-48 w-full" />
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <nav className="text-sm text-muted-foreground">
          <Link to="/admin/tickets" className="hover:text-foreground">
            ← Тикеты
          </Link>
        </nav>

        <PageHeader
          title={detail.subject}
          description={`#${detail.id}${detail.server_id ? ` · ${detail.server_id}` : ""}`}
          actions={<Badge variant={statusBadgeVariant(detail.status)}>{detail.status}</Badge>}
        />

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Переписка</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {detail.messages.map((m) => (
              <div key={m.id} className="rounded-lg border bg-muted/20 p-4">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{m.is_provider ? "Поддержка" : "Арендатор"}</span>
                  <span className="text-xs text-muted-foreground">{m.created_at}</span>
                </div>
                <p className="whitespace-pre-wrap text-sm">{m.body}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ответ</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={reply} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="body">Сообщение</Label>
                <Textarea id="body" name="body" rows={4} required />
              </div>
              <Button type="submit">Отправить</Button>
            </form>
          </CardContent>
        </Card>
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
        <span className="text-foreground">Тикеты</span>
      </nav>

      <PageHeader title="Тикеты" description="Обращения арендаторов в поддержку" />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Фильтры</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2 min-w-[180px]">
              <Label>Статус</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2 flex-1 min-w-[200px]">
              <Label htmlFor="ticket-search">Поиск</Label>
              <Input
                id="ticket-search"
                placeholder="ID, тема или server_id…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="overflow-x-auto pt-6">
          {loadingList ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Тема</TableHead>
                  <TableHead>Статус</TableHead>
                  <TableHead>Сервер</TableHead>
                  <TableHead>Создан</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTickets.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>
                      <Link to={`/admin/tickets/${t.id}`} className="text-primary hover:underline font-medium">
                        {t.id}
                      </Link>
                    </TableCell>
                    <TableCell>{t.subject}</TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(t.status)}>{t.status}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{t.server_id ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">{t.created_at}</TableCell>
                  </TableRow>
                ))}
                {!filteredTickets.length && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      {tickets.length ? "Нет тикетов по фильтру" : "Тикетов пока нет"}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
