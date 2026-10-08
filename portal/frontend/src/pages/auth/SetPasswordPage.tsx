import { FormEvent, useState, type ClipboardEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { api, User } from "@/api/client";
import { normalizeInviteCode } from "@/utils/invite";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = { onLogin: (u: User) => void };

export default function SetPasswordPage({ onLogin }: Props) {
  const [searchParams] = useSearchParams();
  const initialCode = normalizeInviteCode(searchParams.get("code") ?? "");
  const [code, setCode] = useState(initialCode);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    const normalized = normalizeInviteCode(String(fd.get("code")));
    const password = String(fd.get("password"));
    try {
      const user = await api.setPassword(normalized, password);
      onLogin(user);
      navigate("/app", { replace: true });
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
    setCode(normalizeInviteCode(pasted));
  };

  return (
    <Card className="w-full max-w-[480px]">
      <CardHeader>
        <CardTitle>Задать пароль</CardTitle>
        <CardDescription>
          Код из письма или от оператора. Это не пароль — задайте новый пароль ниже.
        </CardDescription>
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
            {busy ? "Сохранение…" : "Сохранить и войти"}
          </Button>
        </form>
        <p className="text-sm text-muted-foreground mt-4">
          Уже задали пароль?{" "}
          <Link to="/login" className="text-primary hover:underline">
            Войти
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
