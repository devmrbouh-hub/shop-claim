type Props = {
  /** Показать полный чеклист (страница установки) или кратко (рядом с download). */
  variant?: "compact" | "full";
};

export default function ConfigInstallHint({ variant = "compact" }: Props) {
  if (variant === "full") {
    return (
      <div className="space-y-3 text-sm">
        <p>
          Файл <strong className="font-medium">не кладут в PBO</strong> и не внутрь папки server mod — только в{" "}
          <strong className="font-medium">profiles</strong> DayZ-инстанса.
        </p>
        <p>
          Путь на game VDS (Windows):
          <br />
          <code className="mt-1 inline-block rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
            &lt;profiles этого инстанса&gt;\ShopClaim\config.json
          </code>
        </p>
        <p className="text-muted-foreground">
          Пример: <code className="rounded bg-muted px-1 py-0.5 text-xs">D:\Servers\Chernarus\profiles\ShopClaim\config.json</code>
          . Каталог <code className="rounded bg-muted px-1 py-0.5 text-xs">ShopClaim</code> создайте, если его нет.
        </p>
        <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
          <li>На каждый DayZ-инстанс — свой config (кнопка «config.json» у строки server_id).</li>
          <li>
            <code className="rounded bg-muted px-1 py-0.5 text-xs">shop_server_id</code> и{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">api_token</code> уже внутри скачанного файла.
          </li>
          <li>После копирования — перезапуск dedicated server.</li>
          <li>
            Проверка: в <code className="rounded bg-muted px-1 py-0.5 text-xs">profiles\ShopClaim\mod.log</code> строка{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">Config loaded</code>.
          </li>
        </ul>
        <p className="text-muted-foreground">
          Каталог товаров (<code className="rounded bg-muted px-1 py-0.5 text-xs">offers.yaml</code>) на VDS не
          кладут — он на стороне ShopClaim Bridge; правки — в разделе «Каталог» ЛК.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 text-sm">
      <p>
        Скачанный файл положите в{" "}
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
          &lt;profiles инстанса&gt;\ShopClaim\config.json
        </code>{" "}
        на game VDS — <span className="text-muted-foreground">не в PBO и не в папку мода</span>.
      </p>
      <p className="text-muted-foreground">
        Один config на инстанс (на каждый server_id — своя кнопка). После копирования перезапустите сервер.
      </p>
    </div>
  );
}
