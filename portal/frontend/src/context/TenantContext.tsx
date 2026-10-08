import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { CatalogMeta, GameServer, Subscription } from "../types/tenant";

type TenantContextValue = {
  subscription: Subscription | null;
  servers: GameServer[];
  catalogMeta: CatalogMeta | null;
  isLoading: boolean;
  reload: () => Promise<void>;
};

const TenantContext = createContext<TenantContextValue | null>(null);

export function TenantProvider({ children }: { children: ReactNode }) {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [servers, setServers] = useState<GameServer[]>([]);
  const [catalogMeta, setCatalogMeta] = useState<CatalogMeta | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const reload = useCallback(async () => {
    setIsLoading(true);
    try {
      const [sub, srv, meta] = await Promise.all([
        api.tenant.subscription(),
        api.tenant.servers(),
        api.tenant.catalogMeta(),
      ]);
      setSubscription(sub as Subscription);
      setServers(srv as GameServer[]);
      setCatalogMeta(meta as CatalogMeta);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const value = useMemo(
    () => ({ subscription, servers, catalogMeta, isLoading, reload }),
    [subscription, servers, catalogMeta, isLoading, reload],
  );

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenant() {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error("useTenant requires TenantProvider");
  return ctx;
}
