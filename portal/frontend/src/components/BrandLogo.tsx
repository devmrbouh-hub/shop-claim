import { cn } from "@/lib/utils";

type Props = {
  variant?: "icon" | "header" | "auth";
  className?: string;
  subtitle?: string;
};

export default function BrandLogo({ variant = "header", className, subtitle }: Props) {
  const icon = (
    <img
      src="/logo-shop-claim-icon.png"
      alt=""
      width={32}
      height={32}
      className={cn("shrink-0 rounded-lg", variant === "auth" ? "size-12" : "size-8")}
    />
  );

  if (variant === "icon") {
    return <span className={cn("inline-flex", className)}>{icon}</span>;
  }

  const defaultSubtitle =
    subtitle ??
    (variant === "auth"
      ? "Автовыдача покупок wargm для DayZ"
      : "ShopClaim — автовыдача wargm для DayZ");

  return (
    <div className={cn("flex items-center gap-3", variant === "auth" && "flex-col text-center gap-2", className)}>
      {icon}
      <div className={variant === "auth" ? "space-y-1" : undefined}>
        <span className={cn("block font-bold tracking-tight", variant === "auth" ? "text-2xl" : "text-base")}>
          ShopClaim
        </span>
        <span className="block text-xs font-normal text-muted-foreground">{defaultSubtitle}</span>
      </div>
    </div>
  );
}
