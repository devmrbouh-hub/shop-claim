import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FIT = [
  "✅ Есть магазин wargm с товарами на автовыдачу (тип api или online)",
  "✅ Несколько карт / серверов DayZ",
  "✅ Готовы поставить @CF, @ShopClaim, @ShopClaim_GUI",
  "✅ Нужна автоматизация без дежурства админа в игре",
];

const NOT_FIT = [
  "❌ Нет магазина wargm",
  "❌ Нельзя установить моды на сервер",
  "❌ Нужен другой магазин (не wargm) — пока не поддерживаем",
];

export default function FitChecklist() {
  return (
    <section id="fit" className="py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <h2 className="mb-8 text-2xl font-semibold tracking-tight">Для кого</h2>
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="py-5">
            <CardHeader className="px-5 pb-0">
              <CardTitle className="text-base text-success">Подходит</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pt-4">
              <ul className="space-y-2 text-sm leading-relaxed">
                {FIT.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
          <Card className="py-5">
            <CardHeader className="px-5 pb-0">
              <CardTitle className="text-base text-muted-foreground">Не подходит</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pt-4">
              <ul className="space-y-2 text-sm leading-relaxed text-muted-foreground">
                {NOT_FIT.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
