import { Card, CardContent } from "@/components/ui/card";

const INCLUDES = [
  {
    title: "Облачная выдача",
    text: "связь с магазином wargm и очередь заказов на нашей стороне",
  },
  {
    title: "Личный кабинет",
    text: "серверы, статус подписки, скачать настройки для мода",
  },
  { title: "Поддержка", text: "тикеты в личном кабинете" },
  {
    title: "Оформление в игре",
    text: "своё оформление окна магазина под стиль сервера",
  },
  {
    title: "Каталог выдачи",
    text: "редактор того, что выдаётся после покупки — в кабинете",
  },
];

export default function IncludesList() {
  return (
    <section id="includes" className="py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <h2 className="mb-8 text-2xl font-semibold tracking-tight">Что входит в подписку</h2>
        <Card className="divide-y divide-border py-0">
          <CardContent className="p-0">
            <ul className="divide-y divide-border">
              {INCLUDES.map((item) => (
                <li key={item.title} className="px-6 py-4">
                  <strong className="text-foreground">{item.title}</strong>
                  <span className="text-muted-foreground"> — {item.text}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
