import { portalHomeUrl } from "@/lib/siteUrls";

export default function AuthSiteLink() {
  return (
    <p className="text-sm text-muted-foreground mt-4 text-center">
      <a href={portalHomeUrl()} className="text-primary hover:underline">
        На сайт
      </a>
    </p>
  );
}
