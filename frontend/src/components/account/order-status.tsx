import { Badge } from "@/components/ui/misc";
import type { OrderStatus } from "@/lib/api/types";

const STATUS: Record<
  OrderStatus,
  { label: string; variant: "soft" | "success" | "warning" | "muted" }
> = {
  created: { label: "Ожидает оплаты", variant: "warning" },
  paid: { label: "Оплачен", variant: "soft" },
  assembling: { label: "Собирается", variant: "soft" },
  shipped: { label: "В пути", variant: "soft" },
  delivered: { label: "Доставлен", variant: "success" },
  cancelled: { label: "Отменён", variant: "muted" },
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const { label, variant } = STATUS[status];
  return <Badge variant={variant}>{label}</Badge>;
}

export const ORDER_FLOW: OrderStatus[] = ["created", "paid", "assembling", "shipped", "delivered"];

export function orderStatusLabel(status: OrderStatus) {
  return STATUS[status].label;
}
