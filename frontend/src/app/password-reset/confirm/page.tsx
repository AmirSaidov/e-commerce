"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { passwordSchema } from "@/lib/validation";

const schema = z
  .object({ password: passwordSchema, password_confirm: z.string() })
  .refine((d) => d.password === d.password_confirm, {
    path: ["password_confirm"],
    message: "Пароли не совпадают",
  });

// Ссылка из письма: /password-reset/confirm?uid=...&token=...
function ConfirmForm() {
  const router = useRouter();
  const params = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  if (!uid || !token) {
    return (
      <p className="text-muted-foreground text-center text-sm">Ссылка неполная. Запросите новую.</p>
    );
  }

  return (
    <form
      className="grid gap-4"
      noValidate
      onSubmit={handleSubmit(async ({ password }) => {
        try {
          await api.auth.confirmPasswordReset(uid, token, password);
          toast.success("Пароль изменён — войдите с новым паролем");
          router.push("/login");
        } catch (error) {
          setError("root", {
            message:
              error instanceof ApiError ? error.message : "Ссылка устарела. Запросите новую.",
          });
        }
      })}
    >
      <Field label="Новый пароль" htmlFor="password" error={errors.password?.message}>
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
        <p className="bg-destructive/10 text-destructive rounded-lg px-3 py-2 text-sm" role="alert">
          {errors.root.message}
        </p>
      )}
      <Button type="submit" size="lg" loading={isSubmitting}>
        Сохранить пароль
      </Button>
    </form>
  );
}

export default function PasswordResetConfirmPage() {
  return (
    <AuthCard
      title="Новый пароль"
      footer={<AuthLink href="/password-reset">Запросить ссылку заново</AuthLink>}
    >
      <Suspense>
        <ConfirmForm />
      </Suspense>
    </AuthCard>
  );
}
