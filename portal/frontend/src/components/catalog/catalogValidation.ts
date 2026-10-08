import type { CatalogItem, CatalogOffer } from "@/types/catalog";
import { MAX_ATTACHMENTS, MAX_CARGO_ITEMS, MAX_OFFER_ITEMS } from "@/types/catalog";

/** Mirror of portal/backend shop_claim_portal/services/catalog_service.py */
export const CLASSNAME_RE = /^[A-Za-z0-9_]+$/;
export const MAX_CLASSNAME_LEN = 128;

export const CLASSNAME_HINT =
  "Латиница, цифры и _ (до 128 символов). Убедитесь, что ClassName есть в mod list сервера.";

export function isValidClassName(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > MAX_CLASSNAME_LEN) return false;
  return CLASSNAME_RE.test(trimmed);
}

export function classNameError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (trimmed.length > MAX_CLASSNAME_LEN) return "Слишком длинный ClassName (макс. 128)";
  if (!CLASSNAME_RE.test(trimmed)) return CLASSNAME_HINT;
  return null;
}

export function validateClassNames(names: string[], label: string): string | null {
  for (const raw of names) {
    const trimmed = raw.trim();
    if (!trimmed) continue;
    if (!isValidClassName(trimmed)) {
      return `${label}: ${CLASSNAME_HINT}`;
    }
  }
  return null;
}

export function buildCargoItemsPayload(items: CatalogItem[]): CatalogItem[] {
  return items
    .filter((i) => i.class.trim())
    .map((i) => {
      const attachments = (i.attachments || []).map((a) => a.trim()).filter(Boolean);
      const out: CatalogItem = {
        class: i.class.trim(),
        qty: Math.max(1, Number(i.qty) || 1),
      };
      if (attachments.length) out.attachments = attachments;
      return out;
    });
}

export function parseCargoItemsFromApi(raw: unknown): CatalogItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((x): x is Record<string, unknown> => typeof x === "object" && x !== null)
    .map((row) => ({
      class: String(row.class ?? ""),
      qty: Math.max(1, Number(row.qty) || 1),
      attachments: Array.isArray(row.attachments)
        ? row.attachments.map((a) => String(a))
        : [],
    }));
}

export function validateOfferForm(offer: CatalogOffer): string | null {
  if (!offer.name.trim()) return "Укажите название для игрового меню";

  if (offer.type === "vehicle") {
    const vclass = (offer.class || "").trim();
    if (!vclass) return "Укажите ClassName техники";
    if (!isValidClassName(vclass)) return `ClassName техники: ${CLASSNAME_HINT}`;
    return null;
  }

  const container = (offer.container || "SeaChest").trim();
  if (!isValidClassName(container)) return `Контейнер: ${CLASSNAME_HINT}`;

  const items = buildCargoItemsPayload(offer.items || []);
  if (!items.length) return "Добавьте хотя бы один предмет в ящик";
  if (items.length > MAX_OFFER_ITEMS) return `Максимум ${MAX_OFFER_ITEMS} предметов`;

  for (const item of items) {
    if (!isValidClassName(item.class)) return `Предмет «${item.class}»: ${CLASSNAME_HINT}`;
    const attachments = item.attachments || [];
    if (attachments.length > MAX_ATTACHMENTS) {
      return `Максимум ${MAX_ATTACHMENTS} attachments на предмет`;
    }
    const attErr = validateClassNames(attachments, "Attachment");
    if (attErr) return attErr;
  }
  return null;
}

export function validateProfilePayload(
  className: string,
  spawnFlat: string[],
  cargoItems: CatalogItem[],
): string | null {
  const cls = className.trim();
  if (!cls) return "Укажите ClassName техники";
  if (!isValidClassName(cls)) return `ClassName техники: ${CLASSNAME_HINT}`;

  const spawnErr = validateClassNames(spawnFlat, "Часть машины");
  if (spawnErr) return spawnErr;

  const cargo = buildCargoItemsPayload(cargoItems);
  if (cargo.length > MAX_CARGO_ITEMS) return `Максимум ${MAX_CARGO_ITEMS} предметов в багажнике`;

  for (const item of cargo) {
    if (!isValidClassName(item.class)) return `Cargo «${item.class}»: ${CLASSNAME_HINT}`;
    const attachments = item.attachments || [];
    if (attachments.length > MAX_ATTACHMENTS) {
      return `Максимум ${MAX_ATTACHMENTS} attachments на предмет`;
    }
    const attErr = validateClassNames(attachments, "Attachment");
    if (attErr) return attErr;
  }
  return null;
}

export function buildOfferPayload(offer: CatalogOffer): CatalogOffer {
  const base = {
    type: offer.type,
    name: offer.name.trim(),
    ...(offer.shop_server_ids?.length ? { shop_server_ids: offer.shop_server_ids } : {}),
  };
  if (offer.type === "vehicle") {
    return {
      ...base,
      class: offer.class?.trim(),
      spawn: offer.spawn,
    };
  }
  const items = buildCargoItemsPayload(offer.items || []).map((i) => ({
    ...i,
    ...(i.attachments?.length ? { attachments: i.attachments.filter(Boolean) } : {}),
  }));
  return {
    ...base,
    container: (offer.container || "SeaChest").trim(),
    items,
  };
}
