import { HelpCircle } from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';

interface HelpTooltipProps {
  content: string;
  className?: string;
  position?: 'above' | 'below';
}

export function HelpTooltip({ content, className = '', position = 'above' }: HelpTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback(() => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();

      setTooltipPosition({
        top: position === 'below'
          ? rect.bottom + 8
          : rect.top - 32,
        left: rect.left + rect.width / 2,
      });
    }
  }, [position]);

  useEffect(() => {
    if (isVisible) {
      updatePosition();
      const handleScroll = () => updatePosition();
      const handleResize = () => updatePosition();

      window.addEventListener('scroll', handleScroll, true);
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('scroll', handleScroll, true);
        window.removeEventListener('resize', handleResize);
      };
    }
    return undefined;
  }, [isVisible, position, updatePosition]);

  const tooltipElement = isVisible && (
    <div
      className="fixed bg-popover border border-border text-popover-foreground text-xs rounded py-2 px-3 whitespace-nowrap shadow-lg transform -translate-x-1/2"
      style={{
        top: tooltipPosition.top,
        left: tooltipPosition.left,
        zIndex: 99999,
      }}
    >
      {content}
      <div
        className={`absolute w-2 h-2 bg-popover border rotate-45 ${
          position === 'below'
            ? 'border-l border-t border-border -top-1 left-1/2 transform -translate-x-1/2'
            : 'border-r border-b border-border -bottom-1 left-1/2 transform -translate-x-1/2'
        }`}
      />
    </div>
  );

  return (
    <>
      <div
        ref={triggerRef}
        className={`inline-block cursor-help ${className}`}
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
      >
        <HelpCircle
          className="h-4 w-4 text-muted-foreground hover:text-foreground"
          aria-label="Help"
        />
      </div>
      {tooltipElement && createPortal(tooltipElement, document.body)}
    </>
  );
}