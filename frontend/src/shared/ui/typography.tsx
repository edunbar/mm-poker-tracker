import { cva, type VariantProps } from "class-variance-authority";
import React from "react";
import { cn } from "../../lib/utils";

const headingVariants = cva(
  "font-sans text-foreground",
  {
    variants: {
      variant: {
        h1: "text-4xl font-bold tracking-tight",
        h2: "text-3xl font-bold tracking-tight",
        h3: "text-2xl font-semibold tracking-tight",
        h4: "text-xl font-semibold tracking-tight",
        h5: "text-lg font-semibold",
        h6: "text-base font-semibold",
      },
      colorStyle: {
        default: "text-foreground",
        muted: "text-muted-foreground",
        primary: "text-primary",
        destructive: "text-destructive",
        success: "text-success",
        warning: "text-warning",
      },
    },
    defaultVariants: {
      variant: "h1",
      colorStyle: "default",
    },
  }
);

const textVariants = cva(
  "font-sans",
  {
    variants: {
      variant: {
        body: "text-base leading-relaxed",
        bodyLarge: "text-lg leading-relaxed",
        bodySmall: "text-sm leading-normal",
        caption: "text-xs leading-normal",
        lead: "text-xl leading-relaxed font-light",
        subtle: "text-sm text-muted-foreground",
      },
      colorStyle: {
        default: "text-foreground",
        muted: "text-muted-foreground",
        primary: "text-primary",
        destructive: "text-destructive",
        success: "text-success",
        warning: "text-warning",
      },
      weight: {
        light: "font-light",
        normal: "font-normal",
        medium: "font-medium",
        semibold: "font-semibold",
        bold: "font-bold",
      },
    },
    defaultVariants: {
      variant: "body",
      colorStyle: "default",
      weight: "normal",
    },
  }
);

const codeVariants = cva(
  "font-mono",
  {
    variants: {
      variant: {
        inline: "text-sm bg-muted px-1.5 py-0.5 rounded-sm",
        block: "text-sm bg-muted p-4 rounded-md overflow-x-auto",
      },
      colorStyle: {
        default: "text-foreground",
        muted: "text-muted-foreground",
        primary: "text-primary",
      },
    },
    defaultVariants: {
      variant: "inline",
      colorStyle: "default",
    },
  }
);

export interface HeadingProps
  extends Omit<React.HTMLAttributes<HTMLHeadingElement>, 'color'>,
    VariantProps<typeof headingVariants> {
  as?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
  color?: "default" | "muted" | "primary" | "destructive" | "success" | "warning";
}

export interface TextProps
  extends Omit<React.HTMLAttributes<HTMLElement>, 'color'>,
    VariantProps<typeof textVariants> {
  as?: "p" | "span" | "div" | "label" | "li" | "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "th" | "td";
  color?: "default" | "muted" | "primary" | "destructive" | "success" | "warning";
  htmlFor?: string;
}

export interface CodeProps
  extends Omit<React.HTMLAttributes<HTMLElement>, 'color'>,
    VariantProps<typeof codeVariants> {
  as?: "code" | "pre";
  color?: "default" | "muted" | "primary";
}

const Heading = React.forwardRef<HTMLHeadingElement, HeadingProps>(
  ({ className, variant, color, colorStyle, as, ...props }, ref) => {
    const Comp = as || variant || "h1";
    const actualColorStyle = color || colorStyle;
    return (
      <Comp
        className={cn(headingVariants({ variant, colorStyle: actualColorStyle, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Heading.displayName = "Heading";

const Text = React.forwardRef<HTMLElement, TextProps>(
  ({ className, variant, color, colorStyle, weight, as = "p", htmlFor, ...props }, ref) => {
    const Comp: React.ElementType = as;
    const actualColorStyle = color || colorStyle;
    const labelProps = as === "label" && htmlFor ? { htmlFor } : {};
    return (
      <Comp
        className={cn(textVariants({ variant, colorStyle: actualColorStyle, weight, className }))}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ref={ref as any}
        {...labelProps}
        {...props}
      />
    );
  }
);
Text.displayName = "Text";

const Code = React.forwardRef<HTMLElement, CodeProps>(
  ({ className, variant, color, colorStyle, as = "code", ...props }, ref) => {
    const Comp: React.ElementType = as;
    const actualColorStyle = color || colorStyle;
    return (
      <Comp
        className={cn(codeVariants({ variant, colorStyle: actualColorStyle, className }))}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ref={ref as any}
        {...props}
      />
    );
  }
);
Code.displayName = "Code";

export { Heading, Text, Code, headingVariants, textVariants, codeVariants };