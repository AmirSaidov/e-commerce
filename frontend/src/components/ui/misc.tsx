import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        soft: "bg-primary-soft text-primary",
        sale: "bg-destructive text-white",
        success: "bg-success/15 text-success",
        warning: "bg-warning/20 text-foreground",
        muted: "bg-muted text-muted-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("bg-muted animate-pulse rounded-lg", className)} {...props} />;
}

function Card({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("bg-card rounded-xl border", className)} {...props} />;
}

function Separator({ className }: { className?: string }) {
  return <hr className={cn("border-t", className)} />;
}

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed px-6 py-16 text-center">
      <div className="bg-primary-soft text-primary flex size-14 items-center justify-center rounded-full [&_svg]:size-6">
        {icon}
      </div>
      <h2 className="text-lg font-semibold">{title}</h2>
      {description && <p className="text-muted-foreground max-w-sm text-sm">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export { Badge, Card, EmptyState, Separator, Skeleton };
