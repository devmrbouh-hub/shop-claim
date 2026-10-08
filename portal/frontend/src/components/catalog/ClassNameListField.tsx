import { Plus, Trash2 } from "lucide-react";
import { classNameError, CLASSNAME_HINT } from "@/components/catalog/catalogValidation";
import { MAX_ATTACHMENTS } from "@/types/catalog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type Props = {
  value: string[];
  onChange: (value: string[]) => void;
  label?: string;
  maxItems?: number;
  placeholder?: string;
  compact?: boolean;
};

export default function ClassNameListField({
  value,
  onChange,
  label,
  maxItems = MAX_ATTACHMENTS,
  placeholder = "ClassName",
  compact = false,
}: Props) {
  const rows = value.length ? value : [""];

  const updateRow = (idx: number, next: string) => {
    const copy = [...rows];
    copy[idx] = next;
    onChange(copy);
  };

  const removeRow = (idx: number) => {
    const copy = rows.filter((_, i) => i !== idx);
    onChange(copy.length ? copy : [""]);
  };

  const addRow = () => {
    if (rows.filter((r) => r.trim()).length >= maxItems) return;
    onChange([...rows, ""]);
  };

  const filledCount = rows.filter((r) => r.trim()).length;

  return (
    <div className={cn("space-y-2", compact && "text-sm")}>
      {label && <Label className="text-sm font-normal">{label}</Label>}
      <div className="space-y-2">
        {rows.map((row, idx) => {
          const err = classNameError(row);
          return (
            <div key={idx} className="flex gap-2">
              <Input
                placeholder={placeholder}
                value={row}
                onChange={(e) => updateRow(idx, e.target.value)}
                className={cn(err && "border-destructive")}
                aria-invalid={!!err}
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="shrink-0"
                onClick={() => removeRow(idx)}
                disabled={rows.length === 1 && !row.trim()}
                aria-label="Удалить"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          );
        })}
      </div>
      {filledCount < maxItems && (
        <Button type="button" variant="secondary" size="sm" onClick={addRow}>
          <Plus className="size-4" />
          добавить
        </Button>
      )}
      <p className="text-xs text-muted-foreground">
        {filledCount} / {maxItems}. {CLASSNAME_HINT}
      </p>
    </div>
  );
}
