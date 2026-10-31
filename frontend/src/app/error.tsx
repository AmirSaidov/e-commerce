"use client";

import { CircleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="container-page flex flex-col items-center py-24 text-center">
      <span className="bg-destructive/10 text-destructive flex size-16 items-center justify-center rounded-full">
        <CircleAlert className="size-7" />
      </span>
      <h1 className="mt-6 text-3xl font-bold tracking-tight">Что-то пошло не так</h1>
      <p className="text-muted-foreground mt-2 max-w-md">
        Мы уже разбираемся. Попробуйте обновить страницу — обычно это помогает.
      </p>
      <div className="mt-8 flex gap-2">
        <Button onClick={reset}>Попробовать снова</Button>
        <Button asChild variant="outline">
          <Link href="/">На главную</Link>
        </Button>
      </div>
    </div>
  );
}
