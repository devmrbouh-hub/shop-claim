import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { api } from "@/api/client";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Ticket = {
  id: number;
  subject: string;
  status: string;
  server_id: string | null;
  created_at: string;
};

function ticketStatusClass(status: string): string {
  if (status === "resolved") return "border-muted-foreground/30 text-muted-foreground";
  if (status === "open") return "border-primary/50 text-primary bg-primary/10";
  return "border-warning/50 text-warning bg-warning/10";
}

export default function TenantTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);

  useEffect(() => {
    api.tenant.tickets().then((d) => setTickets(d as Ticket[]));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Поддержка"
        actions={
          <Button asChild>
            <Link to="/app/support/new">
              <Plus className="size-4" />
              Новый тикет
            </Link>
          </Button>
        }
      />

      {tickets === null ? (
        <Card>
          <CardContent className="pt-6 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      ) : tickets.length === 0 ? (
        <EmptyState
          title="Тикетов пока нет"
          hint="Создайте тикет, если нужна помощь с настройкой или возникла проблема."
          action={
            <Button asChild>
              <Link to="/app/support/new">Создать тикет</Link>
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
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
                {tickets.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>
                      <Link to={`/app/support/${t.id}`} className="font-medium text-primary hover:underline">
                        #{t.id}
                      </Link>
                    </TableCell>
                    <TableCell>{t.subject}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={ticketStatusClass(t.status)}>
                        {t.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{t.server_id ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(t.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
