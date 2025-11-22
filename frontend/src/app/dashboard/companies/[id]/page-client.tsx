"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ProtectedLayout from "@/components/layout/ProtectedLayout";
import {
  AnalysisHistoryTab,
  CompanyHeader,
  CompanyTabs,
  DocumentsTab,
  NotesTab,
  OverviewTab,
  type CompanyTabKey,
} from "@/components/dashboard";
import { ExportPreviewModal } from "@/components/dashboard/ExportPreviewModal";
import { Button } from "@/components/ui";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { useAuth } from "@/contexts/AuthContext";
import {
  exportCompanyJson,
  exportCompanyPdf,
  fetchAnalysisStatus,
  fetchCompanyDetail,
  flagCompanyFraudulent,
  markCompanyReviewComplete,
  reanalyzeCompany,
  revokeCompanyApproval,
} from "@/lib/companies-api";
import { mapExportError } from "@/lib/export-utils";
import type { AnalysisStatusResponse, Company, CompanyDetail } from "@/types/company";
import styles from "./page.module.css";

const POLLING_INTERVAL_MS = 5_000;
const BANNER_DISMISS_MS = 6_000;

type ActionKey =
  | "rerun"
  | "retryFailed"
  | "flag"
  | "revoke"
  | "review"
  | "exportPdf"
  | "exportJson"
  | "preview";

interface BannerState {
  type: "success" | "error";
  message: string;
}

interface ActionItem {
  key: ActionKey;
  label: string;
  loadingLabel?: string;
  variant?: "primary" | "secondary";
  className?: string;
  disabled?: boolean;
  onClick: () => void;
}

function createExportFilename(name: string | undefined, extension: "pdf" | "json") {
  const slug = (name ?? "company")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  const safeSlug = slug.length > 0 ? slug : "company";
  return `${safeSlug}-intellicheck.${extension}`;
}

function isAnalyzingStatus(status: Company["analysis_status"] | undefined) {
  return status === "pending" || status === "in_progress";
}

export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const companyIdParam = params?.id;
  const companyId = Array.isArray(companyIdParam) ? companyIdParam[0] : companyIdParam;

  const { getAccessToken, isAuthenticated } = useAuth();
  
  // Prevent any redirects - this page should always render even if there are errors
  useEffect(() => {
    console.log("CompanyDetailPage: Mounted", { 
      companyId, 
      isAuthenticated,
      params,
      pathname: typeof window !== "undefined" ? window.location.pathname : "N/A"
    });
    return () => {
      console.log("CompanyDetailPage: Unmounting", { companyId });
    };
  }, [companyId, isAuthenticated, params]);
  
  // Log when companyId changes
  useEffect(() => {
    if (companyId) {
      console.log("CompanyDetailPage: companyId available", { companyId });
    } else {
      console.warn("CompanyDetailPage: companyId is missing", { params, companyIdParam });
    }
  }, [companyId, params, companyIdParam]);

  const [activeTab, setActiveTab] = useState<CompanyTabKey>("overview");
  const [detail, setDetail] = useState<CompanyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<BannerState | null>(null);
  const [actionLoading, setActionLoading] = useState<ActionKey | null>(null);
  const [statusUpdate, setStatusUpdate] = useState<AnalysisStatusResponse | null>(null);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const loadDetail = useCallback(
    async ({ initial = false }: { initial?: boolean } = {}) => {
      // Validate companyId - it should be a non-empty string
      if (!companyId || typeof companyId !== "string" || companyId.trim() === "") {
        if (initial) {
          setError("Company ID is required");
          setLoading(false);
        }
        return;
      }

      try {
        if (initial) {
          setLoading(true);
          setError(null);
        }

        const token = await getAccessToken();
        
        if (!token) {
          console.error("CompanyDetailPage: No access token available");
          setError("Authentication required. Please sign in again.");
          if (initial) {
            setLoading(false);
          }
          return;
        }

        console.log("CompanyDetailPage: Loading company detail", { companyId, hasToken: !!token });
        const data = await fetchCompanyDetail(companyId, token);
        console.log("CompanyDetailPage: Company detail loaded successfully", { 
          companyName: data.name,
          status: data.status,
          analysisStatus: data.analysis_status 
        });
        
        setDetail(data);

        if (data.analysis_status === "in_progress" || data.analysis_status === "pending") {
          if (!pollingIntervalRef.current) {
            pollingIntervalRef.current = setInterval(() => {
              void loadDetail({ initial: false });
            }, POLLING_INTERVAL_MS);
          }
        } else {
          stopPolling();
        }
      } catch (err) {
        console.error("CompanyDetailPage: Failed to load company detail", {
          companyId,
          error: err,
          errorType: err instanceof Error ? err.constructor.name : typeof err,
          errorMessage: err instanceof Error ? err.message : String(err),
          isApiError: err instanceof Error && "statusCode" in err,
          statusCode: err instanceof Error && "statusCode" in err ? (err as { statusCode: number }).statusCode : undefined,
        });
        
        // Handle 401 - show error message instead of redirecting immediately
        // This prevents the page from redirecting back to dashboard
        // ProtectedLayout will handle auth redirects separately if needed
        if (err instanceof Error && "statusCode" in err && (err as { statusCode: number }).statusCode === 401) {
          console.warn("CompanyDetailPage: 401 Unauthorized - showing error instead of redirecting");
          setError("Authentication failed. Please refresh the page or sign in again.");
          if (initial) {
            setLoading(false);
          }
          return;
        }
        
        const message = err instanceof Error ? err.message : "Failed to load company details";
        setError(message);
        if (initial) {
          setLoading(false);
        }
      } finally {
        if (initial) {
          setLoading(false);
        }
      }
    },
    [companyId, getAccessToken, stopPolling],
  );

  useEffect(() => {
    void loadDetail({ initial: true });

    return () => {
      stopPolling();
    };
  }, [loadDetail, stopPolling]);

  const checkAnalysisStatus = useCallback(async () => {
    if (!companyId) {
      return;
    }

    try {
      const token = await getAccessToken();
      const status = await fetchAnalysisStatus(companyId, token);
      setStatusUpdate(status);

      if (status.status === "in_progress" || status.status === "pending") {
        if (!pollingIntervalRef.current) {
          pollingIntervalRef.current = setInterval(() => {
            void checkAnalysisStatus();
          }, POLLING_INTERVAL_MS);
        }
      } else {
        stopPolling();
        void loadDetail({ initial: false });
      }
    } catch (err) {
      console.error("Failed to check analysis status:", err);
    }
  }, [companyId, getAccessToken, loadDetail, stopPolling]);

  const handleRerun = useCallback(async () => {
    if (!companyId) {
      return;
    }

    setActionLoading("rerun");
    try {
      const token = await getAccessToken();
      await reanalyzeCompany(companyId, false, token);
      setBanner({ type: "success", message: "Reanalysis started successfully." });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
      void checkAnalysisStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start reanalysis";
      setBanner({ type: "error", message });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } finally {
      setActionLoading(null);
    }
  }, [companyId, getAccessToken, checkAnalysisStatus]);

  const handleRetryFailed = useCallback(async () => {
    if (!companyId) {
      return;
    }

    setActionLoading("retryFailed");
    try {
      const token = await getAccessToken();
      await reanalyzeCompany(companyId, true, token);
      setBanner({ type: "success", message: "Retry started successfully." });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
      void checkAnalysisStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to retry failed checks";
      setBanner({ type: "error", message });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } finally {
      setActionLoading(null);
    }
  }, [companyId, getAccessToken, checkAnalysisStatus]);

  const handleFlagFraudulent = useCallback(async () => {
    if (!companyId) {
      return;
    }

    setActionLoading("flag");
    try {
      const token = await getAccessToken();
      await flagCompanyFraudulent(companyId, token);
      setBanner({ type: "success", message: "Company flagged as fraudulent." });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
      void loadDetail({ initial: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to flag company";
      setBanner({ type: "error", message });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } finally {
      setActionLoading(null);
    }
  }, [companyId, getAccessToken, loadDetail]);

  const handleRevokeApproval = useCallback(async () => {
    if (!companyId) {
      return;
    }

    setActionLoading("revoke");
    try {
      const token = await getAccessToken();
      await revokeCompanyApproval(companyId, token);
      setBanner({ type: "success", message: "Company approval revoked." });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
      void loadDetail({ initial: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to revoke approval";
      setBanner({ type: "error", message });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } finally {
      setActionLoading(null);
    }
  }, [companyId, getAccessToken, loadDetail]);

  const handleReviewComplete = useCallback(async () => {
    if (!companyId) {
      return;
    }

    setActionLoading("review");
    try {
      const token = await getAccessToken();
      await markCompanyReviewComplete(companyId, token);
      setBanner({ type: "success", message: "Company marked as review complete." });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
      void loadDetail({ initial: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to mark review complete";
      setBanner({ type: "error", message });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } finally {
      setActionLoading(null);
    }
  }, [companyId, getAccessToken, loadDetail]);

  const handleExportPdf = useCallback(async () => {
    if (!companyId || !detail?.name) {
      return;
    }

    setActionLoading("exportPdf");
    try {
      const token = await getAccessToken();
      const blob = await exportCompanyPdf(companyId, token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = createExportFilename(detail.name, "pdf");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setBanner({ type: "success", message: "PDF exported successfully." });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } catch (err) {
      const errorMessage = mapExportError(err, "pdf");
      setBanner({ type: "error", message: errorMessage });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } finally {
      setActionLoading(null);
    }
  }, [companyId, detail?.name, getAccessToken]);

  const handleExportJson = useCallback(async () => {
    if (!companyId || !detail?.name) {
      return;
    }

    setActionLoading("exportJson");
    try {
      const token = await getAccessToken();
      const blob = await exportCompanyJson(companyId, token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = createExportFilename(detail.name, "json");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setBanner({ type: "success", message: "JSON exported successfully." });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } catch (err) {
      const errorMessage = mapExportError(err, "json");
      setBanner({ type: "error", message: errorMessage });
      setTimeout(() => setBanner(null), BANNER_DISMISS_MS);
    } finally {
      setActionLoading(null);
    }
  }, [companyId, detail?.company.name, getAccessToken]);

  const handlePreview = useCallback(() => {
    setShowPreviewModal(true);
  }, []);

  const actionItems = useMemo<ActionItem[]>(() => {
    if (!detail) {
      return [];
    }

    const items: ActionItem[] = [];
    const { latest_analysis } = detail;

    if (isAnalyzingStatus(detail.analysis_status)) {
      items.push({
        key: "rerun",
        label: "Rerun Analysis",
        loadingLabel: "Starting...",
        variant: "primary",
        disabled: actionLoading !== null,
        onClick: handleRerun,
      });
    } else if (latest_analysis?.failed_checks && latest_analysis.failed_checks.length > 0) {
      items.push({
        key: "retryFailed",
        label: "Retry Failed Checks",
        loadingLabel: "Retrying...",
        variant: "primary",
        disabled: actionLoading !== null,
        onClick: handleRetryFailed,
      });
    }

    if (detail.status === "approved") {
      items.push({
        key: "revoke",
        label: "Revoke Approval",
        loadingLabel: "Revoking...",
        variant: "secondary",
        className: styles.dangerButton,
        disabled: actionLoading !== null,
        onClick: handleRevokeApproval,
      });
    }

    if (detail.status !== "fraudulent" && detail.status !== "revoked") {
      items.push({
        key: "flag",
        label: "Flag as Fraudulent",
        loadingLabel: "Flagging...",
        variant: "secondary",
        className: styles.warningButton,
        disabled: actionLoading !== null,
        onClick: handleFlagFraudulent,
      });
    }

    if (detail.status === "pending") {
      items.push({
        key: "review",
        label: "Mark Review Complete",
        loadingLabel: "Marking...",
        variant: "primary",
        disabled: actionLoading !== null,
        onClick: handleReviewComplete,
      });
    }

    if (latest_analysis) {
      items.push(
        {
          key: "exportPdf",
          label: "Export PDF",
          loadingLabel: "Exporting...",
          variant: "secondary",
          disabled: actionLoading !== null,
          onClick: handleExportPdf,
        },
        {
          key: "exportJson",
          label: "Export JSON",
          loadingLabel: "Exporting...",
          variant: "secondary",
          disabled: actionLoading !== null,
          onClick: handleExportJson,
        },
        {
          key: "preview",
          label: "Preview Export",
          variant: "secondary",
          disabled: actionLoading !== null,
          onClick: handlePreview,
        },
      );
    }

    return items;
  }, [
    detail,
    actionLoading,
    handleRerun,
    handleRetryFailed,
    handleRevokeApproval,
    handleFlagFraudulent,
    handleReviewComplete,
    handleExportPdf,
    handleExportJson,
    handlePreview,
  ]);

  if (loading) {
    return (
      <ProtectedLayout>
        <div className={styles.page}>
          <div style={{ padding: "20px", border: "2px solid red", margin: "20px" }}>
            <h2>Company Detail Page - LOADING</h2>
            <p>Company ID: {companyId || "NOT FOUND"}</p>
            <p>Pathname: {typeof window !== "undefined" ? window.location.pathname : "N/A"}</p>
            <p>Authenticated: {isAuthenticated ? "Yes" : "No"}</p>
          </div>
          <LoadingSkeleton rows={10} columns={1} />
        </div>
      </ProtectedLayout>
    );
  }

  if (error || !detail) {
    return (
      <ProtectedLayout>
        <div className={styles.page}>
          <div className={styles.errorState}>
            <h2>Company Detail Page</h2>
            <p>Company ID: {companyId || "NOT FOUND"}</p>
            <p>Error: {error ?? "Company not found"}</p>
            <p>Loading: {loading ? "Yes" : "No"}</p>
            <p>Authenticated: {isAuthenticated ? "Yes" : "No"}</p>
            <Button
              onClick={() => {
                void loadDetail({ initial: true });
              }}
            >
              Retry
            </Button>
            <Button
              onClick={() => {
                if (typeof window !== "undefined") {
                  window.location.href = "/dashboard";
                }
              }}
            >
              Back to Dashboard
            </Button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  return (
    <ProtectedLayout>
      <div className={styles.page}>
        {banner ? (
          <div className={banner.type === "success" ? styles.statusBannerSuccess : styles.statusBannerError}>
            {banner.message}
          </div>
        ) : null}

        <nav aria-label="Breadcrumb" className={styles.breadcrumb}>
          <Link href="/dashboard" className={styles.breadcrumbLink}>
            Dashboard
          </Link>
          <span className={styles.breadcrumbSeparator}>/</span>
          <span className={styles.breadcrumbCurrent}>{detail.name}</span>
        </nav>

        <CompanyHeader company={detail} latestAnalysis={detail.latest_analysis} />

        <div className={styles.actions}>
          {actionItems.map((item) => (
            <Button
              key={item.key}
              variant={item.variant}
              onClick={item.onClick}
              disabled={item.disabled}
              className={item.className}
            >
              {actionLoading === item.key ? item.loadingLabel ?? item.label : item.label}
            </Button>
          ))}
        </div>

        <CompanyTabs activeTab={activeTab} onTabChange={setActiveTab} />

        <div className={styles.tabContent}>
          {activeTab === "overview" && detail.latest_analysis ? (
            <OverviewTab analysis={detail.latest_analysis} company={detail} />
          ) : activeTab === "documents" ? (
            <DocumentsTab />
          ) : activeTab === "notes" ? (
            <NotesTab />
          ) : activeTab === "history" ? (
            <AnalysisHistoryTab companyName={detail.name} />
          ) : null}
        </div>

        {showPreviewModal && detail.latest_analysis ? (
          <ExportPreviewModal
            isOpen={showPreviewModal}
            company={detail}
            analysis={detail.latest_analysis}
            onClose={() => setShowPreviewModal(false)}
            onExportPdf={handleExportPdf}
            onExportJson={handleExportJson}
            isExportingPdf={actionLoading === "exportPdf"}
            isExportingJson={actionLoading === "exportJson"}
          />
        ) : null}
      </div>
    </ProtectedLayout>
  );
}

