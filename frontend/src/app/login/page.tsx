"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import type { z } from "zod";
import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { API_MODE } from "@/lib/config";
import { DEMO_USER } from "@/lib/mock/backend";
import { loginSchema } from "@/lib/validation";
import { useAuthStore } from "@/stores/auth";

type LoginValues = z.infer<typeof loginSchema>;

function safeNext(next: string | null) {
  // Только относительные пути внутри сайта — защита от open redirect.
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/account";
}

function LoginForm() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const { status, login } = useAuthStore();
  const {
    register,
    handleSubmit,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, router, next]);

  const onSubmit = async (values: LoginValues) => {
    try {
      await login(values.email, values.password);
      toast.success("С возвращением!");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Не удалось войти";
      setError("root", { message });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
      {API_MODE === "mock" && (
        <div className="bg-primary-soft text-primary rounded-lg p-3 text-sm">
          Демо-аккаунт: {DEMO_USER.email} / {DEMO_USER.password}
          <Button
            type="button"
            variant="link"
            size="sm"
            className="ml-1"
            onClick={() => {
              setValue("email", DEMO_USER.email);
              setValue("password", DEMO_USER.password);
            }}
          >
            Подставить
          </Button>
        </div>
      )}
      <Field label="Email" htmlFor="email" error={errors.email?.message}>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          aria-invalid={!!errors.email}
          {...register("email")}
        />
      </Field>
      <Field label="Пароль" htmlFor="password" error={errors.password?.message}>
        <PasswordInput
          id="password"
          autoComplete="current-password"
          aria-invalid={!!errors.password}
          {...register("password")}
        />
      </Field>
      <div className="-mt-2 text-right">
        <AuthLink href="/password-reset">Забыли пароль?</AuthLink>
      </div>
      {errors.root && (
        <p className="bg-destructive/10 text-destructive rounded-lg px-3 py-2 text-sm" role="alert">
          {errors.root.message}
        </p>
      )}
      <Button type="submit" size="lg" loading={isSubmitting}>
        Войти
      </Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthCard
      title="Вход"
      description="Войдите, чтобы оформлять заказы и сохранять избранное"
      footer={
        <>
          Нет аккаунта? <AuthLink href="/register">Зарегистрироваться</AuthLink>
        </>
      }
    >
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthCard>
  );
}
