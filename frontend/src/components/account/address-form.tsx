"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import type { Address } from "@/lib/api/types";
import { applyServerErrors } from "@/lib/form-errors";

const addressSchema = z.object({
  city: z.string().trim().min(2, "Укажите город"),
  street: z.string().trim().min(2, "Укажите улицу"),
  building: z.string().trim().min(1, "Укажите дом"),
  apartment: z.string().trim().max(10),
  postal_code: z
    .string()
    .trim()
    .regex(/^\d{6}$/, "Индекс — 6 цифр")
    .or(z.literal("")),
  is_default: z.boolean(),
});
type AddressValues = z.infer<typeof addressSchema>;

export function formatAddress(a: Pick<Address, "city" | "street" | "building" | "apartment">) {
  return [a.city, `${a.street}, ${a.building}`, a.apartment && `кв. ${a.apartment}`]
    .filter(Boolean)
    .join(", ");
}

export function AddressForm({
  address,
  onSaved,
  onCancel,
}: {
  address?: Address;
  onSaved: (address: Address) => void;
  onCancel?: () => void;
}) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<AddressValues>({
    resolver: zodResolver(addressSchema),
    defaultValues: {
      city: address?.city ?? "",
      street: address?.street ?? "",
      building: address?.building ?? "",
      apartment: address?.apartment ?? "",
      postal_code: address?.postal_code ?? "",
      is_default: address?.is_default ?? false,
    },
  });

  const mutation = useMutation({
    mutationFn: (values: AddressValues) => api.addresses.save(values, address?.id),
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: ["addresses"] });
      toast.success(address ? "Адрес обновлён" : "Адрес добавлен");
      onSaved(saved);
    },
    onError: (error) => {
      if (error instanceof ApiError && applyServerErrors(error, setError)) return;
      toast.error(error instanceof ApiError ? error.message : "Не удалось сохранить адрес");
    },
  });

  return (
    <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="grid gap-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Город" htmlFor="city" error={errors.city?.message}>
          <Input
            id="city"
            autoComplete="address-level2"
            aria-invalid={!!errors.city}
            {...register("city")}
          />
        </Field>
        <Field label="Индекс" htmlFor="postal_code" error={errors.postal_code?.message}>
          <Input
            id="postal_code"
            inputMode="numeric"
            autoComplete="postal-code"
            aria-invalid={!!errors.postal_code}
            {...register("postal_code")}
          />
        </Field>
      </div>
      <Field label="Улица" htmlFor="street" error={errors.street?.message}>
        <Input
          id="street"
          autoComplete="address-line1"
          aria-invalid={!!errors.street}
          {...register("street")}
        />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Дом" htmlFor="building" error={errors.building?.message}>
          <Input id="building" aria-invalid={!!errors.building} {...register("building")} />
        </Field>
        <Field label="Квартира" htmlFor="apartment" error={errors.apartment?.message}>
          <Input id="apartment" aria-invalid={!!errors.apartment} {...register("apartment")} />
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          className="size-4 accent-[var(--primary)]"
          {...register("is_default")}
        />
        Сделать основным
      </label>
      <div className="flex gap-2">
        <Button type="submit" loading={mutation.isPending}>
          Сохранить адрес
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Отмена
          </Button>
        )}
      </div>
    </form>
  );
}
