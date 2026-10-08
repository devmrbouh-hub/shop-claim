import { useEffect } from "react";
import { landingUrl } from "@/lib/siteUrls";

type Props = { path?: string };

export default function RedirectToLanding({ path = "/" }: Props) {
  useEffect(() => {
    window.location.replace(landingUrl(path));
  }, [path]);

  return (
    <p className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">
      Перенаправление…
    </p>
  );
}
