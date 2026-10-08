import { Link, useParams } from "react-router-dom";
import CatalogEditor, { adminCatalogApi } from "@/pages/catalog/CatalogEditor";
import PageHeader from "@/components/PageHeader";

export default function AdminCatalogPage() {
  const { slug } = useParams<{ slug: string }>();
  if (!slug) return null;

  return (
    <div className="space-y-4">
      <nav className="text-sm text-muted-foreground">
        <Link to="/admin" className="hover:text-foreground">
          Обзор
        </Link>
        {" / "}
        <Link to={`/admin/tenants/${slug}`} className="hover:text-foreground">
          {slug}
        </Link>
        {" / "}
        <span className="text-foreground">Каталог</span>
      </nav>
      <PageHeader title={`Каталог: ${slug}`} />
      <CatalogEditor title={`Каталог tenant: ${slug}`} catalogApi={adminCatalogApi(slug)} />
    </div>
  );
}
