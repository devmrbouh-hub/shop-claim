import PageHeader from "@/components/PageHeader";

export default function OfferPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-12 space-y-6">
      <PageHeader
        title="Публичная оферта (демо)"
        description="Шаблон для локальной разработки. Не является юридическим документом."
      />
      <p className="text-sm text-muted-foreground">
        В production разместите свою оферту и укажите URL через переменные окружения и маршруты
        лендинга. Этот репозиторий не содержит персональных данных исполнителя.
      </p>
    </div>
  );
}
