import { useState } from "react";
import CopyField from "./CopyField";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type Props = { bridgeUrl: string };

export default function DiagnosticPanel({ bridgeUrl }: Props) {
  const [open, setOpen] = useState(false);
  const healthUrl = `${bridgeUrl}health`;
  const curlCmd = `curl -sS "${healthUrl}"`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Проверка связи с Bridge</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <CopyField label="Bridge URL" value={bridgeUrl} />
        <Button type="button" variant="outline" onClick={() => setOpen((v) => !v)}>
          {open ? "Скрыть инструкцию" : "Как проверить с game VDS"}
        </Button>
        {open && (
          <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
            <p className="text-sm text-muted-foreground">Выполните на Windows VDS с DayZ (не на ПК игрока):</p>
            <CopyField label="Команда" value={curlCmd} />
            <p className="text-sm text-muted-foreground">
              Ожидается JSON со статусом. Если ошибка — создайте тикет в разделе «Поддержка».
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
