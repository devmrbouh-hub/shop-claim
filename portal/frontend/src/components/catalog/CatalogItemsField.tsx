import { Plus, Trash2 } from "lucide-react";
import ClassNameListField from "@/components/catalog/ClassNameListField";
import { classNameError } from "@/components/catalog/catalogValidation";
import type { CatalogItem } from "@/types/catalog";
import { EMPTY_ITEM, MAX_CARGO_ITEMS, MAX_OFFER_ITEMS } from "@/types/catalog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type Props = {
  items: CatalogItem[];
  onChange: (items: CatalogItem[]) => void;
  label?: string;
  maxItems?: number;
  showAttachments?: boolean;
};

export default function CatalogItemsField({
  items,
  onChange,
  label = "Предметы",
  maxItems = MAX_OFFER_ITEMS,
  showAttachments = true,
}: Props) {
  const rows = items.length ? items : [{ ...EMPTY_ITEM }];

  const updateItem = (idx: number, patch: Partial<CatalogItem>) => {
    const copy = rows.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    onChange(copy);
  };

  const removeItem = (idx: number) => {
    const copy = rows.filter((_, i) => i !== idx);
    onChange(copy.length ? copy : [{ ...EMPTY_ITEM }]);
  };

  const addItem = () => {
    if (rows.filter((r) => r.class.trim()).length >= maxItems) return;
    onChange([...rows, { ...EMPTY_ITEM }]);
  };

  const filledCount = rows.filter((r) => r.class.trim()).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <Label>{label}</Label>
        <span className="text-xs text-muted-foreground">
          {filledCount} / {maxItems}
        </span>
      </div>
      <div className="space-y-4">
        {rows.map((item, idx) => {
          const classErr = classNameError(item.class);
          return (
            <div key={idx} className="space-y-2 rounded-lg border p-3">
              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Input
                  placeholder="ClassName"
                  value={item.class}
                  onChange={(e) => updateItem(idx, { class: e.target.value })}
                  className={cn("min-w-0 flex-1", classErr && "border-destructive")}
                />
                <Input
                  type="number"
                  min={1}
                  max={999}
                  className="w-20 shrink-0"
                  value={item.qty}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    updateItem(idx, { qty: Number.isFinite(n) && n >= 1 ? Math.floor(n) : 1 });
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="shrink-0"
                  onClick={() => removeItem(idx)}
                  disabled={rows.length === 1 && !item.class.trim()}
                  aria-label="Удалить предмет"
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
              {showAttachments && (
                <details className="text-sm">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    Вложения ({(item.attachments || []).filter(Boolean).length})
                  </summary>
                  <div className="mt-2 pl-1">
                    <ClassNameListField
                      compact
                      value={item.attachments?.length ? item.attachments : [""]}
                      onChange={(attachments) => {
                        const trimmed = attachments.map((a) => a.trim()).filter(Boolean);
                        updateItem(idx, { attachments: trimmed.length ? trimmed : [] });
                      }}
                    />
                  </div>
                </details>
              )}
            </div>
          );
        })}
      </div>
      {filledCount < maxItems && (
        <Button type="button" variant="secondary" size="sm" onClick={addItem}>
          <Plus className="size-4" />
          предмет
        </Button>
      )}
    </div>
  );
}

export { MAX_CARGO_ITEMS };
