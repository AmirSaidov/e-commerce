"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { MailCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { emailSchema } from "@/lib/validation";

const schema = z.object({ email: emailSchema });

export default function PasswordResetPage() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  return (
    <AuthCard
      title="Восстановление пароля"
      description="Пришлём ссылку для установки нового пароля"
      footer={<AuthLink href="/login">Вернуться ко входу</AuthLink>}
    >
      {sentTo ? (
        <div className="space-y-3 text-center">
          <MailCheck className="text-primary mx-auto size-12" />
          <p className="text-muted-foreground text-sm">
            Если аккаунт с адресом <span className="text-foreground font-medium">{sentTo}</span>{" "}
            существует, письмо уже в пути. Проверьте папку «Спам», если не найдёте его.
          </p>
        </div>
      ) : (
        <form
          className="grid gap-4"
          noValidate
          onSubmit={handleSubmit(async ({ email }) => {
            // Ответ одинаковый для любых email — чтобы нельзя было перебором узнать, кто зарегистрирован.
            await api.auth.requestPasswordReset(email).catch(() => undefined);
            setSentTo(email);
          })}
        >
          <Field label="Email" htmlFor="email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              aria-invalid={!!errors.email}
              {...register("email")}
            />
          </Field>
          <Button type="submit" size="lg" loading={isSubmitting}>
            Отправить ссылку
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
