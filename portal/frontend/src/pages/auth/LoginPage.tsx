import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { api, User } from "@/api/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = { onLogin: (u: User) => void };

export default function LoginPage({ onLogin }: Props) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    try {
      const user = await api.login(String(fd.get("email")), String(fd.get("password")));
      onLogin(user);
      navigate(user.role === "provider" ? "/admin" : "/app");
    } catch {
      setError("Неверный email или пароль");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="w-full max-w-[420px]">
      <CardHeader>
        <CardTitle>Вход</CardTitle>
        <CardDescription>Войдите в личный кабинет ShopClaim</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email" type="email" required autoComplete="username" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Пароль</Label>
            <Input id="password" name="password" type="password" required autoComplete="current-password" />
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Вход…" : "Войти"}
          </Button>
        </form>
        <p className="text-sm text-muted-foreground mt-4">
          <Link to="/forgot-password" className="text-primary hover:underline">
            Забыли пароль?
          </Link>
          {" · "}
          Первый вход?{" "}
          <Link to="/set-password" className="text-primary hover:underline">
            Задать пароль по приглашению
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
