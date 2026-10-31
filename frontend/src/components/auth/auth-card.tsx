import Link from "next/link";
import { Logo } from "@/components/layout/header";

export function AuthCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="container-page flex justify-center py-10 sm:py-16">
      <div className="w-full max-w-md space-y-6">
        <div className="space-y-4 text-center">
          <Logo className="justify-center" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            {description && <p className="text-muted-foreground mt-1 text-sm">{description}</p>}
          </div>
        </div>
        <div className="bg-card rounded-2xl border p-6 shadow-sm sm:p-8">{children}</div>
        {footer && <p className="text-muted-foreground text-center text-sm">{footer}</p>}
      </div>
    </div>
  );
}

export function AuthLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-primary font-medium hover:underline">
      {children}
    </Link>
  );
}
