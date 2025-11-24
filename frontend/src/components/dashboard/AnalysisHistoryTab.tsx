"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { Button, Badge } from "@/components/ui";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { useAuth } from "@/contexts/AuthContext";
import { fetchCompanyAnalyses } from "@/lib/companies-api";
import type { CompanyAnalysis } from "@/types/company";
import { AnalysisVersionModal } from "./AnalysisVersionModal";
import styles from "./AnalysisHistoryTab.module.css";

export interface AnalysisHistoryTabProps {
  companyName: string;
  companyId?: string;
}

function formatDate(dateString: string) {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
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

function resolveStatusBadge(analysis: CompanyAnalysis) {
  const failedChecks = analysis.failed_checks ?? [];

  if (!analysis.is_complete || failedChecks.length > 0) {
    const label = !analysis.is_complete ? "Incomplete" : "Complete (Issues)";
    return { variant: "analysis-warning" as const, label };
  }

  return { variant: "analysis-complete" as const, label: "Complete" };
}

export function AnalysisHistoryTab({ companyName, companyId: propCompanyId }: AnalysisHistoryTabProps) {
  const params = useParams<{ id: string }>();
  const companyIdParam = params?.id;
  const urlCompanyId = Array.isArray(companyIdParam) ? companyIdParam[0] : companyIdParam;
  // Use prop companyId if provided (for modal), otherwise fall back to URL params (for page route)
  const companyId = propCompanyId ?? urlCompanyId;

  const { getAccessToken } = useAuth();

  const [analyses, setAnalyses] = useState<CompanyAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<CompanyAnalysis | null>(null);

  const loadAnalyses = useCallback(async () => {
    if (!companyId) {
      setAnalyses([]);
      setError("Company not found.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = await getAccessToken();

      if (!token) {
        setError("Authentication required. Please sign in again.");
        setAnalyses([]);
        return;
      }

      const response = await fetchCompanyAnalyses(companyId, token);
      const sorted = [...response].sort((a, b) => b.version - a.version);
      setAnalyses(sorted);
    } catch (err) {
      console.error("Failed to load analysis history", err);
      setError("Failed to load analysis history. Please try again.");
      setAnalyses([]);
    } finally {
      setLoading(false);
    }
  }, [companyId, getAccessToken]);

  useEffect(() => {
    void loadAnalyses();
  }, [loadAnalyses]);

  const resolvedCompanyName = useMemo(() => companyName || "Company", [companyName]);

  const handleViewReport = useCallback((analysis: CompanyAnalysis) => {
    setSelectedAnalysis(analysis);
  }, []);

  const handleCloseModal = useCallback(() => {
    setSelectedAnalysis(null);
  }, []);

  if (loading) {
    return (
      <div className={styles.stateWrapper}>
        <LoadingSkeleton rows={4} columns={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.stateWrapper}>
        <p className={styles.errorMessage}>{error}</p>
        <Button variant="secondary" onClick={() => void loadAnalyses()} className={styles.retryButton}>
          Retry
        </Button>
      </div>
    );
  }

  if (analyses.length === 0) {
    return (
      <div className={styles.stateWrapper}>
        <p className={styles.emptyMessage}>No analysis history is available yet.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Version</th>
              <th scope="col">Date</th>
              <th scope="col">Risk Score</th>
              <th scope="col">Status</th>
              <th scope="col" className={styles.actionsHeader}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((analysis) => {
              const riskVariant = getRiskVariant(analysis.risk_score);
              const statusBadge = resolveStatusBadge(analysis);
              const riskClassName =
                riskVariant === "low"
                  ? styles.riskLow
                  : riskVariant === "medium"
                  ? styles.riskMedium
                  : styles.riskHigh;

              return (
                <tr key={analysis.id}>
                  <td>
                    <span className={styles.version}>v{analysis.version}</span>
                    <span className={styles.algorithm}>Algorithm {analysis.algorithm_version}</span>
                  </td>
                  <td>{formatDate(analysis.created_at)}</td>
                  <td>
                    <span className={`${styles.riskBadge} ${riskClassName}`}>
                      {analysis.risk_score}
                    </span>
                  </td>
                  <td>
                    <Badge variant={statusBadge.variant} className={styles.statusBadge}>
                      {statusBadge.label}
                    </Badge>
                  </td>
                  <td className={styles.actionsCell}>
                    <Button
                      variant="secondary"
                      className={styles.viewButton}
                      onClick={() => handleViewReport(analysis)}
                    >
                      View Report
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <AnalysisVersionModal
        isOpen={Boolean(selectedAnalysis)}
        onClose={handleCloseModal}
        analysis={selectedAnalysis}
        companyName={resolvedCompanyName}
      />
    </div>
  );
}

export default AnalysisHistoryTab;
