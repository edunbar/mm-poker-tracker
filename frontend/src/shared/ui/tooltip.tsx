import React from "react";
import { cn } from "../../lib/utils";

interface TooltipContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const TooltipContext = React.createContext<TooltipContextValue | null>(null);

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export function Tooltip({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);

  return (
    <TooltipContext.Provider value={{ open, setOpen }}>
      <div className="relative inline-block">
        {children}
      </div>
    </TooltipContext.Provider>
  );
}

export const TooltipTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    asChild?: boolean;
  }
>(({ className, children, asChild, ...props }, ref) => {
  const context = React.useContext(TooltipContext);

  if (!context) {
    throw new Error("TooltipTrigger must be used within Tooltip");
  }

  const handleMouseEnter = () => context.setOpen(true);
  const handleMouseLeave = () => context.setOpen(false);

  if (asChild) {
    return React.cloneElement(
      children as React.ReactElement,
      {
        onMouseEnter: handleMouseEnter,
        onMouseLeave: handleMouseLeave,
        ref,
      }
    );
  }

  return (
    <button
      ref={ref}
      className={cn("cursor-pointer", className)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      {...props}
    >
      {children}
    </button>
  );
});

TooltipTrigger.displayName = "TooltipTrigger";

export const TooltipContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  const context = React.useContext(TooltipContext);

  if (!context) {
    throw new Error("TooltipContent must be used within Tooltip");
  }

  if (!context.open) return null;

  return (
    <div
      ref={ref}
      className={cn(
        "absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50 w-64 rounded-md border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95",
        className
      )}
      {...props}
    >
      {children}
      <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-2 h-2 bg-popover border-r border-b border-border rotate-45 -mt-1" />
    </div>
  );
});

TooltipContent.displayName = "TooltipContent";