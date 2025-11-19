"use client";

import { useCallback, useEffect, useMemo, useState, type MouseEvent } from "react";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { exportCompanyJson, exportCompanyPdf } from "@/lib/companies-api";
import { mapExportError } from "@/lib/export-utils";
import type { CompanyAnalysis } from "@/types/company";
import styles from "./AnalysisVersionModal.module.css";

export interface AnalysisVersionModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: CompanyAnalysis | null;
  companyName: string;
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

function getRiskClass(score: number) {
  if (score <= 30) {
    return "low";
  }
  if (score <= 69) {
    return "medium";
  }
  return "high";
}

function resolveSignalStatusClass(status: string | undefined) {
  switch (status) {
    case "ok":
      return styles.signalOk;
    case "warning":
      return styles.signalWarning;
    case "suspicious":
      return styles.signalSuspicious;
    case "mismatch":
      return styles.signalMismatch;
    default:
      return styles.signalNeutral;
  }
}

export function AnalysisVersionModal({
  isOpen,
  onClose,
  analysis,
  companyName,
}: AnalysisVersionModalProps) {
  const params = useParams<{ id: string }>();
  const companyIdParam = params?.id;
  const companyId = Array.isArray(companyIdParam) ? companyIdParam[0] : companyIdParam;

  const { getAccessToken } = useAuth();
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingJson, setIsExportingJson] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

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

  const titleId = useMemo(() => {
    if (!analysis) {
      return "analysis-version-modal-title";
    }
    return `analysis-version-modal-title-${analysis.id}`;
  }, [analysis]);

  const riskVariant = analysis ? getRiskClass(analysis.risk_score) : "medium";
  const riskClassName =
    riskVariant === "low"
      ? styles.riskLow
      : riskVariant === "medium"
      ? styles.riskMedium
      : styles.riskHigh;

  useEffect(() => {
    if (!isOpen) {
      setFeedback(null);
      setIsExportingPdf(false);
      setIsExportingJson(false);
    }
  }, [isOpen]);

  const handleBackdropClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  const handleExportPdf = useCallback(async () => {
    if (!analysis || !companyId) {
      return;
    }

    setFeedback(null);
    setIsExportingPdf(true);

    try {
      const token = await getAccessToken();

      if (!token) {
        setFeedback({ type: "error", message: "Authentication required. Please sign in again." });
        return;
      }

      const blob = await exportCompanyPdf(companyId, token, analysis.version);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${companyName.replace(/\s+/g, "_")}_v${analysis.version}_report.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(url);
      setFeedback({ type: "success", message: "PDF export downloaded." });
    } catch (error) {
      console.error("Failed to export PDF", error);
      setFeedback({ type: "error", message: mapExportError(error, "pdf") });
    } finally {
      setIsExportingPdf(false);
    }
  }, [analysis, companyId, companyName, getAccessToken]);

  const handleExportJson = useCallback(async () => {
    if (!analysis || !companyId) {
      return;
    }

    setFeedback(null);
    setIsExportingJson(true);

    try {
      const token = await getAccessToken();

      if (!token) {
        setFeedback({ type: "error", message: "Authentication required. Please sign in again." });
        return;
      }

      const data = await exportCompanyJson(companyId, token, analysis.version);
      const json = JSON.stringify(data, null, 2);
      const blob = new Blob([json], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${companyName.replace(/\s+/g, "_")}_v${analysis.version}_report.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(url);
      setFeedback({ type: "success", message: "JSON export downloaded." });
    } catch (error) {
      console.error("Failed to export JSON", error);
      setFeedback({ type: "error", message: mapExportError(error, "json") });
    } finally {
      setIsExportingJson(false);
    }
  }, [analysis, companyId, companyName, getAccessToken]);

  if (!isOpen || !analysis) {
    return null;
  }

  const submittedEntries = Object.entries(analysis.submitted_data ?? {});
  const discoveredEntries = Object.entries(analysis.discovered_data ?? {});
  const signals = analysis.signals ?? [];
  const failedChecks = analysis.failed_checks ?? [];

  return (
    <div className={styles.backdrop} onClick={handleBackdropClick}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className={styles.header}>
          <div>
            <p className={styles.company}>{companyName}</p>
            <h2 id={titleId} className={styles.title}>
              Analysis Version v{analysis.version}
            </h2>
            <p className={styles.subtitle}>
              {new Date(analysis.created_at).toLocaleString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
            <div className={styles.meta}>
              <span>Algorithm {analysis.algorithm_version}</span>
              <span>ID {analysis.id}</span>
            </div>
          </div>
          <div className={styles.headerActions}>
            <span className={`${styles.riskBadge} ${riskClassName}`}>
              Risk {analysis.risk_score}
            </span>
            <button
              type="button"
              className={styles.closeButton}
              onClick={onClose}
              aria-label="Close analysis history modal"
            >
              ×
            </button>
          </div>
        </header>

        <div className={styles.body}>
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Submitted vs Discovered Data</h3>
            <div className={styles.columns}>
              <div className={styles.column}>
                <h4 className={styles.columnTitle}>Submitted Data</h4>
                {submittedEntries.length === 0 ? (
                  <p className={styles.emptyData}>No submitted data recorded.</p>
                ) : (
                  <ul className={styles.dataList}>
                    {submittedEntries.map(([key, value]) => (
                      <li key={key}>
                        <span className={styles.dataLabel}>{formatLabel(key)}</span>
                        <span className={styles.dataValue}>{formatValue(value)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className={styles.column}>
                <h4 className={styles.columnTitle}>Discovered Data</h4>
                {discoveredEntries.length === 0 ? (
                  <p className={styles.emptyData}>No discovered data recorded.</p>
                ) : (
                  <ul className={styles.dataList}>
                    {discoveredEntries.map(([key, value]) => (
                      <li key={key}>
                        <span className={styles.dataLabel}>{formatLabel(key)}</span>
                        <span className={styles.dataValue}>{formatValue(value)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </section>

          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Verification Signals</h3>
            {signals.length === 0 ? (
              <p className={styles.emptyData}>No signals were recorded for this analysis.</p>
            ) : (
              <table className={styles.signalsTable}>
                <thead>
                  <tr>
                    <th scope="col">Field</th>
                    <th scope="col">Value</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((signal, index) => (
                    <tr key={`${signal.field}-${index}`}>
                      <td>{formatLabel(signal.field ?? `Field ${index + 1}`)}</td>
                      <td>
                        <span className={styles.signalValue}>{formatValue(signal.value)}</span>
                      </td>
                      <td>
                        <span className={`${styles.signalStatus} ${resolveSignalStatusClass(signal.status)}`}>
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
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>LLM Summary</h3>
              <div className={styles.summaryBox}>
                <p>{analysis.llm_summary}</p>
              </div>
            </section>
          ) : null}

          {analysis.llm_details ? (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>LLM Details</h3>
              <div className={styles.detailsBox}>
                <pre>{analysis.llm_details}</pre>
              </div>
            </section>
          ) : null}

          {failedChecks.length > 0 ? (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Failed Checks</h3>
              <ul className={styles.failedChecks}>
                {failedChecks.map((check) => (
                  <li key={check}>{formatLabel(check)}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        <footer className={styles.footer}>
          {feedback ? (
            <div
              className={`${styles.feedback} ${
                feedback.type === "success" ? styles.feedbackSuccess : styles.feedbackError
              }`}
              role="status"
              aria-live="polite"
            >
              {feedback.message}
            </div>
          ) : null}

          <div className={styles.footerActions}>
            <Button
              variant="secondary"
              onClick={() => void handleExportPdf()}
              className={styles.footerButton}
              disabled={isExportingPdf || isExportingJson}
            >
              {isExportingPdf ? "Exporting PDF…" : "Export PDF"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => void handleExportJson()}
              className={styles.footerButton}
              disabled={isExportingPdf || isExportingJson}
            >
              {isExportingJson ? "Exporting JSON…" : "Export JSON"}
            </Button>
            <Button onClick={onClose} className={styles.footerButton}>
              Close
            </Button>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default AnalysisVersionModal;

