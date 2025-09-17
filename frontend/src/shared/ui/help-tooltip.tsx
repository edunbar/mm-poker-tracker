import { HelpCircle } from 'lucide-react';

interface HelpTooltipProps {
  content: string;
  className?: string;
}

export function HelpTooltip({ content, className = '' }: HelpTooltipProps) {
  return (
    <div className={`group relative inline-block ${className}`}>
      <HelpCircle
        className="h-4 w-4 text-muted-foreground hover:text-foreground cursor-help"
        aria-label="Help"
      />
      <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 invisible group-hover:visible bg-popover border border-border text-popover-foreground text-xs rounded py-2 px-3 whitespace-nowrap z-50 shadow-lg">
        {content}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-2 h-2 bg-popover border-r border-b border-border rotate-45 -mt-1" />
      </div>
    </div>
  );
}