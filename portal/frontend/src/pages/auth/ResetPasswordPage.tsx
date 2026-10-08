import { FormEvent, useState, type ClipboardEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "@/api/client";
import { normalizeActionCode } from "@/utils/invite";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const initialCode = normalizeActionCode(searchParams.get("code") ?? "");
  const [code, setCode] = useState(initialCode);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    const normalized = normalizeActionCode(String(fd.get("code")));
    const password = String(fd.get("password"));
    try {
      await api.resetPassword(normalized, password);
      setDone(true);
    } catch {
      setError("Неверный или просроченный код");
    } finally {
      setBusy(false);
    }
  };

  const onCodePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData("text");
    if (!pasted.trim()) return;
    e.preventDefault();
    setCode(normalizeActionCode(pasted));
  };

  if (done) {
    return (
      <Card className="w-full max-w-[480px]">
        <CardHeader>
          <CardTitle>Пароль обновлён</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <CheckCircle2 className="size-4" />
            <AlertDescription>Войдите с новым паролем.</AlertDescription>
          </Alert>
          <Button type="button" className="w-full" onClick={() => navigate("/login", { replace: true })}>
            Войти
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-[480px]">
      <CardHeader>
        <CardTitle>Новый пароль</CardTitle>
        <CardDescription>Код из письма для сброса пароля</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="code">Код</Label>
            <Input
              id="code"
              name="code"
              required
              minLength={32}
              maxLength={128}
              autoComplete="off"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onPaste={onCodePaste}
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Новый пароль (мин. 10 символов)</Label>
            <Input
              id="password"
              name="password"
              type="password"
              required
              minLength={10}
              maxLength={128}
              autoComplete="new-password"
            />
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Сохранение…" : "Сохранить пароль"}
          </Button>
        </form>
        <p className="text-sm text-muted-foreground mt-4">
          <Link to="/login" className="text-primary hover:underline">
            Войти
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
