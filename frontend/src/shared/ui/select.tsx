import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "../../lib/utils";

const selectVariants = cva(
  "flex w-full border bg-background text-foreground transition-colors focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border-input focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        ghost: "border-transparent focus-visible:border-input",
        error: "border-destructive focus-visible:ring-2 focus-visible:ring-destructive focus-visible:ring-offset-2",
      },
      size: {
        default: "h-10 px-3 py-2 text-sm",
        sm: "h-8 px-2 py-1 text-xs",
        lg: "h-12 px-4 py-3 text-base",
        xl: "h-14 px-4 py-3 text-lg",
      },
      rounded: {
        default: "rounded-md",
        sm: "rounded-sm",
        lg: "rounded-lg",
        full: "rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      rounded: "default",
    },
  }
);

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'>,
    VariantProps<typeof selectVariants> {
  error?: boolean;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, variant, size, rounded, error, children, ...props }, ref) => {
    return (
      <select
        className={cn(
          selectVariants({
            variant: error ? "error" : variant,
            size,
            rounded,
          }),
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </select>
    );
  }
);
Select.displayName = "Select";

export { Select, selectVariants };