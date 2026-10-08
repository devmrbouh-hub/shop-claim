import AccountSettings from "@/pages/account/AccountSettings";
import PageHeader from "@/components/PageHeader";
import { User } from "@/api/client";

type Props = { user: User; onUserUpdate: (user: User) => void };

export default function TenantAccountPage({ user, onUserUpdate }: Props) {
  return (
    <div className="space-y-6">
      <PageHeader title="Аккаунт" description="Профиль и настройки входа" />
      <AccountSettings user={user} onUserUpdate={onUserUpdate} />
    </div>
  );
}
