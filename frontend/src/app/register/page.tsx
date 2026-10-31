"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import type { z } from "zod";
import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { API_MODE } from "@/lib/config";
import { applyServerErrors } from "@/lib/form-errors";
import { registerSchema } from "@/lib/validation";
import { useAuthStore } from "@/stores/auth";

type RegisterValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async ({ password_confirm: _, ...values }: RegisterValues) => {
    try {
      await api.auth.register(values);
      if (API_MODE === "mock") {
        // В демо письма не уходят — сразу входим.
        await login(values.email, values.password);
        toast.success("Аккаунт создан");
        router.push("/account");
      } else {
        setSentTo(values.email);
      }
    } catch (error) {
      if (error instanceof ApiError && applyServerErrors(error, setError)) return;
      setError("root", {
        message: error instanceof ApiError ? error.message : "Не удалось зарегистрироваться",
      });
    }
  };

  if (sentTo) {
    return (
      <AuthCard title="Подтвердите email">
        <div className="space-y-4 text-center">
          <MailCheck className="text-primary mx-auto size-12" />
          <p className="text-muted-foreground text-sm">
            Мы отправили письмо на <span className="text-foreground font-medium">{sentTo}</span>.
            Перейдите по ссылке из письма, чтобы активировать аккаунт.
          </p>
          <Button asChild variant="outline">
            <Link href="/login">Перейти ко входу</Link>
          </Button>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Регистрация"
      description="Создайте аккаунт за минуту"
      footer={
        <>
          Уже есть аккаунт? <AuthLink href="/login">Войти</AuthLink>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
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
        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            aria-invalid={!!errors.email}
            {...register("email")}
          />
        </Field>
        <Field
          label="Пароль"
          htmlFor="password"
          error={errors.password?.message}
          hint="Минимум 8 символов"
        >
          <PasswordInput
            id="password"
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            {...register("password")}
          />
        </Field>
        <Field
          label="Повторите пароль"
          htmlFor="password_confirm"
          error={errors.password_confirm?.message}
        >
          <PasswordInput
            id="password_confirm"
            autoComplete="new-password"
            aria-invalid={!!errors.password_confirm}
            {...register("password_confirm")}
          />
        </Field>
        {errors.root && (
          <p
            className="bg-destructive/10 text-destructive rounded-lg px-3 py-2 text-sm"
            role="alert"
          >
            {errors.root.message}
          </p>
        )}
        <Button type="submit" size="lg" loading={isSubmitting}>
          Создать аккаунт
        </Button>
      </form>
    </AuthCard>
  );
}
