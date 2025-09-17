import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "../../lib/utils";

/**
 * Button component with variants
 * - Uses class-variance-authority for variant styling
 * - Tailwind classes for clean dashboard look
 */

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-colors " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90 rounded-2xl",
        outline: "border border-border bg-background hover:bg-accent hover:text-accent-foreground rounded-2xl",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-2xl",
        ghost: "hover:bg-accent hover:text-accent-foreground rounded-md",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-2xl",
        muted: "bg-muted text-foreground hover:bg-accent rounded-md",
        link: "text-primary underline-offset-4 hover:underline rounded-md",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3 py-1.5",
        lg: "h-11 px-8 py-3",
        xl: "h-12 px-6 py-3",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";
