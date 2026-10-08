import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

type Props = { standalone?: boolean };

const LK = "https://lk.example.com";

const HERO_ALT =
  "ShopClaim — автовыдача доната DayZ: покупки wargm сразу в игре. 1 год бесплатно на первую карту.";

export default function HeroSection({ standalone }: Props) {
  return (
    <section id="top" className="bg-gradient-mesh py-16 md:py-24">
      <div className="mx-auto max-w-5xl space-y-6 px-5">
        <h1 className="sr-only">Автовыдача доната DayZ: покупки wargm — сразу в игре</h1>
        <img
          src="/landing/hero-banner.webp"
          alt={HERO_ALT}
          className="w-full rounded-lg border border-border/60 shadow-lg"
          width={1280}
          height={853}
          loading="eager"
          decoding="async"
        />
        <div className="flex flex-wrap justify-center gap-3 sm:justify-start">
          <Button asChild>
            <a href="#apply">Оставить заявку</a>
          </Button>
          {standalone ? (
            <Button variant="outline" asChild>
              <a href={`${LK}/login`}>Войти в личный кабинет</a>
            </Button>
          ) : (
            <Button variant="outline" asChild>
              <Link to="/login">Войти в личный кабинет</Link>
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
