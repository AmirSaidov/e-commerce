import { create } from "zustand";
import { api } from "@/lib/api";
import type { User } from "@/lib/api/types";
import { linesFromServer, useCartStore } from "./cart";
import { useWishlistStore } from "./wishlist";

type Status = "loading" | "authenticated" | "guest";

interface AuthState {
  status: Status;
  user: User | null;
  /** Вызывается один раз при старте приложения: восстанавливает сессию по refresh-cookie. */
  init: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

async function afterLogin() {
  // Гостевая корзина сливается с серверной, затем подтягиваем избранное.
  const cart = useCartStore.getState();
  try {
    const merged = await api.cart.merge(
      cart.lines.map((l) => ({ variant_id: l.variantId, quantity: l.quantity })),
    );
    cart.replace(linesFromServer(merged));
  } catch {
    // корзина останется локальной и синхронизируется при следующем изменении
  }
  await useWishlistStore.getState().load();
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  status: "loading",
  user: null,
  init: async () => {
    if (get().status !== "loading") return;
    try {
      if (await api.auth.restore()) {
        const user = await api.users.me();
        set({ status: "authenticated", user });
        await useWishlistStore.getState().load();
        return;
      }
    } catch {
      // сессии нет или бэкенд недоступен — работаем как гость
    }
    set({ status: "guest", user: null });
  },
  login: async (email, password) => {
    await api.auth.login(email, password);
    const user = await api.users.me();
    set({ status: "authenticated", user });
    await afterLogin();
  },
  logout: async () => {
    try {
      await api.auth.logout();
    } finally {
      set({ status: "guest", user: null });
      useCartStore.getState().clear();
      useWishlistStore.getState().reset();
    }
  },
  setUser: (user) => set({ user }),
}));
