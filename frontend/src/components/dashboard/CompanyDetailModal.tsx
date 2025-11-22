"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import styles from "./CompanyDetailModal.module.css";

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

export interface CompanyDetailModalProps {
  isOpen: boolean;
  companyId: string | null;
  onClose: () => void;
  onCompanyUpdated?: () => void;
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

export function CompanyDetailModal({
  isOpen,
  companyId,
  onClose,
  onCompanyUpdated,
}: CompanyDetailModalProps) {
  const modalRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);
  const { getAccessToken } = useAuth();

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

  // Handle modal open/close behavior
  useEffect(() => {
    if (!isOpen) {
      // Reset state when modal closes
      setDetail(null);
      setLoading(true);
      setError(null);
      setBanner(null);
      setActiveTab("overview");
      setShowPreviewModal(false);
      stopPolling();
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    previouslyFocusedElementRef.current = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.removeProperty("overflow");
      stopPolling();
      previouslyFocusedElementRef.current?.focus({ preventScroll: true });
    };
  }, [isOpen, onClose, stopPolling]);

  const handleOverlayClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  const loadDetail = useCallback(
    async ({ initial = false }: { initial?: boolean } = {}) => {
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
          console.error("CompanyDetailModal: No access token available");
          setError("Authentication required. Please sign in again.");
          if (initial) {
            setLoading(false);
          }
          return;
        }

        const data = await fetchCompanyDetail(companyId, token);
        
        // Validate response structure
        if (!data || !data.company) {
          throw new Error("Invalid response: company data is missing");
        }
        
        setDetail(data);

        if (data.company.analysis_status === "in_progress" || data.company.analysis_status === "pending") {
          if (!pollingIntervalRef.current) {
            pollingIntervalRef.current = setInterval(() => {
              void loadDetail({ initial: false });
            }, POLLING_INTERVAL_MS);
          }
        } else {
          stopPolling();
        }

        // Notify parent that company was updated
        if (onCompanyUpdated) {
          onCompanyUpdated();
        }
      } catch (err) {
        console.error("CompanyDetailModal: Failed to load company detail", err);

        if (err instanceof Error && "statusCode" in err && (err as { statusCode: number }).statusCode === 401) {
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
    [companyId, getAccessToken, stopPolling, onCompanyUpdated],
  );

  useEffect(() => {
    if (isOpen && companyId) {
      void loadDetail({ initial: true });
    }

    return () => {
      stopPolling();
    };
  }, [isOpen, companyId, loadDetail, stopPolling]);

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
    if (!companyId || !detail?.company.name) {
      return;
    }

    setActionLoading("exportPdf");
    try {
      const token = await getAccessToken();
      const blob = await exportCompanyPdf(companyId, token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = createExportFilename(detail.company.name, "pdf");
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
  }, [companyId, detail?.company.name, getAccessToken]);

  const handleExportJson = useCallback(async () => {
    if (!companyId || !detail?.company.name) {
      return;
    }

    setActionLoading("exportJson");
    try {
      const token = await getAccessToken();
      const blob = await exportCompanyJson(companyId, token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = createExportFilename(detail.company.name, "json");
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
    if (!detail || !detail.company) {
      return [];
    }

    const items: ActionItem[] = [];
    const { company, latest_analysis } = detail;

    if (company && isAnalyzingStatus(company.analysis_status)) {
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

    if (company?.status === "approved") {
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

    if (company?.status && company.status !== "fraudulent" && company.status !== "revoked") {
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

    if (company?.status === "pending") {
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

  if (!isOpen) {
    return null;
  }

  return (
    <>
      <div
        className={styles.overlay}
        role="presentation"
        onClick={handleOverlayClick}
      >
        <div
          ref={modalRef}
          className={styles.modal}
          role="dialog"
          aria-modal="true"
          aria-labelledby="company-detail-modal-title"
          onClick={(e) => e.stopPropagation()}
        >
          <div className={styles.header}>
            <div className={styles.headerTop}>
              <h2 id="company-detail-modal-title">Company Details</h2>
              <button
                type="button"
                className={styles.closeButton}
                aria-label="Close"
                onClick={onClose}
              >
                ×
              </button>
            </div>
          </div>

          <div className={styles.content}>
            {loading ? (
              <div className={styles.loadingState}>
                <LoadingSkeleton rows={10} columns={1} />
              </div>
            ) : error || !detail || !detail.company ? (
              <div className={styles.errorState}>
                <h3>Error Loading Company</h3>
                <p>{error ?? "Company not found or invalid data"}</p>
                <div className={styles.errorActions}>
                  <Button
                    onClick={() => {
                      void loadDetail({ initial: true });
                    }}
                  >
                    Retry
                  </Button>
                  <Button variant="secondary" onClick={onClose}>
                    Close
                  </Button>
                </div>
              </div>
            ) : (
              <>
                {banner ? (
                  <div className={banner.type === "success" ? styles.statusBannerSuccess : styles.statusBannerError}>
                    {banner.message}
                  </div>
                ) : null}

                <CompanyHeader company={detail.company} latestAnalysis={detail.latest_analysis} />

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
                    <OverviewTab analysis={detail.latest_analysis} company={detail.company} />
                  ) : activeTab === "documents" ? (
                    <DocumentsTab companyId={companyId ?? undefined} />
                  ) : activeTab === "notes" ? (
                    <NotesTab companyId={companyId ?? undefined} />
                  ) : activeTab === "history" ? (
                    <AnalysisHistoryTab companyName={detail.company.name} />
                  ) : null}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {showPreviewModal && detail?.latest_analysis ? (
        <ExportPreviewModal
          isOpen={showPreviewModal}
          company={detail.company}
          analysis={detail.latest_analysis}
          onClose={() => setShowPreviewModal(false)}
          onExportPdf={handleExportPdf}
          onExportJson={handleExportJson}
          isExportingPdf={actionLoading === "exportPdf"}
          isExportingJson={actionLoading === "exportJson"}
        />
      ) : null}
    </>
  );
}

export default CompanyDetailModal;

