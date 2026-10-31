"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleCheck, Clock } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { RequireAuth } from "@/components/auth/require-auth";
import { OrderStatusBadge } from "@/components/account/order-status";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { formatPrice } from "@/lib/utils";

// После Stripe Checkout статус меняет вебхук, а не редирект, поэтому опрашиваем заказ, пока он не оплачен.
const POLL_MS = 2000;
const POLL_LIMIT = 15;

function Success() {
  const number = useSearchParams().get("order") ?? "";
  const [startedAt] = useState(() => Date.now());
  const {
    data: order,
    isPending,
    isError,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["order", number],
    queryFn: () => api.orders.get(number),
    enabled: !!number,
    refetchInterval: (query) => {
      const o = query.state.data;
      const waiting = o?.payment_method === "card" && o.status === "created";
      return waiting && query.state.dataUpdateCount < POLL_LIMIT ? POLL_MS : false;
    },
  });

  if (!number || isError) {
    return (
      <div className="text-center">
        <p className="text-muted-foreground">Заказ не найден.</p>
        <Button asChild variant="link">
          <Link href="/account/orders">Мои заказы</Link>
        </Button>
      </div>
    );
  }
  if (isPending) return <Skeleton className="mx-auto h-72 max-w-xl" />;

  const waiting = order.payment_method === "card" && order.status === "created";
  const gaveUp = waiting && dataUpdatedAt - startedAt >= POLL_MS * (POLL_LIMIT - 1);

  return (
    <div className="bg-card mx-auto max-w-xl space-y-6 rounded-3xl border p-6 text-center sm:p-10">
      <div
        className={
          waiting
            ? "bg-warning/20 text-warning mx-auto flex size-16 items-center justify-center rounded-full"
            : "bg-success/15 text-success mx-auto flex size-16 items-center justify-center rounded-full"
        }
      >
        {waiting ? <Clock className="size-8" /> : <CircleCheck className="size-8" />}
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">
          {waiting ? "Ждём подтверждение оплаты…" : "Спасибо, заказ оформлен!"}
        </h1>
        <p className="text-muted-foreground">
          Номер заказа <span className="text-foreground font-semibold">{order.number}</span>.{" "}
          {gaveUp
            ? "Оплата обрабатывается дольше обычного — статус обновится в личном кабинете."
            : "Письмо с деталями отправили на вашу почту."}
        </p>
        <OrderStatusBadge status={order.status} />
      </div>
      <dl className="bg-muted/50 space-y-2 rounded-2xl p-4 text-left text-sm">
        {order.items.map((it) => (
          <div key={it.id} className="flex justify-between gap-4">
            <dt className="truncate">
              {it.product_name} <span className="text-muted-foreground">× {it.quantity}</span>
            </dt>
            <dd className="tabular-nums">{formatPrice(Number(it.price) * it.quantity)}</dd>
          </div>
        ))}
        <div className="flex justify-between border-t pt-2 font-semibold">
          <dt>Итого</dt>
          <dd className="tabular-nums">{formatPrice(order.total)}</dd>
        </div>
      </dl>
      <div className="flex flex-col justify-center gap-2 sm:flex-row">
        <Button asChild>
          <Link href={`/account/orders/${order.number}`}>Открыть заказ</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/catalog">Продолжить покупки</Link>
        </Button>
      </div>
    </div>
  );
}

export default function CheckoutSuccessPage() {
  return (
    <div className="container-page py-10">
      <RequireAuth>
        <Suspense fallback={<Skeleton className="mx-auto h-72 max-w-xl" />}>
          <Success />
        </Suspense>
      </RequireAuth>
    </div>
  );
}
