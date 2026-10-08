import { useEffect, useState } from "react";
import { ExternalLink, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type ModArtifact, type ModsManifest } from "@/api/client";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

type Props = {
  compact?: boolean;
};

export default function ModDistributionCard({ compact }: Props) {
  const [mods, setMods] = useState<ModsManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .mods()
      .then(setMods)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return <p className="text-sm text-muted-foreground">Не удалось загрузить список модов: {error}</p>;
  }

  if (!mods) {
    return <p className="text-sm text-muted-foreground">Загрузка модов…</p>;
  }

  return (
    <div className="space-y-3">
      {!compact && (
        <p className="text-sm text-muted-foreground">
          Версия пакета: <strong className="text-foreground">{mods.version}</strong>
          {mods.updated_at ? ` · обновлено ${mods.updated_at}` : null}
        </p>
      )}
      <ul className="space-y-3">
        {mods.artifacts.map((artifact) => (
          <ModArtifactRow key={artifact.id} artifact={artifact} />
        ))}
      </ul>
    </div>
  );
}

function ModArtifactRow({ artifact }: { artifact: ModArtifact }) {
  const downloadHref = artifact.download_available
    ? `${API_BASE}${artifact.download_url}`
    : null;

  return (
    <li className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="font-medium">
          {artifact.name}
          {artifact.required ? (
            <span className="ml-2 text-xs text-muted-foreground">обязательно</span>
          ) : (
            <span className="ml-2 text-xs text-muted-foreground">опционально</span>
          )}
        </p>
        <p className="text-sm text-muted-foreground">{artifact.description}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {artifact.workshop_url ? (
          <Button variant="outline" size="sm" asChild>
            <a href={artifact.workshop_url} target="_blank" rel="noreferrer">
              <ExternalLink className="mr-1 h-4 w-4" />
              Workshop
            </a>
          </Button>
        ) : null}
        {downloadHref ? (
          <Button variant="secondary" size="sm" asChild>
            <a href={downloadHref} download={artifact.filename ?? true}>
              <Download className="mr-1 h-4 w-4" />
              Скачать
            </a>
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground self-center">Сборка недоступна — см. провайдера</span>
        )}
      </div>
    </li>
  );
}
