import * as React from "react";
import { cn } from "../../lib/utils";

/**
 * Minimal shadcn-style table primitives for CRA + React 17.
 * Tailwind classes match the admin page mock (clean, dashboard look).
 */

export function Table({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <table
      className={cn("w-full caption-bottom text-sm text-foreground table-fixed", className)}
      {...props}
    />
  );
}

export function TableHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className={cn("[&_tr]:border-b bg-muted/50 border-b-2 border-border", className)} {...props} />
  );
}

export function TableBody({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody className={cn("[&_tr:last-child]:border-0", className)} {...props} />
  );
}

export function TableFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tfoot className={cn("bg-muted font-medium", className)} {...props} />
  );
}

export function TableRow({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn("border-b border-border transition-colors", className)}
      {...props}
    />
  );
}

export function TableHead({
  className,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "h-12 px-4 text-left align-middle font-semibold text-foreground text-sm uppercase tracking-wide",
        className
      )}
      {...props}
    />
  );
}

export function TableCell({
  className,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn("px-4 py-4 align-middle text-foreground border-b border-border/50", className)}
      {...props}
    />
  );
}

export function TableCaption({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableCaptionElement>) {
  return (
    <caption
      className={cn("mt-2 text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}
