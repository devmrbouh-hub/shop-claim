import CatalogEditor, { tenantCatalogApi } from "@/pages/catalog/CatalogEditor";
import PageHeader from "@/components/PageHeader";
import { useTenant } from "@/context/TenantContext";
import { Card, CardContent } from "@/components/ui/card";

type Props = { tenantId: string | null };

export default function TenantCatalogPage({ tenantId }: Props) {
  const { reload } = useTenant();

  return (
    <div className="space-y-6">
      <PageHeader title="Каталог" description={`Управление офферами — ${tenantId ?? "…"}`} />
      <Card>
        <CardContent className="pt-6">
          <CatalogEditor
            title={`Каталог — ${tenantId}`}
            catalogApi={tenantCatalogApi()}
            onPublished={reload}
            requireStepUp
          />
        </CardContent>
      </Card>
    </div>
  );
}
