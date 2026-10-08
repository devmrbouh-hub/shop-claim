import { FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";
import CatalogItemsField, { MAX_CARGO_ITEMS } from "@/components/catalog/CatalogItemsField";
import ClassNameQtyListField, {
  spawnOverLimit,
} from "@/components/catalog/ClassNameQtyListField";
import {
  buildCargoItemsPayload,
  classNameError,
  parseCargoItemsFromApi,
  validateProfilePayload,
} from "@/components/catalog/catalogValidation";
import {
  expandSpawnAttachments,
  groupSpawnAttachments,
} from "@/components/catalog/spawnAttachmentUtils";
import type { CatalogItem, SpawnAttachmentRow, VehicleProfile } from "@/types/catalog";
import { EMPTY_ITEM } from "@/types/catalog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type ProfileFormState = {
  className: string;
  isNew: boolean;
  spawnRows: SpawnAttachmentRow[];
  cargoItems: CatalogItem[];
  fuel: number;
  coolant: number;
};

type Props = {
  open: boolean;
  form: ProfileFormState | null;
  busy: boolean;
  onOpenChange: (open: boolean) => void;
  onFormChange: (form: ProfileFormState) => void;
  onSave: (className: string, body: VehicleProfile) => Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
};

export function profileToFormState(className: string, prof: VehicleProfile, isNew: boolean): ProfileFormState {
  const cargoRaw = prof.cargo_items as unknown;
  const cargoItems = parseCargoItemsFromApi(cargoRaw);
  const fluids = prof.fluids || {};
  return {
    className,
    isNew,
    spawnRows: groupSpawnAttachments(prof.spawn_attachments || []),
    cargoItems: cargoItems.length ? cargoItems : [],
    fuel: typeof fluids.fuel === "number" ? fluids.fuel : 1,
    coolant: typeof fluids.coolant === "number" ? fluids.coolant : 1,
  };
}

export function emptyProfileFormState(): ProfileFormState {
  return {
    className: "",
    isNew: true,
    spawnRows: [{ class: "", qty: 1 }],
    cargoItems: [],
    fuel: 1,
    coolant: 1,
  };
}

export default function VehicleProfileDialog({
  open,
  form,
  busy,
  onOpenChange,
  onFormChange,
  onSave,
  onDirtyChange,
}: Props) {
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (open && form) {
      setDirty(false);
      onDirtyChange?.(false);
    }
  }, [open, form?.className, form?.isNew]);

  const patchForm = (next: ProfileFormState) => {
    onFormChange(next);
    setDirty(true);
    onDirtyChange?.(true);
  };

  const requestClose = () => {
    if (dirty) {
      if (!window.confirm("Закрыть без сохранения? Несохранённые изменения будут потеряны.")) {
        return;
      }
    }
    onOpenChange(false);
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      requestClose();
      return;
    }
    onOpenChange(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;

    const spawnFlat = expandSpawnAttachments(form.spawnRows);
    if (spawnOverLimit(form.spawnRows)) {
      toast.error("Слишком много частей (макс. 30 в YAML)");
      return;
    }

    const cargoItems = buildCargoItemsPayload(form.cargoItems);
    const err = validateProfilePayload(form.className, spawnFlat, cargoItems);
    if (err) {
      toast.error(err);
      return;
    }

    const fuel = Math.min(1, Math.max(0, Number(form.fuel) || 0));
    const coolant = Math.min(1, Math.max(0, Number(form.coolant) || 0));

    const body: VehicleProfile = {
      spawn_attachments: spawnFlat,
      cargo_items: cargoItems,
      fluids: { fuel, coolant },
    };

    await onSave(form.className.trim(), body);
    setDirty(false);
    onDirtyChange?.(false);
  };

  if (!form) return null;

  const classErr = form.isNew ? classNameError(form.className) : null;
  const submitBlocked = spawnOverLimit(form.spawnRows);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {form.isNew ? "Новый vehicle profile" : `Профиль: ${form.className}`}
          </DialogTitle>
          <DialogDescription>
            Комплектация техники для vehicle offers. Черновик до публикации каталога.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="profile_class">ClassName техники</Label>
            <Input
              id="profile_class"
              autoFocus={form.isNew}
              value={form.className}
              onChange={(e) => patchForm({ ...form, className: e.target.value })}
              required
              readOnly={!form.isNew}
              disabled={!form.isNew}
              className={cn(classErr && "border-destructive")}
            />
          </div>

          <ClassNameQtyListField
            rows={form.spawnRows}
            onChange={(spawnRows) => patchForm({ ...form, spawnRows })}
          />

          <CatalogItemsField
            label="Cargo в багажнике"
            maxItems={MAX_CARGO_ITEMS}
            items={form.cargoItems.length ? form.cargoItems : [{ ...EMPTY_ITEM }]}
            onChange={(cargoItems) => patchForm({ ...form, cargoItems })}
            showAttachments
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="fuel">Топливо (0–1)</Label>
              <Input
                id="fuel"
                type="number"
                min={0}
                max={1}
                step={0.1}
                value={form.fuel}
                onChange={(e) => patchForm({ ...form, fuel: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="coolant">Охлаждение (0–1)</Label>
              <Input
                id="coolant"
                type="number"
                min={0}
                max={1}
                step={0.1}
                value={form.coolant}
                onChange={(e) => patchForm({ ...form, coolant: Number(e.target.value) })}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="secondary" onClick={requestClose}>
              Отмена
            </Button>
            <Button type="submit" disabled={busy || submitBlocked}>
              {busy ? "Сохранение…" : "Сохранить профиль"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
