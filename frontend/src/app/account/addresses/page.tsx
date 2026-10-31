"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AddressForm, formatAddress } from "@/components/account/address-form";
import { Button } from "@/components/ui/button";
import { Badge, EmptyState, Skeleton } from "@/components/ui/misc";
import { Dialog, DialogContent } from "@/components/ui/sheet";
import { api } from "@/lib/api";
import type { Address } from "@/lib/api/types";

export default function AddressesPage() {
  const queryClient = useQueryClient();
  const { data, isPending } = useQuery({ queryKey: ["addresses"], queryFn: api.addresses.list });
  const [editing, setEditing] = useState<Address | "new" | null>(null);

  const remove = useMutation({
    mutationFn: (id: number) => api.addresses.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["addresses"] });
      toast.success("Адрес удалён");
    },
    onError: () => toast.error("Не удалось удалить адрес"),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Адреса доставки</h1>
        {!!data?.length && (
          <Button onClick={() => setEditing("new")}>
            <Plus /> Добавить
          </Button>
        )}
      </div>

      {isPending ? (
        <Skeleton className="h-32" />
      ) : !data?.length ? (
        <EmptyState
          icon={<MapPin />}
          title="Адресов пока нет"
          description="Сохраните адрес, чтобы быстрее оформлять заказы."
          action={
            <Button onClick={() => setEditing("new")}>
              <Plus /> Добавить адрес
            </Button>
          }
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {data.map((a) => (
            <li key={a.id} className="bg-card flex flex-col gap-3 rounded-2xl border p-5">
              <div className="flex items-start justify-between gap-2">
                <MapPin className="text-muted-foreground mt-0.5 size-5 shrink-0" />
                <div className="flex-1">
                  <p className="font-medium">{formatAddress(a)}</p>
                  {a.postal_code && (
                    <p className="text-muted-foreground text-sm">Индекс {a.postal_code}</p>
                  )}
                </div>
                {a.is_default && <Badge variant="soft">Основной</Badge>}
              </div>
              <div className="mt-auto flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => setEditing(a)}>
                  <Pencil /> Изменить
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground hover:text-destructive"
                  onClick={() => remove.mutate(a.id)}
                  disabled={remove.isPending}
                >
                  <Trash2 /> Удалить
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        {editing !== null && (
          <DialogContent title={editing === "new" ? "Новый адрес" : "Изменить адрес"}>
            <AddressForm
              address={editing === "new" ? undefined : editing}
              onSaved={() => setEditing(null)}
              onCancel={() => setEditing(null)}
            />
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
