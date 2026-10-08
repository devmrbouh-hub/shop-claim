export type CatalogItem = {
  class: string;
  qty: number;
  attachments?: string[];
};

export type CatalogOffer = {
  type: "container" | "vehicle";
  name: string;
  container?: string;
  items?: CatalogItem[];
  class?: string;
  spawn?: Record<string, number>;
  shop_server_ids?: number[];
};

export type VehicleProfile = {
  spawn_attachments?: string[];
  cargo_items?: CatalogItem[];
  fluids?: { fuel?: number; coolant?: number };
};

export type CatalogData = {
  offers: Record<string, CatalogOffer>;
  vehicle_profiles: Record<string, VehicleProfile>;
  has_unpublished_changes: boolean;
  catalog_published_at: string | null;
};

export type SpawnAttachmentRow = {
  class: string;
  qty: number;
};

export const EMPTY_ITEM: CatalogItem = { class: "", qty: 1, attachments: [] };

export const MAX_SPAWN_EXPANDED = 30;
export const MAX_ATTACHMENTS = 20;
export const MAX_CARGO_ITEMS = 30;
export const MAX_OFFER_ITEMS = 50;
