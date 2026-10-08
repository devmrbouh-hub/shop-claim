import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { api, formatApiError, User } from "@/api/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Props = {
  user: User;
  onUserUpdate: (user: User) => void;
};

const emailSchema = z.object({
  current_password: z.string().min(1, "Введите текущий пароль"),
  new_email: z.string().email("Некорректный email"),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Введите текущий пароль"),
    new_password: z.string().min(10, "Новый пароль: минимум 10 символов").max(128),
    confirm_password: z.string().min(1, "Подтвердите пароль"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Пароли не совпадают",
    path: ["confirm_password"],
  });

type EmailFormValues = z.infer<typeof emailSchema>;
type PasswordFormValues = z.infer<typeof passwordSchema>;

export default function AccountSettings({ user, onUserUpdate }: Props) {
  const emailForm = useForm<EmailFormValues>({
    resolver: zodResolver(emailSchema),
    defaultValues: { current_password: "", new_email: "" },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const changeEmail = async (values: EmailFormValues) => {
    try {
      const r = await api.changeEmail(values.current_password, values.new_email);
      onUserUpdate({ ...user, pending_email: r.pending_email });
      emailForm.reset();
      toast.success(`Письмо отправлено на ${r.pending_email}. Подтвердите смену по ссылке из письма.`);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const cancelPending = async () => {
    try {
      await api.cancelEmailChange();
      onUserUpdate({ ...user, pending_email: null });
      toast.success("Смена email отменена");
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const changePassword = async (values: PasswordFormValues) => {
    try {
      const updated = await api.changePassword(values.current_password, values.new_password);
      onUserUpdate(updated);
      passwordForm.reset();
      toast.success("Пароль обновлён");
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Аккаунт</CardTitle>
        <CardDescription>
          Email для входа: <span className="font-medium text-foreground">{user.email}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {user.pending_email && (
          <Alert>
            <AlertDescription className="space-y-2">
              <p>
                Ожидается подтверждение смены email на{" "}
                <span className="font-medium">{user.pending_email}</span>. Проверьте почту на новом
                адресе.
              </p>
              <Button type="button" variant="secondary" size="sm" onClick={cancelPending}>
                Отменить смену
              </Button>
            </AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="email">
          <TabsList>
            <TabsTrigger value="email">Email</TabsTrigger>
            <TabsTrigger value="password">Пароль</TabsTrigger>
          </TabsList>

          <TabsContent value="email" className="mt-4">
            <Form {...emailForm}>
              <form onSubmit={emailForm.handleSubmit(changeEmail)} className="grid max-w-md gap-4">
                <FormField
                  control={emailForm.control}
                  name="current_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Текущий пароль</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="current-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={emailForm.control}
                  name="new_email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Новый email</FormLabel>
                      <FormControl>
                        <Input type="email" autoComplete="email" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" disabled={emailForm.formState.isSubmitting}>
                  {emailForm.formState.isSubmitting ? "Отправка…" : "Отправить подтверждение"}
                </Button>
              </form>
            </Form>
          </TabsContent>

          <TabsContent value="password" className="mt-4">
            <Form {...passwordForm}>
              <form onSubmit={passwordForm.handleSubmit(changePassword)} className="grid max-w-md gap-4">
                <FormField
                  control={passwordForm.control}
                  name="current_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Текущий пароль</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="current-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={passwordForm.control}
                  name="new_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Новый пароль</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="new-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={passwordForm.control}
                  name="confirm_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Подтверждение пароля</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="new-password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" disabled={passwordForm.formState.isSubmitting}>
                  {passwordForm.formState.isSubmitting ? "Сохранение…" : "Сменить пароль"}
                </Button>
              </form>
            </Form>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
