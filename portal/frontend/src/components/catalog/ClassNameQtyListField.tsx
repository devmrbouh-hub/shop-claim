import { Plus, Trash2 } from "lucide-react";
import {
  expandedSpawnCount,
  spawnOverLimit,
} from "@/components/catalog/spawnAttachmentUtils";
import { classNameError, CLASSNAME_HINT } from "@/components/catalog/catalogValidation";
import type { SpawnAttachmentRow } from "@/types/catalog";
import { MAX_SPAWN_EXPANDED } from "@/types/catalog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type Props = {
  rows: SpawnAttachmentRow[];
  onChange: (rows: SpawnAttachmentRow[]) => void;
  maxExpanded?: number;
};

export default function ClassNameQtyListField({
  rows,
  onChange,
  maxExpanded = MAX_SPAWN_EXPANDED,
}: Props) {
  const displayRows = rows.length ? rows : [{ class: "", qty: 1 }];
  const expanded = expandedSpawnCount(displayRows);
  const overLimit = spawnOverLimit(displayRows, maxExpanded);

  const updateRow = (idx: number, patch: Partial<SpawnAttachmentRow>) => {
    const copy = displayRows.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    onChange(copy);
  };

  const removeRow = (idx: number) => {
    const copy = displayRows.filter((_, i) => i !== idx);
    onChange(copy.length ? copy : [{ class: "", qty: 1 }]);
  };

  const addRow = () => {
    onChange([...displayRows, { class: "", qty: 1 }]);
  };

  return (
    <div className="space-y-3">
      <Label>Части машины (spawn_attachments)</Label>
      <div className="space-y-2">
        {displayRows.map((row, idx) => {
          const err = classNameError(row.class);
          return (
            <div key={idx} className="flex flex-wrap gap-2 sm:flex-nowrap">
              <Input
                placeholder="ClassName"
                value={row.class}
                onChange={(e) => updateRow(idx, { class: e.target.value })}
                className={cn("min-w-0 flex-1", err && "border-destructive")}
              />
              <Input
                type="number"
                min={1}
                max={maxExpanded}
                className="w-20 shrink-0"
                value={row.qty}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  updateRow(idx, { qty: Number.isFinite(n) && n >= 1 ? Math.floor(n) : 1 });
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="shrink-0"
                onClick={() => removeRow(idx)}
                disabled={displayRows.length === 1 && !row.class.trim()}
                aria-label="Удалить"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={addRow}>
          <Plus className="size-4" />
          часть
        </Button>
        <span className="text-xs text-muted-foreground">
          В YAML: {expanded} / {maxExpanded}
        </span>
      </div>
      {overLimit && (
        <Alert variant="destructive">
          <AlertDescription>
            Слишком много частей ({expanded}). Максимум {maxExpanded} записей в YAML.
          </AlertDescription>
        </Alert>
      )}
      <p className="text-xs text-muted-foreground">{CLASSNAME_HINT}</p>
    </div>
  );
}

export { expandedSpawnCount, spawnOverLimit };
