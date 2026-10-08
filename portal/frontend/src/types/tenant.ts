export type Subscription = {
  tenant_id: string;
  enabled: boolean;
  subscription_until: string;
  active: boolean;
  deploy_status: string | null;
  bridge_url: string;
  max_servers: number;
  server_count: number;
  wargm_configured: boolean;
  plan: string;
  days_remaining: number;
  price_per_server_rub: number;
  billing_enabled: boolean;
  checkout_available: boolean;
  monthly_fee_rub: number;
  tier: string;
  network3_rub: number;
  unlimited_rub: number;
  next_add_target_max: number | null;
  next_add_monthly_fee_rub: number | null;
};

export type GameServer = {
  server_id: string;
  shop_server_id: number;
  api_token_masked: string;
  enabled: boolean;
};

export type CatalogMeta = {
  has_unpublished_changes: boolean;
  catalog_published_at: string | null;
  offers_path: string;
  vehicle_profiles_path: string;
  published_offer_count: number;
  merged_offer_count: number;
};
