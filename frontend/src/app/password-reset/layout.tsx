import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Восстановление пароля",
  robots: { index: false },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
