import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api, formatApiError } from "@/api/client";
import OfferFormDialog, { type OfferFormState } from "@/components/catalog/OfferFormDialog";
import { groupSpawnAttachments } from "@/components/catalog/spawnAttachmentUtils";
import VehicleProfileDialog, {
  emptyProfileFormState,
  profileToFormState,
  type ProfileFormState,
} from "@/components/catalog/VehicleProfileDialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  CatalogData,
  CatalogItem,
  CatalogOffer,
  VehicleProfile,
} from "@/types/catalog";
import { EMPTY_ITEM } from "@/types/catalog";
import { cn } from "@/lib/utils";

export type { CatalogItem, CatalogOffer, VehicleProfile, CatalogData };

type CatalogApi = {
  get: () => Promise<CatalogData>;
  putOffer: (offerId: string, body: CatalogOffer) => Promise<CatalogData>;
  deleteOffer: (offerId: string) => Promise<CatalogData>;
  publish: (expectedPublishedAt?: string | null, currentPassword?: string) => Promise<unknown>;
  discard: () => Promise<CatalogData>;
  importWargm: (offerIds: string[], currentPassword?: string) => Promise<ImportResult>;
  previewWargm: (offerId: string) => Promise<PreviewResult>;
  putVehicleProfile: (className: string, body: VehicleProfile) => Promise<CatalogData>;
};

export type ImportResult = {
  imported: string[];
  skipped: string[];
  errors: { offer_id: string; error: string }[];
  warnings: { offer_id: string; warning: string }[];
};

type PreviewResult = {
  offer_id: string;
  wargm: Record<string, unknown>;
  draft: CatalogOffer;
  warnings: string[];
};

type Props = {
  title: string;
  catalogApi: CatalogApi;
  onPublished?: () => void;
  requireStepUp?: boolean;
};

function confirmDiscardDirty(dirty: boolean): boolean {
  if (!dirty) return true;
  return window.confirm("Закрыть без сохранения? Несохранённые изменения будут потеряны.");
}

function profileSummary(prof: VehicleProfile): string {
  const flat = prof.spawn_attachments || [];
  const grouped = groupSpawnAttachments(flat);
  const parts = flat.length;
  const types = grouped.length;
  const cargo = (prof.cargo_items || []).length;
  if (!parts && !cargo) return "пустой профиль";
  const bits: string[] = [];
  if (parts) bits.push(`${parts} част${parts === 1 ? "ь" : parts < 5 ? "и" : "ей"} (${types} тип.)`);
  if (cargo) bits.push(`${cargo} cargo`);
  return bits.join(" · ");
}

export default function CatalogEditor({ title, catalogApi, onPublished, requireStepUp }: Props) {
  const [catalog, setCatalog] = useState<CatalogData | null>(null);
  const [busy, setBusy] = useState(false);
  const [stepUpPassword, setStepUpPassword] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<OfferFormState | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const offerDirtyRef = useRef(false);

  const [profileForm, setProfileForm] = useState<ProfileFormState | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileDirtyRef = useRef(false);

  const [showImport, setShowImport] = useState(false);
  const [importText, setImportText] = useState("");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await catalogApi.get();
      setCatalog(data);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  }, [catalogApi]);

  useEffect(() => {
    reload();
  }, [reload]);

  const openOfferForm = (next: OfferFormState, editId: string | null) => {
    if (formOpen && offerDirtyRef.current && !confirmDiscardDirty(true)) return;
    setEditingId(editId);
    setForm(next);
    setFormOpen(true);
    offerDirtyRef.current = false;
  };

  const startNew = () => {
    if (showImport) setShowImport(false);
    openOfferForm(
      {
        offerId: "",
        offer: {
          type: "container",
          name: "",
          container: "SeaChest",
          items: [{ ...EMPTY_ITEM }],
        },
      },
      null,
    );
  };

  const startEdit = (offerId: string, offer: CatalogOffer) => {
    if (showImport) setShowImport(false);
    openOfferForm(
      {
        offerId,
        offer: {
          ...offer,
          items: offer.items?.length
            ? offer.items.map((i) => ({
                class: i.class,
                qty: i.qty,
                attachments: i.attachments ? [...i.attachments] : [],
              }))
            : [{ ...EMPTY_ITEM }],
        },
      },
      offerId,
    );
  };

  const saveOffer = async (offerId: string, body: CatalogOffer) => {
    setBusy(true);
    try {
      const data = await catalogApi.putOffer(offerId, body);
      setCatalog(data);
      setFormOpen(false);
      setForm(null);
      setEditingId(null);
      offerDirtyRef.current = false;
      toast.success("Черновик сохранён");
    } catch (err) {
      toast.error(formatApiError(err));
      throw err;
    } finally {
      setBusy(false);
    }
  };

  const removeOffer = async (offerId: string) => {
    if (!confirm(`Удалить offer ${offerId} из каталога? (применится после публикации)`)) return;
    setBusy(true);
    try {
      const data = await catalogApi.deleteOffer(offerId);
      setCatalog(data);
      toast.success("Offer удалён из черновика");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (requireStepUp && !stepUpPassword) {
      toast.error("Введите текущий пароль для публикации");
      return;
    }
    setBusy(true);
    try {
      await catalogApi.publish(
        catalog?.catalog_published_at,
        requireStepUp ? stepUpPassword : undefined,
      );
      await reload();
      onPublished?.();
      toast.success("Каталог опубликован");
      setStepUpPassword("");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const discard = async () => {
    if (!confirm("Отменить все неопубликованные изменения?")) return;
    setBusy(true);
    try {
      const data = await catalogApi.discard();
      setCatalog(data);
      toast.success("Черновик сброшен");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const runImport = async (e: FormEvent) => {
    e.preventDefault();
    const ids = importText
      .split(/[\s,;]+/)
      .map((s) => s.trim())
      .filter((s) => /^\d+$/.test(s));
    if (!ids.length) {
      toast.error("Введите offer_id через запятую или с новой строки");
      return;
    }
    if (requireStepUp && !stepUpPassword) {
      toast.error("Введите текущий пароль для импорта");
      return;
    }
    setBusy(true);
    try {
      const result = await catalogApi.importWargm(
        ids,
        requireStepUp ? stepUpPassword : undefined,
      );
      setImportResult(result);
      await reload();
      if (result.imported.length) {
        toast.success(`Импортировано: ${result.imported.length}`);
      }
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const openProfile = (state: ProfileFormState) => {
    if (profileOpen && profileDirtyRef.current && !confirmDiscardDirty(true)) return;
    setProfileForm(state);
    setProfileOpen(true);
    profileDirtyRef.current = false;
  };

  const startEditProfile = (className: string, prof: VehicleProfile) => {
    openProfile(profileToFormState(className, prof, false));
  };

  const startNewProfile = () => {
    openProfile(emptyProfileFormState());
  };

  const saveProfile = async (className: string, body: VehicleProfile) => {
    setBusy(true);
    try {
      const data = await catalogApi.putVehicleProfile(className, body);
      setCatalog(data);
      setProfileOpen(false);
      setProfileForm(null);
      profileDirtyRef.current = false;
      toast.success("Профиль техники сохранён в черновик");
    } catch (err) {
      toast.error(formatApiError(err));
      throw err;
    } finally {
      setBusy(false);
    }
  };

  const offers = catalog ? Object.entries(catalog.offers).sort(([a], [b]) => Number(a) - Number(b)) : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>

      {catalog?.has_unpublished_changes && (
        <Alert>
          <AlertTitle>Есть неопубликованные изменения</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>Игроки видят последний опубликованный каталог до нажатия «Опубликовать».</p>
            {requireStepUp && (
              <div className="space-y-2 max-w-sm">
                <label htmlFor="publish_password" className="text-sm font-medium">
                  Текущий пароль
                </label>
                <input
                  id="publish_password"
                  type="password"
                  autoComplete="current-password"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                  value={stepUpPassword}
                  onChange={(e) => setStepUpPassword(e.target.value)}
                />
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <Button type="button" disabled={busy} onClick={publish}>
                Опубликовать
              </Button>
              <Button type="button" variant="secondary" disabled={busy} onClick={discard}>
                Отменить изменения
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Товары ({offers.length})</CardTitle>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                if (formOpen && offerDirtyRef.current && !confirmDiscardDirty(true)) return;
                setFormOpen(false);
                setShowImport(true);
              }}
            >
              Импорт wargm
            </Button>
            <Button type="button" size="sm" onClick={startNew}>
              Добавить offer
            </Button>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>offer_id</TableHead>
                <TableHead>Название</TableHead>
                <TableHead>Тип</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {offers.map(([id, offer]) => (
                <TableRow
                  key={id}
                  className={cn(editingId === id && formOpen && "bg-muted/50 ring-1 ring-primary/20")}
                >
                  <TableCell className="font-mono">{id}</TableCell>
                  <TableCell>{offer.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{offer.type}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button type="button" variant="secondary" size="sm" onClick={() => startEdit(id, offer)}>
                        Изменить
                      </Button>
                      <Button type="button" variant="outline" size="sm" onClick={() => removeOffer(id)}>
                        Удалить
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!offers.length && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    Каталог пуст. Добавьте offer или импортируйте из wargm.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Vehicle profiles</CardTitle>
          <Button type="button" variant="secondary" size="sm" onClick={startNewProfile}>
            Новый профиль
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Профили комплектации для vehicle offers (черновик до публикации).
          </p>
          {catalog &&
            Object.entries(catalog.vehicle_profiles).map(([cls, prof]) => (
              <div
                key={cls}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
              >
                <div className="text-sm">
                  <strong>{cls}</strong>
                  <span className="text-muted-foreground"> — {profileSummary(prof)}</span>
                </div>
                <Button type="button" variant="secondary" size="sm" onClick={() => startEditProfile(cls, prof)}>
                  Изменить
                </Button>
              </div>
            ))}
          {catalog && !Object.keys(catalog.vehicle_profiles).length && (
            <p className="text-sm text-muted-foreground">Профилей пока нет.</p>
          )}
        </CardContent>
      </Card>

      <OfferFormDialog
        open={formOpen}
        editingId={editingId}
        form={form}
        busy={busy}
        onOpenChange={(open) => {
          if (!open) {
            setFormOpen(false);
            setForm(null);
            setEditingId(null);
            offerDirtyRef.current = false;
          } else {
            setFormOpen(true);
          }
        }}
        onFormChange={setForm}
        onSave={saveOffer}
        onDirtyChange={(d) => {
          offerDirtyRef.current = d;
        }}
      />

      <VehicleProfileDialog
        open={profileOpen}
        form={profileForm}
        busy={busy}
        onOpenChange={(open) => {
          if (!open) {
            setProfileOpen(false);
            setProfileForm(null);
            profileDirtyRef.current = false;
          } else {
            setProfileOpen(true);
          }
        }}
        onFormChange={setProfileForm}
        onSave={saveProfile}
        onDirtyChange={(d) => {
          profileDirtyRef.current = d;
        }}
      />

      <Dialog
        open={showImport}
        onOpenChange={(open) => {
          setShowImport(open);
          if (!open) {
            setImportResult(null);
            setImportText("");
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Импорт из wargm</DialogTitle>
            <DialogDescription>
              Вставьте offer_id из ЛК wargm (до 50 за раз). Название и предметы заполняются вручную, если offer уже
              есть.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={runImport} className="space-y-4">
            <Textarea
              rows={5}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder="5001, 5010"
            />
            {requireStepUp && (
              <div className="space-y-2">
                <label htmlFor="import_password" className="text-sm font-medium">
                  Текущий пароль
                </label>
                <input
                  id="import_password"
                  type="password"
                  autoComplete="current-password"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                  value={stepUpPassword}
                  onChange={(e) => setStepUpPassword(e.target.value)}
                />
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="secondary" onClick={() => setShowImport(false)}>
                Закрыть
              </Button>
              <Button type="submit" disabled={busy}>
                Импортировать
              </Button>
            </DialogFooter>
          </form>
          {importResult && (
            <div className="space-y-2 text-sm">
              {importResult.imported.length > 0 && (
                <p className="text-success">Импортировано: {importResult.imported.join(", ")}</p>
              )}
              {importResult.skipped.length > 0 && (
                <p>Пропущено (уже заполнены): {importResult.skipped.join(", ")}</p>
              )}
              {importResult.warnings.map((w) => (
                <p key={w.offer_id} className="text-muted-foreground">
                  {w.offer_id}: {w.warning}
                </p>
              ))}
              {importResult.errors.map((e) => (
                <p key={e.offer_id} className="text-destructive">
                  {e.offer_id}: {e.error}
                </p>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function tenantCatalogApi(): CatalogApi {
  return {
    get: () => api.tenant.catalog() as Promise<CatalogData>,
    putOffer: (id, body) => api.tenant.putCatalogOffer(id, body) as Promise<CatalogData>,
    deleteOffer: (id) => api.tenant.deleteCatalogOffer(id) as Promise<CatalogData>,
    publish: (expected, pw) => api.tenant.publishCatalog(expected, pw),
    discard: () => api.tenant.discardCatalog() as Promise<CatalogData>,
    importWargm: (ids, pw) => api.tenant.importWargm(ids, pw) as Promise<ImportResult>,
    previewWargm: (id) => api.tenant.previewWargm(id) as Promise<PreviewResult>,
    putVehicleProfile: (cls, body) => api.tenant.putVehicleProfile(cls, body) as Promise<CatalogData>,
  };
}

export function adminCatalogApi(slug: string): CatalogApi {
  return {
    get: () => api.admin.getCatalog(slug) as Promise<CatalogData>,
    putOffer: (id, body) => api.admin.putCatalogOffer(slug, id, body) as Promise<CatalogData>,
    deleteOffer: (id) => api.admin.deleteCatalogOffer(slug, id) as Promise<CatalogData>,
    publish: (expected) => api.admin.publishCatalog(slug, expected),
    discard: () => api.admin.discardCatalog(slug) as Promise<CatalogData>,
    importWargm: (ids) => api.admin.importWargm(slug, ids) as Promise<ImportResult>,
    previewWargm: (id) => api.tenant.previewWargm(id) as Promise<PreviewResult>,
    putVehicleProfile: (cls, body) => api.admin.putVehicleProfile(slug, cls, body) as Promise<CatalogData>,
  };
}
