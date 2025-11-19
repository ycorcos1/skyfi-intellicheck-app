"use client";

import { useCallback, useEffect, useMemo, type MouseEvent } from "react";

import { Button } from "@/components/ui";
import { Badge } from "@/components/ui/Badge";
import type { Company, CompanyAnalysis } from "@/types/company";
import styles from "./ExportPreviewModal.module.css";

export interface ExportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  company: Company;
  analysis: CompanyAnalysis;
  onExportPdf: () => void;
  onExportJson: () => void;
  isExportingPdf?: boolean;
  isExportingJson?: boolean;
}

function formatLabel(key: string) {
  return key
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatValue(value: unknown) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "N/A";
  }

  if (typeof value === "object") {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  return String(value);
}

function getRiskVariant(score: number) {
  if (score <= 30) {
    return "low";
  }

  if (score <= 69) {
    return "medium";
  }

  return "high";
}

function formatStatus(status: Company["status"]) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function ExportPreviewModal({
  isOpen,
  onClose,
  company,
  analysis,
  onExportPdf,
  onExportJson,
  isExportingPdf = false,
  isExportingJson = false,
}: ExportPreviewModalProps) {
  const riskVariant = getRiskVariant(analysis.risk_score);
  const riskClassName =
    riskVariant === "low"
      ? styles.riskLow
      : riskVariant === "medium"
      ? styles.riskMedium
      : styles.riskHigh;

  const submittedEntries = useMemo(() => Object.entries(analysis.submitted_data ?? {}), [analysis.submitted_data]);
  const discoveredEntries = useMemo(() => Object.entries(analysis.discovered_data ?? {}), [analysis.discovered_data]);
  const signals = analysis.signals ?? [];

  const modalTitleId = useMemo(() => `export-preview-${analysis.id}`, [analysis.id]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    if (!isOpen) {
      return undefined;
    }

    document.addEventListener("keydown", handleKeyDown);

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, onClose]);

  const handleBackdropClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  const analysisDate = useMemo(
    () =>
      new Date(analysis.created_at).toLocaleString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }),
    [analysis.created_at],
  );

  if (!isOpen) {
    return null;
  }

  return (
    <div className={styles.overlay} onClick={handleBackdropClick}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={modalTitleId}
      >
        <header className={styles.header}>
          <div>
            <h2 id={modalTitleId} className={styles.title}>
              Report Preview
            </h2>
            <p className={styles.subtitle}>Review the verification summary before exporting.</p>
          </div>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close export preview"
          >
            ×
          </button>
        </header>

        <div className={styles.body}>
          <section className={styles.coverSection}>
            <p className={styles.brand}>SkyFi IntelliCheck</p>
            <h3 className={styles.companyName}>{company.name}</h3>
            <p className={styles.companyDomain}>{company.domain}</p>

            <div className={styles.statusRow}>
              <Badge variant={company.status} className={styles.statusBadge}>
                {formatStatus(company.status)}
              </Badge>
              <span className={`${styles.riskBadge} ${riskClassName}`}>
                Risk Score {analysis.risk_score}
              </span>
            </div>

            <div className={styles.coverMeta}>
              <span>Version v{analysis.version}</span>
              <span>Algorithm {analysis.algorithm_version}</span>
              <span>{analysisDate}</span>
            </div>
          </section>

          <section className={styles.dataSection}>
            <h4 className={styles.sectionTitle}>Submitted vs Discovered</h4>
            <div className={styles.columns}>
              <div className={styles.column}>
                <h5 className={styles.columnTitle}>Submitted Data</h5>
                {submittedEntries.length === 0 ? (
                  <p className={styles.emptyState}>No submitted data recorded.</p>
                ) : (
                  <dl className={styles.dataList}>
                    {submittedEntries.map(([key, value]) => (
                      <div key={key} className={styles.dataItem}>
                        <dt>{formatLabel(key)}</dt>
                        <dd>{formatValue(value)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </div>

              <div className={styles.column}>
                <h5 className={styles.columnTitle}>Discovered Data</h5>
                {discoveredEntries.length === 0 ? (
                  <p className={styles.emptyState}>No discovered data recorded.</p>
                ) : (
                  <dl className={styles.dataList}>
                    {discoveredEntries.map(([key, value]) => (
                      <div key={key} className={styles.dataItem}>
                        <dt>{formatLabel(key)}</dt>
                        <dd>{formatValue(value)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </div>
            </div>
          </section>

          <section className={styles.signalsSection}>
            <h4 className={styles.sectionTitle}>Verification Signals</h4>
            {signals.length === 0 ? (
              <p className={styles.emptyState}>No signals recorded for this analysis.</p>
            ) : (
              <table className={styles.signalsTable}>
                <thead>
                  <tr>
                    <th scope="col">Signal</th>
                    <th scope="col">Value</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((signal, index) => (
                    <tr key={`${signal.field}-${index}`}>
                      <td>{formatLabel(signal.field ?? `Field ${index + 1}`)}</td>
                      <td>{formatValue(signal.value)}</td>
                      <td>
                        <span className={`${styles.signalStatus} ${styles[signal.status ?? "unknown"] ?? styles.signalNeutral}`}>
                          {signal.status ?? "unknown"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {analysis.llm_summary ? (
            <section className={styles.summarySection}>
              <h4 className={styles.sectionTitle}>AI Summary</h4>
              <div className={styles.summaryBox}>
                <p>{analysis.llm_summary}</p>
              </div>
            </section>
          ) : null}
        </div>

        <footer className={styles.footer}>
          <div className={styles.footerActions}>
            <Button
              variant="secondary"
              onClick={onExportJson}
              disabled={isExportingPdf || isExportingJson}
            >
              {isExportingJson ? "Exporting JSON…" : "Export JSON"}
            </Button>
            <Button onClick={onExportPdf} disabled={isExportingPdf || isExportingJson}>
              {isExportingPdf ? "Exporting PDF…" : "Export PDF"}
            </Button>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default ExportPreviewModal;

