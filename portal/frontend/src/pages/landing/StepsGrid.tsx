import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STEPS = [
  {
    title: "Покупка на wargm",
    text: "Игрок оплачивает товар с автовыдачей в вашем магазине wargm.ru.",
  },
  {
    title: "Заказ в ShopClaim",
    text: "Заказ попадает в ShopClaim и готовится к выдаче на ваш сервер.",
  },
  {
    title: "Мод на сервере",
    text: "На сервер ставится мод ShopClaim — он получает заказ и готовит выдачу на карте.",
  },
  {
    title: "Забрать в игре",
    text: "Игрок нажимает Home, видит список покупок и нажимает «Забрать».",
  },
];

export default function StepsGrid() {
  return (
    <section id="how" className="py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <h2 className="mb-8 text-2xl font-semibold tracking-tight">Как работает автовыдача</h2>
        <img
          src="/landing/steps-how.webp"
          alt="Как работает автовыдача доната DayZ: покупка на wargm, заказ в ShopClaim, мод на сервере, забрать в игре по Home"
          className="mb-8 w-full rounded-lg border border-border/60"
          width={1120}
          height={747}
          loading="lazy"
          decoding="async"
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <Card key={s.title} className="gap-4 py-5">
              <CardHeader className="gap-3 px-5 pb-0">
                <Badge variant="outline" className="w-fit border-primary/40 text-primary">
                  {i + 1}
                </Badge>
                <CardTitle className="text-base">{s.title}</CardTitle>
              </CardHeader>
              <CardContent className="px-5 pt-0">
                <p className="text-sm text-muted-foreground leading-relaxed">{s.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
