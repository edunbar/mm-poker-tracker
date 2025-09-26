import { ChevronUp, ChevronDown, ArrowUpDown } from 'lucide-react';
import React from 'react';
import { cn } from '../../lib/utils';
import { Pagination } from './pagination';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './table';

// Types for the enhanced data table
export interface Column<T> {
  id: string;
  header: string | React.ReactNode;
  accessor: keyof T | ((item: T) => React.ReactNode);
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export interface SortConfig {
  key: string;
  direction: 'asc' | 'desc';
}

interface EnhancedDataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  sortConfig?: SortConfig;
  onSort?: (column: string) => void;
  onRowClick?: (item: T, index: number) => void;
  selectedRows?: Set<number>;
  onRowSelect?: (index: number, selected: boolean) => void;
  className?: string;
  emptyState?: React.ReactNode;
  loading?: boolean;
  stickyHeader?: boolean;
  // Pagination props
  currentPage?: number;
  totalPages?: number;
  totalItems?: number;
  itemsPerPage?: number;
  onPageChange?: (page: number) => void;
  onItemsPerPageChange?: (itemsPerPage: number) => void;
  showPagination?: boolean;
  // Additional styling options
  variant?: 'default' | 'compact' | 'spacious';
  striped?: boolean;
  bordered?: boolean;
}

export function EnhancedDataTable<T>({
  data,
  columns,
  sortConfig,
  onSort,
  onRowClick,
  selectedRows = new Set(),
  onRowSelect,
  className,
  emptyState,
  loading = false,
  stickyHeader = false,
  currentPage = 1,
  totalPages = 1,
  totalItems = 0,
  itemsPerPage = 10,
  onPageChange,
  onItemsPerPageChange: _onItemsPerPageChange,
  showPagination = false,
  variant = 'default',
  striped = false,
  bordered = true,
}: EnhancedDataTableProps<T>) {
  const handleSort = (columnId: string) => {
    if (onSort) {
      onSort(columnId);
    }
  };

  const getSortIcon = (columnId: string) => {
    if (!sortConfig || sortConfig.key !== columnId) {
      return <ArrowUpDown className="ml-2 h-4 w-4 opacity-0 group-hover:opacity-50" />;
    }
    return sortConfig.direction === 'asc'
      ? <ChevronUp className="ml-2 h-4 w-4 opacity-70" />
      : <ChevronDown className="ml-2 h-4 w-4 opacity-70" />;
  };

  const getCellValue = (item: T, column: Column<T>) => {
    if (typeof column.accessor === 'function') {
      return column.accessor(item);
    }
    return item[column.accessor] as React.ReactNode;
  };

  const getVariantClasses = () => {
    switch (variant) {
      case 'compact':
        return {
          header: 'h-8 px-2 text-xs',
          cell: 'p-2 text-sm',
        };
      case 'spacious':
        return {
          header: 'h-12 px-6 text-sm',
          cell: 'p-6 text-base',
        };
      default:
        return {
          header: 'h-10 px-3 text-xs',
          cell: 'p-3 text-sm',
        };
    }
  };

  const variantClasses = getVariantClasses();

  if (loading) {
    return (
      <div className="w-full">
        <div className="animate-pulse">
          <div className="bg-muted h-12 rounded-t-lg mb-2" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-muted/50 h-12 mb-1 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!data.length && emptyState) {
    return (
      <div className="w-full">
        <div className="rounded-lg border border-border bg-card">
          <div className="p-8 text-center">
            {emptyState}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      <div className={cn(
        "w-full overflow-hidden rounded-lg bg-card",
        bordered && "border border-border",
        className
      )}>
        <div className="overflow-x-auto">
          <Table className="w-full">
            <TableHeader className={cn(stickyHeader && "sticky top-0 z-10")}>
              <TableRow className={cn(striped && "bg-muted/50")}>
                {onRowSelect && (
                  <TableHead className="w-12">
                    <input
                      type="checkbox"
                      className="rounded border-border"
                      checked={data.length > 0 && selectedRows.size === data.length}
                      onChange={(e) => {
                        data.forEach((_, index) => {
                          onRowSelect(index, e.target.checked);
                        });
                      }}
                    />
                  </TableHead>
                )}
                {columns.map((column) => (
                  <TableHead
                    key={column.id}
                    className={cn(
                      variantClasses.header,
                      "font-medium text-muted-foreground uppercase tracking-wider",
                      column.className,
                      column.width && `w-[${column.width}]`,
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right',
                      column.sortable && 'cursor-pointer select-none group'
                    )}
                    style={column.width ? { width: column.width } : undefined}
                    onClick={() => column.sortable && handleSort(column.id)}
                  >
                    <div className="flex items-center">
                      <span>{column.header}</span>
                      {column.sortable && getSortIcon(column.id)}
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item, index) => (
                <TableRow
                  key={index}
                  className={cn(
                    "transition-colors",
                    selectedRows.has(index) && "bg-accent/50",
                    onRowClick && "cursor-pointer",
                    striped && index % 2 === 1 && "bg-muted/25"
                  )}
                  onClick={() => onRowClick?.(item, index)}
                >
                  {onRowSelect && (
                    <TableCell>
                      <input
                        type="checkbox"
                        className="rounded border-border"
                        checked={selectedRows.has(index)}
                        onChange={(e) => {
                          e.stopPropagation();
                          onRowSelect(index, e.target.checked);
                        }}
                      />
                    </TableCell>
                  )}
                  {columns.map((column) => (
                    <TableCell
                      key={column.id}
                      className={cn(
                        variantClasses.cell,
                        "align-middle text-foreground",
                        column.className,
                        column.align === 'center' && 'text-center',
                        column.align === 'right' && 'text-right'
                      )}
                    >
                      {getCellValue(item, column)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {showPagination && onPageChange && totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={onPageChange}
          itemsPerPage={itemsPerPage}
          totalItems={totalItems}
          className="justify-end"
        />
      )}
    </div>
  );
}

// Utility function to create column definitions
export function createColumn<T>(
  id: string,
  header: string | React.ReactNode,
  accessor: keyof T | ((item: T) => React.ReactNode),
  options?: Partial<Column<T>>
): Column<T> {
  return {
    id,
    header,
    accessor,
    ...options,
  };
}

// Hook for managing table state
export function useTableState<T>(
  data: T[],
  defaultSortKey?: string,
  defaultSortDirection: 'asc' | 'desc' = 'asc'
) {
  const [sortConfig, setSortConfig] = React.useState<SortConfig | null>(
    defaultSortKey ? { key: defaultSortKey, direction: defaultSortDirection } : null
  );
  const [selectedRows, setSelectedRows] = React.useState<Set<number>>(new Set());

  const handleSort = (columnId: string) => {
    setSortConfig(prevConfig => {
      if (!prevConfig || prevConfig.key !== columnId) {
        return { key: columnId, direction: 'asc' };
      }
      if (prevConfig.direction === 'asc') {
        return { key: columnId, direction: 'desc' };
      }
      return null; // Remove sorting
    });
  };

  const handleRowSelect = (index: number, selected: boolean) => {
    setSelectedRows(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(index);
      } else {
        newSet.delete(index);
      }
      return newSet;
    });
  };

  const sortedData = React.useMemo(() => {
    if (!sortConfig) return data;

    return [...data].sort((a, b) => {
      const aValue = (a as Record<string, unknown>)[sortConfig.key];
      const bValue = (b as Record<string, unknown>)[sortConfig.key];

      if ((aValue as string | number) < (bValue as string | number)) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if ((aValue as string | number) > (bValue as string | number)) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [data, sortConfig]);

  return {
    sortConfig,
    selectedRows,
    sortedData,
    handleSort,
    handleRowSelect,
    clearSelection: () => setSelectedRows(new Set()),
  };
}