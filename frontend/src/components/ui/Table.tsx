import React from "react";
import styles from "./Table.module.css";

export type SortDirection = "asc" | "desc";

export interface TableColumn<Row extends Record<string, unknown>> {
  key: keyof Row | string;
  label: string;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  width?: string;
  render?: (value: unknown, row: Row, rowIndex: number) => React.ReactNode;
  truncate?: number;
}

export interface TableProps<Row extends Record<string, unknown>> {
  caption?: string;
  columns: Array<TableColumn<Row>>;
  data: Row[];
  sortedColumn?: string;
  sortDirection?: SortDirection;
  onSort?: (key: string, direction: SortDirection) => void;
  getRowKey?: (row: Row, index: number) => React.Key;
  emptyState?: React.ReactNode;
  className?: string;
}

export interface TablePaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
  disabled?: boolean;
}

function composeClassNames(...values: Array<string | undefined | false>) {
  return values.filter(Boolean).join(" ");
}

export function Table<Row extends Record<string, unknown>>({
  caption,
  columns,
  data,
  sortedColumn,
  sortDirection = "asc",
  onSort,
  getRowKey,
  emptyState,
  className,
}: TableProps<Row>) {
  const handleHeaderClick = (column: TableColumn<Row>) => {
    if (!column.sortable || !onSort) {
      return;
    }

    const columnKey = column.key.toString();
    const isCurrentlySorted = sortedColumn === columnKey;
    const nextDirection: SortDirection = isCurrentlySorted && sortDirection === "asc" ? "desc" : "asc";

    onSort(columnKey, nextDirection);
  };

  const renderCellContent = (column: TableColumn<Row>, row: Row, rowIndex: number) => {
    if (column.render) {
      return column.render(row[column.key as keyof Row], row, rowIndex);
    }
    const value = row[column.key as keyof Row];
    if (value === null || value === undefined) {
      return "—";
    }
    return String(value);
  };

  const resolveRowKey = (row: Row, index: number) => {
    if (getRowKey) {
      return getRowKey(row, index);
    }

    if ("id" in row) {
      return String(row.id);
    }

    return index;
  };

  return (
    <div className={composeClassNames(styles.container, className)}>
      <table className={styles.table}>
        {caption ? <caption className={styles.caption}>{caption}</caption> : null}
        <thead className={styles.thead}>
          <tr>
            {columns.map((column) => {
              const columnKey = column.key.toString();
              const isSorted = sortedColumn === columnKey;
              const ariaSortValue =
                column.sortable && sortedColumn === columnKey
                  ? (sortDirection === "asc" ? "ascending" : "descending")
                  : column.sortable
                    ? "none"
                    : undefined;

              const headerContent = column.sortable && onSort ? (
                <button
                  type="button"
                  className={styles.headerButton}
                  onClick={() => handleHeaderClick(column)}
                >
                  <span>{column.label}</span>
                  <span
                    aria-hidden
                    className={composeClassNames(
                      styles.sortIcon,
                      isSorted ? styles[`sort-${sortDirection}`] : undefined,
                    )}
                  />
                  <span className={styles.srOnly}>
                    {isSorted ? `Sorted ${sortDirection === "asc" ? "ascending" : "descending"}` : "Activate to sort"}
                  </span>
                </button>
              ) : (
                <span className={styles.headerLabel}>{column.label}</span>
              );

              return (
                <th
                  key={columnKey}
                  scope="col"
                  aria-sort={ariaSortValue}
                  style={{
                    width: column.width,
                    textAlign: column.align ?? "left",
                  }}
                >
                  {headerContent}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td className={styles.emptyCell} colSpan={columns.length}>
                {emptyState ?? <p className={styles.emptyMessage}>No results found.</p>}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr key={resolveRowKey(row, rowIndex)} className={styles.row}>
                {columns.map((column) => {
                  const columnKey = column.key.toString();
                  const cellContent = renderCellContent(column, row, rowIndex);
                  const isStringContent = typeof cellContent === "string";
                  const shouldTruncate = column.truncate && isStringContent;

                  return (
                    <td
                      key={columnKey}
                      className={composeClassNames(
                        styles.cell,
                        column.align ? styles[`align-${column.align}`] : undefined,
                        shouldTruncate ? styles.truncate : undefined,
                      )}
                      style={{
                        maxWidth: shouldTruncate ? `${column.truncate}ch` : column.width,
                      }}
                      title={shouldTruncate ? (cellContent as string) : undefined}
                    >
                      {cellContent}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function TablePagination({
  currentPage,
  totalPages,
  onPageChange,
  className,
  disabled = false,
}: TablePaginationProps) {
  const handlePrevious = () => {
    if (disabled || currentPage <= 1) {
      return;
    }

    onPageChange(currentPage - 1);
  };

  const handleNext = () => {
    if (disabled || currentPage >= totalPages) {
      return;
    }

    onPageChange(currentPage + 1);
  };

  return (
    <div className={composeClassNames(styles.pagination, className)} aria-live="polite">
      <button
        type="button"
        className={styles.paginationButton}
        onClick={handlePrevious}
        disabled={disabled || currentPage <= 1}
      >
        Previous
      </button>
      <span className={styles.paginationStatus}>
        Page {totalPages === 0 ? 0 : currentPage} of {totalPages}
      </span>
      <button
        type="button"
        className={styles.paginationButton}
        onClick={handleNext}
        disabled={disabled || currentPage >= totalPages}
      >
        Next
      </button>
    </div>
  );
}

export default Table;

