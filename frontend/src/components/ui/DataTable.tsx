import React from 'react';
import { ChevronUp, ChevronDown, MoreHorizontal, ArrowUpDown } from 'lucide-react';
import { cn } from '../../lib/utils';

// Types for the data table
export interface Column<T> {
  id: string;
  header: string;
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

interface DataTableProps<T> {
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
}

// Airtable-inspired data table with enhanced sorting and selection
export function DataTable<T>({
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
}: DataTableProps<T>) {
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
    <div className={cn("w-full overflow-hidden rounded-lg border border-border bg-card", className)}>
      <div className="overflow-x-auto">
        <table className="w-full table-airtable">
          <thead className={cn(stickyHeader && "sticky top-0 z-10")}>
            <tr>
              {onRowSelect && (
                <th className="w-12">
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
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={column.id}
                  className={cn(
                    column.className,
                    column.width && `w-[${column.width}]`,
                    column.align === 'center' && 'text-center',
                    column.align === 'right' && 'text-right',
                    column.sortable && 'cursor-pointer select-none group hover:bg-[hsl(var(--table-row-hover))]'
                  )}
                  style={column.width ? { width: column.width } : undefined}
                  onClick={() => column.sortable && handleSort(column.id)}
                >
                  <div className="flex items-center">
                    <span>{column.header}</span>
                    {column.sortable && getSortIcon(column.id)}
                  </div>
                </th>
              ))}
              <th className="w-12">
                <MoreHorizontal className="h-4 w-4 opacity-0" />
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => (
              <tr
                key={index}
                className={cn(
                  "transition-colors",
                  selectedRows.has(index) && "selected",
                  onRowClick && "cursor-pointer"
                )}
                onClick={() => onRowClick?.(item, index)}
              >
                {onRowSelect && (
                  <td>
                    <input
                      type="checkbox"
                      className="rounded border-border"
                      checked={selectedRows.has(index)}
                      onChange={(e) => {
                        e.stopPropagation();
                        onRowSelect(index, e.target.checked);
                      }}
                    />
                  </td>
                )}
                {columns.map((column) => (
                  <td
                    key={column.id}
                    className={cn(
                      column.className,
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right'
                    )}
                  >
                    {getCellValue(item, column)}
                  </td>
                ))}
                <td>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // Row actions menu would go here
                    }}
                    className="p-1 rounded hover:bg-muted opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Table pagination component
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (itemsPerPage: number) => void;
}

export function TablePagination({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
}: PaginationProps) {
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  return (
    <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-card">
      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
        <div className="flex items-center space-x-2">
          <span>Show</span>
          <select
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className="rounded border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span>entries</span>
        </div>
        <div>
          Showing {startItem} to {endItem} of {totalItems} entries
        </div>
      </div>
      
      <div className="flex items-center space-x-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-3 py-1 text-sm border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        
        {/* Page numbers */}
        <div className="flex space-x-1">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const page = i + Math.max(1, currentPage - 2);
            if (page > totalPages) return null;
            
            return (
              <button
                key={page}
                onClick={() => onPageChange(page)}
                className={cn(
                  "px-3 py-1 text-sm border rounded",
                  page === currentPage
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border hover:bg-muted"
                )}
              >
                {page}
              </button>
            );
          })}
        </div>
        
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-3 py-1 text-sm border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  );
}