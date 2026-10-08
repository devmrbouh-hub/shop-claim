import { Outlet } from "react-router-dom";
import BrandLogo from "@/components/BrandLogo";
import AuthSiteLink from "@/components/AuthSiteLink";
import { portalHomeUrl } from "@/lib/siteUrls";

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-gradient-mesh flex flex-col items-center justify-center p-4">
      <a href={portalHomeUrl()} className="text-foreground no-underline hover:text-foreground mb-8">
        <BrandLogo variant="auth" subtitle="ShopClaim · автовыдача wargm для DayZ" />
      </a>
      <Outlet />
      <AuthSiteLink />
    </div>
  );
}
