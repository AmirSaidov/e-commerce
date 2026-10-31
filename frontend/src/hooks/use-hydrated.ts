import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/**
 * true только после гидрации. Нужен для данных из localStorage (корзина, тема),
 * чтобы серверный HTML совпадал с первым клиентским рендером.
 */
export function useHydrated() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
