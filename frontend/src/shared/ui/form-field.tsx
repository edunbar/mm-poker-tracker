import * as React from "react";
import { cn } from "../../lib/utils";
import { Label } from "./label";

// Form Field Components for better composition

export interface FormFieldProps {
  children: React.ReactNode;
  className?: string;
}

const FormField = React.forwardRef<HTMLDivElement, FormFieldProps>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn("space-y-2", className)} {...props}>
      {children}
    </div>
  )
);
FormField.displayName = "FormField";

export interface FormLabelProps extends React.ComponentProps<typeof Label> {}

const FormLabel = React.forwardRef<
  React.ElementRef<typeof Label>,
  FormLabelProps
>(({ className, ...props }, ref) => (
  <Label
    ref={ref}
    className={cn("block mb-2", className)}
    {...props}
  />
));
FormLabel.displayName = "FormLabel";

export interface FormMessageProps
  extends React.HTMLAttributes<HTMLParagraphElement> {
  variant?: "default" | "error" | "muted";
}

const FormMessage = React.forwardRef<HTMLParagraphElement, FormMessageProps>(
  ({ className, variant = "default", children, ...props }, ref) => {
    if (!children) return null;

    const variantClasses = {
      default: "text-sm text-muted-foreground",
      error: "text-sm text-destructive",
      muted: "text-xs text-muted-foreground",
    };

    return (
      <p
        ref={ref}
        className={cn("mt-1", variantClasses[variant], className)}
        {...props}
      >
        {children}
      </p>
    );
  }
);
FormMessage.displayName = "FormMessage";

export { FormField, FormLabel, FormMessage };