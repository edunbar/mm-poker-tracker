import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "../../lib/utils";

const textareaVariants = cva(
  "flex min-h-[60px] w-full border bg-background text-foreground transition-colors placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 resize-vertical",
  {
    variants: {
      variant: {
        default: "border-input focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        ghost: "border-transparent focus-visible:border-input",
        error: "border-destructive focus-visible:ring-2 focus-visible:ring-destructive focus-visible:ring-offset-2",
      },
      size: {
        default: "px-3 py-2 text-sm",
        sm: "px-2 py-1 text-xs",
        lg: "px-4 py-3 text-base",
        xl: "px-4 py-3 text-lg",
      },
      rounded: {
        default: "rounded-md",
        sm: "rounded-sm",
        lg: "rounded-lg",
        full: "rounded-full",
      },
      resize: {
        none: "resize-none",
        vertical: "resize-vertical",
        horizontal: "resize-horizontal",
        both: "resize",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      rounded: "default",
      resize: "vertical",
    },
  }
);

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {
  error?: boolean;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant, size, rounded, resize, error, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          textareaVariants({
            variant: error ? "error" : variant,
            size,
            rounded,
            resize,
          }),
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea, textareaVariants };