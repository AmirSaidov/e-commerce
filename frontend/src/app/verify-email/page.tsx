"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";

// Ссылка из письма: /verify-email?uid=...&token=...
function Verify() {
  const params = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const { isPending, isError, error } = useQuery({
    queryKey: ["verify-email", uid, token],
    queryFn: () => api.auth.verifyEmail(uid, token).then(() => true),
    enabled: !!uid && !!token,
    retry: false,
  });

  if (!uid || !token || isError) {
    return (
      <div className="space-y-4 text-center">
        <CircleAlert className="text-destructive mx-auto size-12" />
        <p className="text-muted-foreground text-sm">
          {error instanceof ApiError ? error.message : "Ссылка недействительна или устарела."}
        </p>
      </div>
    );
  }
  if (isPending) {
    return <LoaderCircle className="text-muted-foreground mx-auto size-10 animate-spin" />;
  }
  return (
    <div className="space-y-4 text-center">
      <CircleCheck className="text-success mx-auto size-12" />
      <p className="text-muted-foreground text-sm">Email подтверждён. Теперь можно войти.</p>
      <Button asChild>
        <Link href="/login">Войти</Link>
      </Button>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <AuthCard title="Подтверждение email">
      <Suspense>
        <Verify />
      </Suspense>
    </AuthCard>
  );
}
