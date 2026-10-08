import { Link } from "react-router-dom";
import PageHeader from "@/components/PageHeader";
import ConfigInstallHint from "@/components/ConfigInstallHint";
import ModDistributionCard from "@/components/ModDistributionCard";
import SetupStepper from "@/components/SetupStepper";
import { useTenant } from "@/context/TenantContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function TenantSetupPage() {
  const { subscription: sub, catalogMeta } = useTenant();

  return (
    <div className="space-y-6">
      <PageHeader title="Установка mod" description="Чеклист подключения DayZ-инстанса к ShopClaim" />

      <SetupStepper sub={sub} meta={catalogMeta} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Моды и дистрибуция</CardTitle>
          <CardDescription>Скачайте server mod, GUI и шаблон theme; установите на game VDS и у игроков</CardDescription>
        </CardHeader>
        <CardContent>
          <ModDistributionCard />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">config.json</CardTitle>
          <CardDescription>
            Скачайте в разделе{" "}
            <Link to="/app/servers" className="text-primary hover:underline">
              Серверы
            </Link>{" "}
            — по одному файлу на каждый DayZ-инстанс
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConfigInstallHint variant="full" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Полная инструкция</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Подробный чеклист установки — в документации subscriber-onboarding (у провайдера / в репозитории
            ShopClaim).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
