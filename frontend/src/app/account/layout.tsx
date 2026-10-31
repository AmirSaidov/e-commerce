import type { Metadata } from "next";
import { AccountNav } from "@/components/account/account-nav";
import { RequireAuth } from "@/components/auth/require-auth";

export const metadata: Metadata = {
  title: "Личный кабинет",
  robots: { index: false },
};

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container-page py-6 sm:py-8">
      <div className="grid gap-6 lg:grid-cols-[220px_1fr] lg:gap-10">
        <AccountNav />
        <div className="min-w-0">
          <RequireAuth>{children}</RequireAuth>
        </div>
      </div>
    </div>
  );
}
