import { Progress } from "@/components/ui/progress";

type Props = { count: number; max: number; label?: string };

export default function QuotaMeter({ count, max, label = "Серверы" }: Props) {
  const pct = max > 0 ? Math.min(100, (count / max) * 100) : 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {count} / {max}
        </span>
      </div>
      <Progress value={pct} aria-label={`${label}: ${count} из ${max}`} />
    </div>
  );
}
