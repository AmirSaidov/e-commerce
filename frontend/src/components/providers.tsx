"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useEffect, useState } from "react";
import { Toaster } from "sonner";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useCartStore } from "@/stores/cart";

function SessionBootstrap() {
  const init = useAuthStore((s) => s.init);
  useEffect(() => {
    void init();
  }, [init]);
  return null;
}

// Пока пользователь залогинен, корзина дублируется на сервер — чтобы она была на всех устройствах.
function CartSync() {
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsubscribe = useCartStore.subscribe((state, prev) => {
      if (state.lines === prev.lines) return;
      if (useAuthStore.getState().status !== "authenticated") return;
      clearTimeout(timer);
      timer = setTimeout(() => {
        const items = state.lines.map((l) => ({ variant_id: l.variantId, quantity: l.quantity }));
        api.cart.replace(items).catch(() => {
          // не критично: при следующем входе корзина сольётся заново
        });
      }, 800);
    });
    return () => {
      clearTimeout(timer);
      unsubscribe();
    };
  }, []);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <SessionBootstrap />
        <CartSync />
        {children}
        <Toaster position="bottom-right" richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
