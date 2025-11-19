"use client";

import { Button, Input, Select } from "@/components/ui";
import type { SelectOption } from "@/components/ui";
import { useEffect, useId, useState } from "react";
import styles from "./FilterPanel.module.css";

const STATUS_OPTIONS: SelectOption[] = [
  { value: "all", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "fraudulent", label: "Fraudulent" },
  { value: "revoked", label: "Revoked" },
];

export interface FilterPanelProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  selectedStatus: string;
  onStatusChange: (value: string) => void;
  riskMin: string;
  onRiskMinChange: (value: string) => void;
  riskMax: string;
  onRiskMaxChange: (value: string) => void;
  onClearFilters: () => void;
  disabled?: boolean;
  riskRangeError?: string | null;
}

export function FilterPanel({
  searchTerm,
  onSearchChange,
  selectedStatus,
  onStatusChange,
  riskMin,
  onRiskMinChange,
  riskMax,
  onRiskMaxChange,
  onClearFilters,
  disabled = false,
  riskRangeError,
}: FilterPanelProps) {
  const contentId = useId();
  const [isMobile, setIsMobile] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");

    const updateMatches = (matches: boolean) => {
      setIsMobile(matches);
      setIsDrawerOpen((prev) => {
        if (matches) {
          return false;
        }

        if (!matches && !prev) {
          return true;
        }

        return prev;
      });
    };

    updateMatches(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => {
      updateMatches(event.matches);
    };

    mediaQuery.addEventListener("change", handleChange);

    return () => {
      mediaQuery.removeEventListener("change", handleChange);
    };
  }, []);

  return (
    <section className={styles.panel} aria-label="Companies filters">
      {isMobile ? (
        <header className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>Filters</h2>
          <button
            type="button"
            className={styles.toggleButton}
            onClick={() => setIsDrawerOpen((open) => !open)}
            aria-expanded={isDrawerOpen}
            aria-controls={contentId}
          >
            {isDrawerOpen ? "Hide filters" : "Show filters"}
            <span className={styles.toggleIcon} aria-hidden />
          </button>
        </header>
      ) : null}
      <div
        id={contentId}
        className={styles.panelContent}
        data-open={isDrawerOpen}
        hidden={isMobile && !isDrawerOpen}
        aria-hidden={isMobile && !isDrawerOpen}
      >
        <div className={styles.filterGrid}>
          <Input
            id="filter-search"
            label="Search by Company Name"
            placeholder="Search companies"
            value={searchTerm}
            onChange={(event) => onSearchChange(event.target.value)}
            containerClassName={styles.searchField}
            disabled={disabled}
          />
          <Select
            id="filter-status"
            label="Status"
            options={STATUS_OPTIONS}
            value={selectedStatus}
            onChange={(event) => onStatusChange(event.target.value)}
            disabled={disabled}
          />
          <Input
            id="filter-risk-min"
            label="Risk Score (Min)"
            type="number"
            inputMode="numeric"
            min={0}
            max={100}
            value={riskMin}
            onChange={(event) => onRiskMinChange(event.target.value)}
            disabled={disabled}
          />
          <Input
            id="filter-risk-max"
            label="Risk Score (Max)"
            type="number"
            inputMode="numeric"
            min={0}
            max={100}
            value={riskMax}
            onChange={(event) => onRiskMaxChange(event.target.value)}
            error={riskRangeError ?? undefined}
            disabled={disabled}
          />
        </div>
        <div className={styles.actions}>
          <Button
            variant="secondary"
            onClick={onClearFilters}
            className={styles.clearButton}
            disabled={disabled}
          >
            Clear Filters
          </Button>
        </div>
      </div>
    </section>
  );
}

export default FilterPanel;

