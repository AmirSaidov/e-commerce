import { create } from "zustand";
import { api } from "@/lib/api";

interface WishlistState {
  ids: number[];
  load: () => Promise<void>;
  /** Оптимистично переключает товар; при ошибке API откатывает состояние и пробрасывает её. */
  toggle: (productId: number) => Promise<boolean>;
  reset: () => void;
}

export const useWishlistStore = create<WishlistState>()((set, get) => ({
  ids: [],
  load: async () => {
    try {
      const products = await api.wishlist.list();
      set({ ids: products.map((p) => p.id) });
    } catch {
      set({ ids: [] });
    }
  },
  toggle: async (productId) => {
    const wasIn = get().ids.includes(productId);
    set((s) => ({ ids: wasIn ? s.ids.filter((id) => id !== productId) : [productId, ...s.ids] }));
    try {
      if (wasIn) await api.wishlist.remove(productId);
      else await api.wishlist.add(productId);
      return !wasIn;
    } catch (error) {
      set((s) => ({ ids: wasIn ? [productId, ...s.ids] : s.ids.filter((id) => id !== productId) }));
      throw error;
    }
  },
  reset: () => set({ ids: [] }),
}));
