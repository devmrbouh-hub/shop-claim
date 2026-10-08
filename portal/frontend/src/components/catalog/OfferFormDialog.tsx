import { FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";
import CatalogItemsField from "@/components/catalog/CatalogItemsField";
import {
  buildOfferPayload,
  classNameError,
  validateOfferForm,
} from "@/components/catalog/catalogValidation";
import type { CatalogOffer } from "@/types/catalog";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export type OfferFormState = {
  offerId: string;
  offer: CatalogOffer;
};

type Props = {
  open: boolean;
  editingId: string | null;
  form: OfferFormState | null;
  busy: boolean;
  onOpenChange: (open: boolean) => void;
  onFormChange: (form: OfferFormState) => void;
  onSave: (offerId: string, body: CatalogOffer) => Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
};

export default function OfferFormDialog({
  open,
  editingId,
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
  }, [open, editingId, form?.offerId, onDirtyChange]);

  const patchForm = (next: OfferFormState) => {
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
    const oid = form.offerId.trim();
    if (!oid || !/^\d+$/.test(oid)) {
      toast.error("offer_id должен быть числом wargm");
      return;
    }
    const err = validateOfferForm(form.offer);
    if (err) {
      toast.error(err);
      return;
    }
    const body = buildOfferPayload(form.offer);
    await onSave(oid, body);
    setDirty(false);
    onDirtyChange?.(false);
  };

  if (!form) return null;

  const containerErr = form.offer.type === "container" ? classNameError(form.offer.container || "") : null;
  const vehicleErr =
    form.offer.type === "vehicle" ? classNameError(form.offer.class || "") : null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editingId ? `Редактирование ${editingId}` : "Новый offer"}</DialogTitle>
          <DialogDescription>
            Изменения попадут в черновик. Игроки увидят их после «Опубликовать».
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-4">
          {!editingId && (
            <div className="space-y-2">
              <Label htmlFor="offer_id">offer_id (wargm)</Label>
              <Input
                id="offer_id"
                autoFocus
                value={form.offerId}
                onChange={(e) => patchForm({ ...form, offerId: e.target.value })}
                required
                pattern="\d+"
              />
            </div>
          )}
          <div className="space-y-2">
            <Label>Тип</Label>
            <Select
              value={form.offer.type}
              onValueChange={(value) =>
                patchForm({
                  ...form,
                  offer: {
                    ...form.offer,
                    type: value as "container" | "vehicle",
                  },
                })
              }
            >
              <SelectTrigger className="w-full max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="container">container (ящик)</SelectItem>
                <SelectItem value="vehicle">vehicle (техника)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="offer_name">Название в игровом меню</Label>
            <Input
              id="offer_name"
              autoFocus={!!editingId}
              value={form.offer.name}
              onChange={(e) =>
                patchForm({ ...form, offer: { ...form.offer, name: e.target.value } })
              }
              required
            />
          </div>
          {form.offer.type === "container" ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="container">Контейнер (ClassName)</Label>
                <Input
                  id="container"
                  value={form.offer.container || "SeaChest"}
                  onChange={(e) =>
                    patchForm({
                      ...form,
                      offer: { ...form.offer, container: e.target.value },
                    })
                  }
                  className={cn(containerErr && "border-destructive")}
                />
              </div>
              <CatalogItemsField
                items={form.offer.items || [{ ...EMPTY_ITEM }]}
                onChange={(items) =>
                  patchForm({ ...form, offer: { ...form.offer, items } })
                }
              />
            </>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="vehicle_class">ClassName техники</Label>
                <Input
                  id="vehicle_class"
                  value={form.offer.class || ""}
                  onChange={(e) =>
                    patchForm({
                      ...form,
                      offer: { ...form.offer, class: e.target.value },
                    })
                  }
                  required
                  className={cn(vehicleErr && "border-destructive")}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="distance_m">distance_m</Label>
                  <Input
                    id="distance_m"
                    type="number"
                    value={form.offer.spawn?.distance_m ?? 6}
                    onChange={(e) =>
                      patchForm({
                        ...form,
                        offer: {
                          ...form.offer,
                          spawn: {
                            ...form.offer.spawn,
                            distance_m: Number(e.target.value),
                          },
                        },
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max_slope_deg">max_slope_deg</Label>
                  <Input
                    id="max_slope_deg"
                    type="number"
                    value={form.offer.spawn?.max_slope_deg ?? 15}
                    onChange={(e) =>
                      patchForm({
                        ...form,
                        offer: {
                          ...form.offer,
                          spawn: {
                            ...form.offer.spawn,
                            max_slope_deg: Number(e.target.value),
                          },
                        },
                      })
                    }
                  />
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Комплектация (spawn_attachments, cargo) — в vehicle profiles ниже.
              </p>
            </>
          )}
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="secondary" onClick={requestClose}>
              Отмена
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Сохранение…" : "Сохранить в черновик"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
