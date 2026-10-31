"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Banknote, Check, CreditCard, MapPin, Plus, Store, Truck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { AddressForm, formatAddress } from "@/components/account/address-form";
import { RequireAuth } from "@/components/auth/require-auth";
import { Button } from "@/components/ui/button";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { useHydrated } from "@/hooks/use-hydrated";
import { ApiError, api } from "@/lib/api";
import type { DeliveryMethod, PaymentMethod } from "@/lib/api/types";
import { DELIVERY } from "@/lib/config";
import { calcDeliveryPrice, cn, formatPrice } from "@/lib/utils";
import { cartTotals, useCartStore } from "@/stores/cart";

type Step = 1 | 2 | 3;

function StepCard({
  step,
  current,
  title,
  summary,
  onEdit,
  children,
}: {
  step: Step;
  current: Step;
  title: string;
  summary?: React.ReactNode;
  onEdit: () => void;
  children: React.ReactNode;
}) {
  const done = current > step;
  const active = current === step;
  return (
    <section
      aria-current={active ? "step" : undefined}
      className={cn(
        "bg-card rounded-2xl border p-5 sm:p-6",
        active && "border-primary/40 shadow-sm",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-3 text-lg font-semibold">
          <span
            className={cn(
              "flex size-7 items-center justify-center rounded-full text-sm",
              done
                ? "bg-success text-white"
                : active
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted",
            )}
          >
            {done ? <Check className="size-4" /> : step}
          </span>
          {title}
        </h2>
        {done && (
          <Button variant="link" size="sm" onClick={onEdit}>
            Изменить
          </Button>
        )}
      </div>
      {done && summary && <div className="text-muted-foreground mt-2 pl-10 text-sm">{summary}</div>}
      {active && <div className="mt-5">{children}</div>}
    </section>
  );
}

function OptionCard({
  checked,
  onSelect,
  icon,
  title,
  description,
  aside,
  name,
}: {
  checked: boolean;
  onSelect: () => void;
  icon: React.ReactNode;
  title: string;
  description?: string;
  aside?: React.ReactNode;
  name: string;
}) {
  return (
    <label
      className={cn(
        "has-[:focus-visible]:ring-ring/30 flex cursor-pointer items-center gap-4 rounded-xl border-2 p-4 transition-colors has-[:focus-visible]:ring-3",
        checked ? "border-primary bg-primary-soft/50" : "hover:border-input",
      )}
    >
      <input type="radio" name={name} checked={checked} onChange={onSelect} className="sr-only" />
      <span className="bg-muted flex size-10 shrink-0 items-center justify-center rounded-lg [&_svg]:size-5">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{title}</span>
        {description && <span className="text-muted-foreground block text-sm">{description}</span>}
      </span>
      {aside && <span className="text-sm font-medium">{aside}</span>}
    </label>
  );
}

function CheckoutFlow() {
  const router = useRouter();
  const lines = useCartStore((s) => s.lines);
  const promo = useCartStore((s) => s.promo);
  const clearCart = useCartStore((s) => s.clear);
  const { count, subtotal, discount, total } = cartTotals(lines, promo);

  const [step, setStep] = useState<Step>(1);
  const [addressId, setAddressId] = useState<number | null>(null);
  const [addingAddress, setAddingAddress] = useState(false);
  const [delivery, setDelivery] = useState<DeliveryMethod>("courier");
  const [payment, setPayment] = useState<PaymentMethod>("card");

  const addresses = useQuery({ queryKey: ["addresses"], queryFn: api.addresses.list });
  const selectedAddress =
    addresses.data?.find((a) => a.id === addressId) ??
    addresses.data?.find((a) => a.is_default) ??
    addresses.data?.[0];

  const deliveryPrice = calcDeliveryPrice(delivery, total);
  const grandTotal = total + deliveryPrice;

  const placeOrder = useMutation({
    mutationFn: async () => {
      const order = await api.orders.create({
        address_id: selectedAddress?.id,
        delivery_method: delivery,
        payment_method: payment,
        promo_code: promo?.code,
        items: lines.map((l) => ({ variant_id: l.variantId, quantity: l.quantity })),
      });
      const redirect =
        payment === "card"
          ? (await api.payments.checkoutSession(order.number)).url
          : `/checkout/success?order=${order.number}`;
      return { order, redirect };
    },
    onSuccess: ({ redirect }) => {
      clearCart();
      if (redirect.startsWith("http")) window.location.assign(redirect);
      else router.push(redirect);
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Не удалось оформить заказ"),
  });

  if (lines.length === 0 && !placeOrder.isSuccess) {
    return (
      <EmptyState
        icon={<Truck />}
        title="Нечего оформлять"
        description="Корзина пуста — добавьте товары, чтобы оформить заказ."
        action={
          <Button asChild>
            <Link href="/catalog">В каталог</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="grid items-start gap-8 lg:grid-cols-[1fr_380px]">
      <div className="space-y-4">
        <StepCard
          step={1}
          current={step}
          title="Адрес"
          onEdit={() => setStep(1)}
          summary={selectedAddress && formatAddress(selectedAddress)}
        >
          {addresses.isPending ? (
            <Skeleton className="h-24" />
          ) : addingAddress || !addresses.data?.length ? (
            <AddressForm
              onSaved={(a) => {
                setAddressId(a.id);
                setAddingAddress(false);
              }}
              onCancel={addresses.data?.length ? () => setAddingAddress(false) : undefined}
            />
          ) : (
            <div className="space-y-3">
              {addresses.data.map((a) => (
                <OptionCard
                  key={a.id}
                  name="address"
                  checked={selectedAddress?.id === a.id}
                  onSelect={() => setAddressId(a.id)}
                  icon={<MapPin />}
                  title={formatAddress(a)}
                  description={a.postal_code ? `Индекс ${a.postal_code}` : undefined}
                  aside={
                    a.is_default ? (
                      <span className="text-muted-foreground">основной</span>
                    ) : undefined
                  }
                />
              ))}
              <div className="flex flex-wrap gap-2 pt-2">
                <Button onClick={() => setStep(2)} disabled={!selectedAddress}>
                  Продолжить
                </Button>
                <Button variant="ghost" onClick={() => setAddingAddress(true)}>
                  <Plus /> Новый адрес
                </Button>
              </div>
            </div>
          )}
        </StepCard>

        <StepCard
          step={2}
          current={step}
          title="Доставка"
          onEdit={() => setStep(2)}
          summary={`${DELIVERY[delivery].label}, ${deliveryPrice ? formatPrice(deliveryPrice) : "бесплатно"}`}
        >
          <div className="space-y-3">
            {(["courier", "pickup"] as const).map((method) => {
              const price = calcDeliveryPrice(method, total);
              return (
                <OptionCard
                  key={method}
                  name="delivery"
                  checked={delivery === method}
                  onSelect={() => setDelivery(method)}
                  icon={method === "courier" ? <Truck /> : <Store />}
                  title={DELIVERY[method].label}
                  description={DELIVERY[method].eta}
                  aside={
                    price ? formatPrice(price) : <span className="text-success">бесплатно</span>
                  }
                />
              );
            })}
            <Button className="mt-2" onClick={() => setStep(3)}>
              Продолжить
            </Button>
          </div>
        </StepCard>

        <StepCard step={3} current={step} title="Оплата" onEdit={() => setStep(3)}>
          <div className="space-y-3">
            <OptionCard
              name="payment"
              checked={payment === "card"}
              onSelect={() => setPayment("card")}
              icon={<CreditCard />}
              title="Картой онлайн"
              description="Через Stripe. Тестовая карта: 4242 4242 4242 4242"
            />
            <OptionCard
              name="payment"
              checked={payment === "cash"}
              onSelect={() => setPayment("cash")}
              icon={<Banknote />}
              title="При получении"
              description="Наличными или картой курьеру"
            />
          </div>
        </StepCard>
      </div>

      <aside className="bg-card space-y-4 rounded-2xl border p-5 lg:sticky lg:top-32">
        <h2 className="text-lg font-semibold">Заказ · {count} шт.</h2>
        <ul className="max-h-64 space-y-3 overflow-y-auto">
          {lines.map((l) => (
            <li key={l.variantId} className="flex items-center gap-3">
              <div className="bg-muted relative size-12 shrink-0 overflow-hidden rounded-lg">
                {l.image && (
                  <Image src={l.image} alt="" fill sizes="48px" className="object-cover" />
                )}
              </div>
              <div className="min-w-0 flex-1 text-sm">
                <p className="truncate font-medium">{l.name}</p>
                <p className="text-muted-foreground">
                  {l.variantName} · {l.quantity} шт.
                </p>
              </div>
              <span className="text-sm font-medium tabular-nums">
                {formatPrice(l.price * l.quantity)}
              </span>
            </li>
          ))}
        </ul>
        <dl className="space-y-2 border-t pt-4 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted-foreground">Товары</dt>
            <dd className="tabular-nums">{formatPrice(subtotal)}</dd>
          </div>
          {discount > 0 && (
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Промокод {promo?.code}</dt>
              <dd className="text-success tabular-nums">−{formatPrice(discount)}</dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt className="text-muted-foreground">Доставка</dt>
            <dd className="tabular-nums">
              {deliveryPrice ? formatPrice(deliveryPrice) : "бесплатно"}
            </dd>
          </div>
        </dl>
        <div className="flex items-baseline justify-between border-t pt-4">
          <span className="font-semibold">К оплате</span>
          <span className="text-2xl font-bold tabular-nums">{formatPrice(grandTotal)}</span>
        </div>
        <Button
          size="lg"
          className="w-full"
          disabled={step < 3 || !selectedAddress}
          loading={placeOrder.isPending}
          onClick={() => placeOrder.mutate()}
        >
          {payment === "card" ? "Перейти к оплате" : "Подтвердить заказ"}
        </Button>
        {step < 3 && (
          <p className="text-muted-foreground text-center text-xs">
            Заполните все шаги, чтобы продолжить
          </p>
        )}
      </aside>
    </div>
  );
}

export default function CheckoutPage() {
  const hydrated = useHydrated();
  return (
    <div className="container-page py-6 sm:py-8">
      <h1 className="mb-6 text-3xl font-bold tracking-tight">Оформление заказа</h1>
      <RequireAuth>{hydrated ? <CheckoutFlow /> : <Skeleton className="h-96" />}</RequireAuth>
    </div>
  );
}
