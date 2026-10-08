import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { api } from "@/api/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    const website = String(fd.get("website") ?? "");
    if (website) {
      setSent(true);
      setBusy(false);
      return;
    }
    try {
      await api.forgotPassword(String(fd.get("email")));
      setSent(true);
    } catch {
      setSent(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="w-full max-w-[420px]">
      <CardHeader>
        <CardTitle>Забыли пароль?</CardTitle>
        <CardDescription>
          Если аккаунт существует, мы отправим ссылку для сброса на указанный email.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {sent ? (
          <Alert>
            <CheckCircle2 className="size-4" />
            <AlertDescription>
              Если email зарегистрирован, письмо со ссылкой для сброса отправлено. Проверьте почту.
            </AlertDescription>
          </Alert>
        ) : (
          <form onSubmit={onSubmit} className="grid gap-4">
            <input type="text" name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden />
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" name="email" type="email" required autoComplete="email" />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? "Отправка…" : "Отправить ссылку"}
            </Button>
          </form>
        )}
        <p className="text-sm text-muted-foreground mt-4">
          <Link to="/login" className="text-primary hover:underline">
            Вернуться ко входу
          </Link>
          {" · "}
          <Link to="/set-password" className="text-primary hover:underline">
            Есть invite-код
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
