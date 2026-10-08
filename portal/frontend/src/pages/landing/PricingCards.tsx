import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const LK = "https://lk.example.com";

type Props = { standalone?: boolean };

type PublicPricing = {
  price_per_server_rub: number;
  network3_rub: number;
  unlimited_rub: number;
};

export default function PricingCards({ standalone }: Props) {
  const [pricing, setPricing] = useState<PublicPricing>({
    price_per_server_rub: 299,
    network3_rub: 699,
    unlimited_rub: 1490,
  });
  const loginHref = standalone ? `${LK}/login` : "/login";

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE ?? LK;
    fetch(`${apiBase}/api/public/pricing`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setPricing({
          price_per_server_rub: d.price_per_server_rub ?? 299,
          network3_rub: d.network3_rub ?? 699,
          unlimited_rub: d.unlimited_rub ?? 1490,
        });
      })
      .catch(() => {});
  }, []);

  const { price_per_server_rub: price1, network3_rub: net3, unlimited_rub: unlim } = pricing;

  const PLANS = [
    {
      title: "Первый год",
      text: "1 карта DayZ — 12 месяцев бесплатно. Полный доступ: выдача, кабинет, каталог.",
      footnote: `После года — ${price1} ₽/мес за 1 карту`,
      badge: "Бесплатно",
      highlighted: true,
    },
    {
      title: "1 карта",
      text: `${price1} ₽/мес после бесплатного года. Оплата в личном кабинете.`,
      footnote: null,
      badge: null,
      highlighted: false,
    },
    {
      title: "Сеть и безлимит",
      text: `До 3 карт — ${net3} ₽/мес. Без лимита карт — ${unlim} ₽/мес. Оформление окна в игре входит.`,
      footnote: null,
      badge: "Сети",
      highlighted: false,
    },
  ];

  return (
    <section id="pricing" className="py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <h2 className="mb-2 text-2xl font-semibold tracking-tight">Тарифы</h2>
        <p className="mb-8 text-sm text-muted-foreground">
          Ступени: <strong className="text-foreground">{price1} ₽</strong> (1 карта) ·{" "}
          <strong className="text-foreground">{net3} ₽</strong> (до 3) ·{" "}
          <strong className="text-foreground">{unlim} ₽</strong> (безлимит). После оплаты автовыдача
          снова включается автоматически.
        </p>
        <img
          src="/landing/pricing-free-year.webp"
          alt="Первая карта DayZ — 12 месяцев бесплатно. Автовыдача доната wargm в игре"
          className="mx-auto mb-8 max-w-md w-full rounded-lg border border-border/60"
          width={800}
          height={533}
          loading="lazy"
          decoding="async"
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <Card
              key={plan.title}
              className={cn(
                "gap-4 py-5",
                plan.highlighted && "border-primary/50 ring-1 ring-primary/20",
              )}
            >
              <CardHeader className="gap-3 px-5 pb-0">
                {plan.badge && (
                  <Badge variant={plan.highlighted ? "default" : "outline"} className="w-fit">
                    {plan.badge}
                  </Badge>
                )}
                <CardTitle className="text-base">{plan.title}</CardTitle>
              </CardHeader>
              <CardContent className="px-5 pt-0">
                <p className="text-sm text-muted-foreground leading-relaxed">{plan.text}</p>
              </CardContent>
              {plan.footnote && (
                <CardFooter className="px-5 pt-0">
                  <p className="text-xs text-muted-foreground">{plan.footnote}</p>
                </CardFooter>
              )}
            </Card>
          ))}
        </div>
        <div className="mt-8">
          <Button asChild>
            <a href={loginHref}>Войти в ЛК</a>
          </Button>
        </div>
      </div>
    </section>
  );
}
