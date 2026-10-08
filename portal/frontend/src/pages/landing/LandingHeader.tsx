import BrandLogo from "@/components/BrandLogo";
import { Button } from "@/components/ui/button";

type Props = { standalone?: boolean };

const LK = "https://lk.example.com";

export default function LandingHeader({ standalone }: Props) {
  const loginHref = standalone ? `${LK}/login` : "/login";

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 px-5 py-3.5">
        <a href="#top" className="text-foreground no-underline hover:text-foreground">
          <BrandLogo />
        </a>

        <nav className="hidden flex-1 flex-wrap gap-4 md:flex">
          <a
            href="#how"
            className="text-sm text-muted-foreground no-underline transition-colors hover:text-foreground"
          >
            Как работает
          </a>
          <a
            href="#why"
            className="text-sm text-muted-foreground no-underline transition-colors hover:text-foreground"
          >
            Преимущества
          </a>
          <a
            href="#pricing"
            className="text-sm text-muted-foreground no-underline transition-colors hover:text-foreground"
          >
            Тарифы
          </a>
          <a
            href="#faq"
            className="text-sm text-muted-foreground no-underline transition-colors hover:text-foreground"
          >
            FAQ
          </a>
        </nav>

        <div className="ml-auto flex flex-wrap gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={loginHref}>Войти в ЛК</a>
          </Button>
          <Button size="sm" asChild>
            <a href="#apply">Оставить заявку</a>
          </Button>
        </div>
      </div>
    </header>
  );
}
