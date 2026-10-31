"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, RotateCcw } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { ORDER_FLOW, OrderStatusBadge, orderStatusLabel } from "@/components/account/order-status";
import { formatAddress } from "@/components/account/address-form";
import { Button } from "@/components/ui/button";
import { Card, Skeleton } from "@/components/ui/misc";
import { ApiError, api } from "@/lib/api";
import type { Order } from "@/lib/api/types";
import { DELIVERY } from "@/lib/config";
import { cn, formatDate, formatPrice, toNumber } from "@/lib/utils";
import { lineFromProduct, useCartStore } from "@/stores/cart";

function Timeline({ order }: { order: Order }) {
  if (order.status === "cancelled") {
    return <p className="text-muted-foreground text-sm">Заказ отменён.</p>;
  }
  const current = ORDER_FLOW.indexOf(order.status);
  return (
    <ol className="grid grid-cols-5 gap-2">
      {ORDER_FLOW.map((status, i) => (
        <li key={status} className="space-y-2">
          <div className={cn("h-1.5 rounded-full", i <= current ? "bg-primary" : "bg-muted")} />
          <p
            className={cn(
              "flex items-center gap-1 text-xs",
              i <= current ? "font-medium" : "text-muted-foreground",
            )}
          >
            {i < current && <Check className="text-primary size-3" />}
            {orderStatusLabel(status)}
          </p>
        </li>
      ))}
    </ol>
  );
}

export default function OrderPage() {
  const { number } = useParams<{ number: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const addToCart = useCartStore((s) => s.add);
  const {
    data: order,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["order", number],
    queryFn: () => api.orders.get(number),
  });

  const cancel = useMutation({
    mutationFn: () => api.orders.cancel(number),
    onSuccess: (updated) => {
      queryClient.setQueryData(["order", number], updated);
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast.success("Заказ отменён");
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Не удалось отменить заказ"),
  });

  const pay = useMutation({
    mutationFn: () => api.payments.checkoutSession(number),
    onSuccess: ({ url }) =>
      url.startsWith("http") ? window.location.assign(url) : router.push(url),
    onError: () => toast.error("Не удалось перейти к оплате"),
  });

  if (isPending) return <Skeleton className="h-96" />;
  if (isError) {
    return (
      <div className="space-y-3">
        <p className="text-muted-foreground">Заказ не найден.</p>
        <Button asChild variant="outline">
          <Link href="/account/orders">К списку заказов</Link>
        </Button>
      </div>
    );
  }

  const repeat = async () => {
    // Актуальные цены и остатки берём из каталога, а не из старого заказа.
    const products = await Promise.all(
      order.items.map((it) => api.catalog.product(it.product_slug).catch(() => null)),
    );
    let added = 0;
    order.items.forEach((it, i) => {
      const product = products[i];
      const variant = product?.variants.find((v) => v.id === it.variant_id);
      if (product && variant && variant.stock > 0) {
        addToCart(lineFromProduct(product, variant), it.quantity);
        added++;
      }
    });
    if (added) {
      toast.success("Товары добавлены в корзину");
      router.push("/cart");
    } else {
      toast.error("Этих товаров сейчас нет в наличии");
    }
  };

  const canCancel = order.status === "created" || order.status === "paid";
  const canPay = order.status === "created" && order.payment_method === "card";

  return (
    <div className="space-y-6">
      <Link
        href="/account/orders"
        className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> Все заказы
      </Link>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Заказ {order.number}</h1>
          <p className="text-muted-foreground text-sm">от {formatDate(order.created_at)}</p>
        </div>
        <OrderStatusBadge status={order.status} />
      </div>

      <Card className="p-5">
        <Timeline order={order} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <Card className="divide-y px-5">
          {order.items.map((it) => (
            <div key={it.id} className="flex items-center gap-4 py-4">
              <div className="bg-muted relative size-16 shrink-0 overflow-hidden rounded-xl">
                {it.image && (
                  <Image src={it.image} alt="" fill sizes="64px" className="object-cover" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <Link
                  href={`/product/${it.product_slug}`}
                  className="hover:text-primary text-sm font-medium"
                >
                  {it.product_name}
                </Link>
                <p className="text-muted-foreground text-xs">
                  {it.variant_name} · {it.quantity} × {formatPrice(it.price)}
                </p>
              </div>
              <span className="font-medium tabular-nums">
                {formatPrice(toNumber(it.price) * it.quantity)}
              </span>
            </div>
          ))}
        </Card>

        <div className="space-y-4">
          <Card className="space-y-3 p-5 text-sm">
            <div>
              <p className="text-muted-foreground">Доставка</p>
              <p className="font-medium">{DELIVERY[order.delivery_method].label}</p>
              {order.address && <p>{formatAddress(order.address)}</p>}
            </div>
            <div>
              <p className="text-muted-foreground">Оплата</p>
              <p className="font-medium">
                {order.payment_method === "card" ? "Картой онлайн" : "При получении"}
              </p>
            </div>
            <dl className="space-y-1.5 border-t pt-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Товары</dt>
                <dd className="tabular-nums">{formatPrice(order.subtotal)}</dd>
              </div>
              {toNumber(order.discount) > 0 && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Промокод {order.promo_code}</dt>
                  <dd className="text-success tabular-nums">−{formatPrice(order.discount)}</dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Доставка</dt>
                <dd className="tabular-nums">
                  {toNumber(order.delivery_price) ? formatPrice(order.delivery_price) : "бесплатно"}
                </dd>
              </div>
              <div className="flex justify-between border-t pt-2 text-base font-semibold">
                <dt>Итого</dt>
                <dd className="tabular-nums">{formatPrice(order.total)}</dd>
              </div>
            </dl>
          </Card>
          <div className="grid gap-2">
            {canPay && (
              <Button onClick={() => pay.mutate()} loading={pay.isPending}>
                Оплатить заказ
              </Button>
            )}
            <Button variant="outline" onClick={repeat}>
              <RotateCcw /> Повторить заказ
            </Button>
            {canCancel && (
              <Button
                variant="ghost"
                className="text-destructive hover:text-destructive"
                loading={cancel.isPending}
                onClick={() => {
                  if (window.confirm("Отменить заказ? Это действие нельзя отменить."))
                    cancel.mutate();
                }}
              >
                Отменить заказ
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
