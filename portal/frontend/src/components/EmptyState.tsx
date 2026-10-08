import { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";

type Props = {
  title: string;
  hint?: string;
  action?: ReactNode;
  icon?: ReactNode;
};

export default function EmptyState({ title, hint, action, icon }: Props) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        {icon && <div className="mb-4 text-muted-foreground">{icon}</div>}
        <h3 className="text-lg font-medium">{title}</h3>
        {hint && <p className="text-sm text-muted-foreground mt-2 max-w-sm">{hint}</p>}
        {action && <div className="mt-4">{action}</div>}
      </CardContent>
    </Card>
  );
}
