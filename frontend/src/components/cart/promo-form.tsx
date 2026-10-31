"use client";

import { Tag, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { toNumber } from "@/lib/utils";
import { useCartStore } from "@/stores/cart";

export function PromoForm({ subtotal }: { subtotal: number }) {
  const promo = useCartStore((s) => s.promo);
  const applyPromo = useCartStore((s) => s.applyPromo);
  const removePromo = useCartStore((s) => s.removePromo);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (promo) {
    return (
      <div className="bg-success/10 flex items-center justify-between rounded-lg px-3 py-2 text-sm">
        <span className="text-success inline-flex items-center gap-2 font-medium">
          <Tag className="size-4" /> {promo.code}
        </span>
        <button
          type="button"
          onClick={removePromo}
          className="text-muted-foreground hover:text-foreground"
          aria-label="Убрать промокод"
        >
          <X className="size-4" />
        </button>
      </div>
    );
  }

  return (
    <form
      className="space-y-1.5"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!code.trim()) return;
        setLoading(true);
        setError(null);
        try {
          const result = await api.cart.checkPromo(code, subtotal);
          applyPromo({ code: result.code, type: result.type, value: toNumber(result.value) });
          setCode("");
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "Не удалось проверить промокод");
        } finally {
          setLoading(false);
        }
      }}
    >
      <div className="flex gap-2">
        <label htmlFor="promo" className="sr-only">
          Промокод
        </label>
        <Input
          id="promo"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="Промокод"
          aria-invalid={!!error}
          aria-describedby={error ? "promo-error" : undefined}
          autoComplete="off"
        />
        <Button type="submit" variant="secondary" loading={loading}>
          Применить
        </Button>
      </div>
      {error && (
        <p id="promo-error" className="text-destructive text-xs" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
