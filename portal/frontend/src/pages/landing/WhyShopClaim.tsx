import type { LucideIcon } from "lucide-react";
import { Check, Cloud, Gamepad2, Gift, Layers, LayoutDashboard, Store, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Advantage = {
  icon: LucideIcon;
  title: string;
  text: string;
};

const ADVANTAGES: Advantage[] = [
  {
    icon: Store,
    title: "Магазин остаётся на wargm",
    text: "Игроки покупают на wargm.ru — не нужен второй донат-сайт.",
  },
  {
    icon: Gamepad2,
    title: "Забрать прямо в игре",
    text: "Меню по Home — без сайта и без ожидания админа.",
  },
  {
    icon: Cloud,
    title: "Облачная выдача",
    text: "Связь с магазином и очередь заказов — у нас. На сервер — только моды ShopClaim.",
  },
  {
    icon: Gift,
    title: "Первый год бесплатно",
    text: "Одна карта DayZ — 12 месяцев без оплаты.",
  },
  {
    icon: LayoutDashboard,
    title: "Личный кабинет",
    text: "Серверы и что выдавать после покупки — в кабинете.",
  },
  {
    icon: Layers,
    title: "Несколько карт",
    text: "До 3 карт или без лимита — цены в блоке «Тарифы».",
  },
];

const OTHERS = [
  "Свой сайт магазина, платежи и отдельная настройка",
  "Игрок забирает покупку через сайт или ждёт админа",
  "Платите с первого месяца; оформление часто за доплату",
];

const SHOPCLAIM = [
  "Оставляете магазин на wargm.ru",
  "Игрок забирает в игре — клавиша Home",
  "Первый год бесплатно; оформление окна в игре без доплаты",
];

export default function WhyShopClaim() {
  return (
    <section id="why" className="bg-gradient-mesh py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <div className="mb-10 space-y-3">
          <h2 className="text-2xl font-semibold tracking-tight">Почему ShopClaim</h2>
          <p className="max-w-2xl text-muted-foreground leading-relaxed">
            Автовыдача доната DayZ для серверов с магазином на wargm: без второго сайта и без
            ручной выдачи админом.
          </p>
        </div>

        <img
          src="/landing/before-after.webp"
          alt="Автовыдача доната DayZ: игрок забирает покупку wargm сам в игре, без ручной выдачи админом"
          className="mx-auto mb-12 max-w-3xl w-full rounded-lg border border-border/60"
          width={960}
          height={640}
          loading="lazy"
          decoding="async"
        />

        <div className="mb-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ADVANTAGES.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.title} className="gap-4 py-5">
                <CardHeader className="gap-3 px-5 pb-0">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/30 bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" aria-hidden />
                  </div>
                  <CardTitle className="text-base">{item.title}</CardTitle>
                </CardHeader>
                <CardContent className="px-5 pt-0">
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.text}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Card className="py-5">
            <CardHeader className="px-5 pb-0">
              <CardTitle className="text-base text-muted-foreground">Обычный путь</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pt-4">
              <ul className="space-y-3 text-sm leading-relaxed text-muted-foreground">
                {OTHERS.map((line) => (
                  <li key={line} className="flex gap-2">
                    <X className="mt-0.5 h-4 w-4 shrink-0 opacity-60" aria-hidden />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="border-primary/30 bg-primary/5 py-5 ring-1 ring-primary/20">
            <CardHeader className="px-5 pb-0">
              <CardTitle className="text-base text-foreground">ShopClaim</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pt-4">
              <ul className="space-y-3 text-sm leading-relaxed">
                {SHOPCLAIM.map((line) => (
                  <li key={line} className="flex gap-2">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
