"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Package } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { OrderStatusBadge } from "@/components/account/order-status";
import { Button } from "@/components/ui/button";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { formatDate, formatPrice, pluralize } from "@/lib/utils";

export default function OrdersPage() {
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["orders"],
    queryFn: api.orders.list,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Мои заказы</h1>
      {isPending ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-muted-foreground space-y-2 text-sm">
          <p>Не удалось загрузить заказы.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Повторить
          </Button>
        </div>
      ) : data.results.length === 0 ? (
        <EmptyState
          icon={<Package />}
          title="Заказов пока нет"
          description="Здесь появится история ваших покупок."
          action={
            <Button asChild>
              <Link href="/catalog">За покупками</Link>
            </Button>
          }
        />
      ) : (
        <ul className="space-y-3">
          {data.results.map((order) => {
            const count = order.items.reduce((s, it) => s + it.quantity, 0);
            return (
              <li key={order.number}>
                <Link
                  href={`/account/orders/${order.number}`}
                  className="group bg-card flex flex-col gap-4 rounded-2xl border p-5 transition-shadow hover:shadow-md sm:flex-row sm:items-center"
                >
                  <div className="flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">Заказ {order.number}</span>
                      <OrderStatusBadge status={order.status} />
                    </div>
                    <p className="text-muted-foreground text-sm">
                      от {formatDate(order.created_at)} · {count}{" "}
                      {pluralize(count, ["товар", "товара", "товаров"])}
                    </p>
                  </div>
                  <div className="flex -space-x-3">
                    {order.items.slice(0, 4).map((it) => (
                      <div
                        key={it.id}
                        className="border-card bg-muted relative size-12 overflow-hidden rounded-xl border-2"
                      >
                        {it.image && (
                          <Image src={it.image} alt="" fill sizes="48px" className="object-cover" />
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between gap-3 sm:w-40 sm:justify-end">
                    <span className="font-semibold tabular-nums">{formatPrice(order.total)}</span>
                    <ChevronRight className="text-muted-foreground size-5 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
