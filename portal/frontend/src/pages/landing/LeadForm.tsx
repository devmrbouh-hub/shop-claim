import { FormEvent, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type Props = { standalone?: boolean };

const LK = "https://lk.example.com";

export default function LeadForm({ standalone }: Props) {
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const apiBase = import.meta.env.VITE_API_BASE ?? LK;
  const setPasswordHref = standalone ? `${LK}/set-password` : "/set-password";

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitting(true);
    const fd = new FormData(e.currentTarget);
    try {
      const res = await fetch(`${apiBase}/api/public/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: fd.get("project_name"),
          email: fd.get("email"),
          telegram: fd.get("telegram") || null,
          instance_count: Number(fd.get("instance_count") || 1),
          comment: fd.get("comment") || null,
          website: fd.get("website") || null,
        }),
      });
      if (!res.ok) throw new Error("Ошибка отправки");
      setSent(true);
      toast.success("Заявка отправлена — мы свяжемся после рассмотрения");
    } catch {
      toast.error("Не удалось отправить заявку. Попробуйте позже.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section id="apply" className="py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <h2 className="mb-3 text-2xl font-semibold tracking-tight">Оставить заявку</h2>
        <p className="mb-8 text-muted-foreground">
          Рассмотрим заявку и пришлём приглашение в личный кабинет на email.
        </p>

        <Card className="py-6">
          <CardContent>
            {sent ? (
              <div className="space-y-4">
                <p className="text-success font-medium">
                  Спасибо! Мы свяжемся с вами после рассмотрения заявки.
                </p>
                <p>Что дальше:</p>
                <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed">
                  <li>Мы рассмотрим заявку (обычно 1–3 дня)</li>
                  <li>На email придёт invite для входа в ЛК</li>
                  <li>Настройте wargm, серверы и mod по чеклисту в ЛК</li>
                </ol>
                <p className="text-sm">
                  Уже есть invite?{" "}
                  <a href={setPasswordHref} className="text-primary hover:underline">
                    Задать пароль по приглашению
                  </a>
                </p>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="project_name">Название проекта / сервера</Label>
                  <Input id="project_name" name="project_name" required maxLength={120} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" name="email" type="email" required />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="telegram">Telegram (опционально, быстрее свяжемся)</Label>
                  <Input id="telegram" name="telegram" maxLength={64} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="instance_count">Число инстансов DayZ</Label>
                  <Input
                    id="instance_count"
                    name="instance_count"
                    type="number"
                    min={1}
                    max={10}
                    defaultValue={1}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="comment">Комментарий</Label>
                  <Textarea id="comment" name="comment" rows={3} maxLength={2000} />
                </div>
                <Label htmlFor="website" className="hp">
                  Website
                </Label>
                <Input
                  id="website"
                  className="hp"
                  name="website"
                  tabIndex={-1}
                  autoComplete="off"
                />
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Отправка…" : "Отправить заявку"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
