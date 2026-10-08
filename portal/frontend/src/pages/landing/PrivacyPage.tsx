import PageHeader from "@/components/PageHeader";

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-12 space-y-6">
      <PageHeader
        title="Политика конфиденциальности (демо)"
        description="Шаблон для локальной разработки. Не является юридическим документом."
      />
      <p className="text-sm text-muted-foreground">
        Опубликуйте свою политику на боевом домене. В open-source снимке персональные данные
        оператора сервиса намеренно не включены.
      </p>
    </div>
  );
}
