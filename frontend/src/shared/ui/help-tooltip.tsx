import React from 'react';
import { HelpCircle } from 'lucide-react';

interface HelpTooltipProps {
  content: string;
  className?: string;
}

export function HelpTooltip({ content, className = '' }: HelpTooltipProps) {
  return (
    <div className={`group relative inline-block ${className}`}>
      <HelpCircle 
        className="h-4 w-4 text-gray-400 hover:text-gray-600 cursor-help" 
        aria-label="Help"
      />
      <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 invisible group-hover:visible bg-gray-900 text-white text-xs rounded py-2 px-3 whitespace-nowrap z-50 shadow-lg">
        {content}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45 -mt-1"></div>
      </div>
    </div>
  );
}