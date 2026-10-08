type Props = { standalone?: boolean };

const STATUS = import.meta.env.VITE_STATUS_URL ?? "http://127.0.0.1:8790/status";

export default function LandingFooter({ standalone }: Props) {
  const loginHref = standalone ? "/login" : "/login";
  const offerHref = standalone ? "/offer" : "/offer";
  const privacyHref = standalone ? "/privacy" : "/privacy";

  return (
    <footer className="border-t border-border py-8 text-sm text-muted-foreground">
      <div className="mx-auto max-w-5xl space-y-2 px-5">
        <p>
          <strong className="text-foreground">ShopClaim</strong> — open-source snapshot
        </p>
        <p>
          <a href={loginHref} className="text-primary hover:underline">
            Войти в ЛК
          </a>
          {" · "}
          <a href={offerHref} className="text-primary hover:underline">
            Оферта (демо)
          </a>
          {" · "}
          <a href={privacyHref} className="text-primary hover:underline">
            Политика (демо)
          </a>
          {" · "}
          <a href="#why" className="text-primary hover:underline">
            Преимущества
          </a>
          {" · "}
          <a href={STATUS} className="text-primary hover:underline">
            Статус (локально)
          </a>
        </p>
        <p>
          Контакт для демо:{" "}
          <a href="mailto:support@example.com" className="text-primary hover:underline">
            support@example.com
          </a>
        </p>
      </div>
    </footer>
  );
}
