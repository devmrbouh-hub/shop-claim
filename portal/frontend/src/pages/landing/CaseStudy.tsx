import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export default function CaseStudy() {
  return (
    <section id="case" className="py-16 md:py-24">
      <div className="mx-auto max-w-5xl px-5">
        <Card className="border-primary/20 bg-card/80 py-6">
          <CardContent className="space-y-4">
            <Badge variant="secondary">Демо</Badge>
            <h2 className="text-2xl font-semibold tracking-tight">Self-hosted и SaaS</h2>
            <p className="text-muted-foreground leading-relaxed">
              Bridge на том же хосте, что DayZ, или удалённый multi-tenant Portal. Каталог YAML, REST для server mod,
              выдача container и vehicle в игре.
            </p>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
