import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const FAQ = [
  {
    q: "Нужен ли магазин wargm?",
    a: "Да. ShopClaim работает с вашим магазином на wargm.ru. Нужны товары с автовыдачей — в настройках товара wargm тип выдачи api или online.",
  },
  {
    q: "Нужно ли делать свой донат-сайт?",
    a: "Нет. Игроки покупают на вашем магазине wargm.ru. ShopClaim добавляет автовыдачу в игре DayZ — без второго сайта и без переноса каталога.",
  },
  {
    q: "Сколько стоит первая карта?",
    a: "Первые 12 месяцев на одной карте DayZ — бесплатно. После года — продление по тарифу на сайте. Дополнительные карты — в блоке «Тарифы».",
  },
  {
    q: "Какие моды ставить?",
    a: "Обязательно: @CF, @ShopClaim на сервер и @ShopClaim_GUI у игроков. Своё оформление окна магазина в игре — по желанию.",
  },
  {
    q: "Нужен ли Expansion?",
    a: "Нет для базовой выдачи. Игрок забирает покупки через меню Home. Часть доп. функций (чат) может использовать Expansion, если он уже есть на сервере.",
  },
  {
    q: "Где хранятся секреты?",
    a: "Ключи магазина wargm и токены сервера выдаются в личном кабинете. Не публикуйте их в Discord и не кладите в открытые репозитории.",
  },
  {
    q: "Что если подписка истекла?",
    a: "Автовыдача останавливается, пока не продлите подписку в личном кабинете. После оплаты доступ восстанавливается.",
  },
  {
    q: "Как начать?",
    a: "Оставьте заявку на этом сайте. После одобрения придёт письмо: задаёте пароль, входите в кабинет, подключаете сервер и ставите моды по инструкции.",
  },
  {
    q: "Как связаться с поддержкой?",
    a: "После входа — тикеты в личном кабинете. До регистрации — форма заявки или email в подвале сайта.",
  },
  {
    q: "Есть ли страница статуса?",
    a: "Да: http://127.0.0.1:8790/status — доступность сервиса выдачи и личного кабинета.",
  },
];

export default function FaqAccordion() {
  return (
    <section id="faq" className="py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <h2 className="mb-8 text-2xl font-semibold tracking-tight">FAQ</h2>
        <Accordion type="single" collapsible defaultValue="item-0" className="rounded-xl border border-border bg-card px-4">
          {FAQ.map((item, i) => (
            <AccordionItem key={item.q} value={`item-${i}`}>
              <AccordionTrigger className="text-base hover:no-underline">{item.q}</AccordionTrigger>
              <AccordionContent className="text-muted-foreground leading-relaxed">{item.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
