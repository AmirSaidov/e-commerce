"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { BadgeCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import type { z } from "zod";
import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Card } from "@/components/ui/misc";
import { ApiError, api } from "@/lib/api";
import type { User } from "@/lib/api/types";
import { applyServerErrors } from "@/lib/form-errors";
import { changePasswordSchema, profileSchema } from "@/lib/validation";
import { useAuthStore } from "@/stores/auth";

type ProfileValues = z.infer<typeof profileSchema>;
type PasswordValues = z.infer<typeof changePasswordSchema>;

function ProfileForm({ user }: { user: User }) {
  const setUser = useAuthStore((s) => s.setUser);
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { first_name: user.first_name, last_name: user.last_name, phone: user.phone },
  });

  return (
    <form
      noValidate
      className="grid gap-4"
      onSubmit={handleSubmit(async (values) => {
        try {
          const updated = await api.users.update(values);
          setUser(updated);
          reset(values);
          toast.success("Профиль сохранён");
        } catch (error) {
          if (error instanceof ApiError && applyServerErrors(error, setError)) return;
          toast.error("Не удалось сохранить профиль");
        }
      })}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Имя" htmlFor="first_name" error={errors.first_name?.message}>
          <Input
            id="first_name"
            autoComplete="given-name"
            aria-invalid={!!errors.first_name}
            {...register("first_name")}
          />
        </Field>
        <Field label="Фамилия" htmlFor="last_name" error={errors.last_name?.message}>
          <Input
            id="last_name"
            autoComplete="family-name"
            aria-invalid={!!errors.last_name}
            {...register("last_name")}
          />
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Email" htmlFor="email" hint="Email изменить нельзя">
          <Input id="email" value={user.email} disabled readOnly />
        </Field>
        <Field label="Телефон" htmlFor="phone" error={errors.phone?.message}>
          <Input
            id="phone"
            type="tel"
            autoComplete="tel"
            aria-invalid={!!errors.phone}
            {...register("phone")}
          />
        </Field>
      </div>
      <div>
        <Button type="submit" loading={isSubmitting} disabled={!isDirty}>
          Сохранить
        </Button>
      </div>
    </form>
  );
}

function PasswordForm() {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordValues>({ resolver: zodResolver(changePasswordSchema) });

  return (
    <form
      noValidate
      className="grid gap-4"
      onSubmit={handleSubmit(async ({ old_password, new_password }) => {
        try {
          await api.users.changePassword(old_password, new_password);
          reset();
          toast.success("Пароль изменён");
        } catch (error) {
          if (error instanceof ApiError && applyServerErrors(error, setError)) return;
          toast.error("Не удалось изменить пароль");
        }
      })}
    >
      <Field label="Текущий пароль" htmlFor="old_password" error={errors.old_password?.message}>
        <PasswordInput
          id="old_password"
          autoComplete="current-password"
          aria-invalid={!!errors.old_password}
          {...register("old_password")}
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Новый пароль" htmlFor="new_password" error={errors.new_password?.message}>
          <PasswordInput
            id="new_password"
            autoComplete="new-password"
            aria-invalid={!!errors.new_password}
            {...register("new_password")}
          />
        </Field>
        <Field
          label="Повторите пароль"
          htmlFor="new_password_confirm"
          error={errors.new_password_confirm?.message}
        >
          <PasswordInput
            id="new_password_confirm"
            autoComplete="new-password"
            aria-invalid={!!errors.new_password_confirm}
            {...register("new_password_confirm")}
          />
        </Field>
      </div>
      <div>
        <Button type="submit" variant="outline" loading={isSubmitting}>
          Изменить пароль
        </Button>
      </div>
    </form>
  );
}

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)!;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Здравствуйте, {user.first_name || "покупатель"}!
        </h1>
        <p className="text-muted-foreground mt-1 inline-flex items-center gap-1.5 text-sm">
          {user.email}
          {user.is_email_verified && (
            <BadgeCheck className="text-success size-4" aria-label="Email подтверждён" />
          )}
        </p>
      </div>
      <Card className="p-5 sm:p-6">
        <h2 className="mb-4 text-lg font-semibold">Личные данные</h2>
        <ProfileForm user={user} />
      </Card>
      <Card className="p-5 sm:p-6">
        <h2 className="mb-4 text-lg font-semibold">Смена пароля</h2>
        <PasswordForm />
      </Card>
    </div>
  );
}
