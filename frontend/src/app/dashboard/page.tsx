"use client";

import ProtectedLayout from "@/components/layout/ProtectedLayout";
import {
  CreateCompanyModal,
  DeleteCompanyModal,
  FilterPanel,
  SummaryCards,
  BulkUploadModal,
} from "@/components/dashboard";
import type { CreateCompanyFormState } from "@/components/dashboard";
import { Badge, BadgeVariant, Button, Table, TableColumn, TablePagination, SortDirection } from "@/components/ui";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/lib/api";
import { fetchCompanies, createCompany, deleteCompany, autoApproveIfEligible, bulkUploadCompanies } from "@/lib/companies-api";
import { useDebounce } from "@/hooks/useDebounce";
import type { Company, CompanyStatus, AnalysisStatus } from "@/types/company";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./dashboard.module.css";

const STATUS_LABELS: Record<CompanyStatus, string> = {
  approved: "Approved",
  pending: "Pending",
  rejected: "Rejected",
  fraudulent: "Fraudulent",
  revoked: "Revoked",
};

const STATUS_BADGE_VARIANTS: Record<CompanyStatus, BadgeVariant> = {
  approved: "approved",
  pending: "pending",
  rejected: "rejected",
  fraudulent: "fraudulent",
  revoked: "revoked",
};

const ANALYSIS_STATUS_LABELS: Record<AnalysisStatus, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  completed: "Completed",
  failed: "Failed",
  incomplete: "Incomplete",
};

const ANALYSIS_BADGE_VARIANTS: Record<AnalysisStatus, BadgeVariant> = {
  pending: "analysis-pending",
  in_progress: "analysis-in-progress",
  completed: "analysis-completed",
  failed: "analysis-failed",
  incomplete: "analysis-incomplete",
};

const formatDate = (value: string | null) => {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
};

const getRiskSeverityClass = (score: number) => {
  if (score >= 70) {
    return styles.riskHigh;
  }

  if (score >= 40) {
    return styles.riskMedium;
  }

  return styles.riskLow;
};

const tableColumns: TableColumn<Company>[] = [
  {
    key: "name",
    label: "Name",
    sortable: true,
    render: (_, row) => (
      <span className={styles.companyName} title={row.name}>
        {row.name}
      </span>
    ),
  },
  {
    key: "domain",
    label: "Domain",
    sortable: true,
    render: (value) => {
      const domain = value as string;
      return (
        <span className={styles.companyDomain} title={domain}>
          {domain}
        </span>
      );
    },
  },
  {
    key: "status",
    label: "Status",
    sortable: true,
    render: (_, row) => (
      <Badge variant={STATUS_BADGE_VARIANTS[row.status]}>{STATUS_LABELS[row.status]}</Badge>
    ),
  },
  {
    key: "analysis_status",
    label: "Analysis",
    sortable: true,
    render: (_, row) => (
      <Badge variant={ANALYSIS_BADGE_VARIANTS[row.analysis_status]}>
        {ANALYSIS_STATUS_LABELS[row.analysis_status]}
      </Badge>
    ),
  },
  {
    key: "risk_score",
    label: "Risk Score",
    sortable: true,
    align: "center",
    render: (value) => {
      const score = value as number;
      return <span className={`${styles.riskScore} ${getRiskSeverityClass(score)}`}>{score}</span>;
    },
  },
  {
    key: "created_at",
    label: "Created",
    sortable: true,
    render: (value) => formatDate(value as string),
  },
  {
    key: "last_analyzed_at",
    label: "Last Analyzed",
    sortable: true,
    render: (value) => (typeof value === "string" ? formatDate(value) : formatDate(null)),
  },
];

const DEFAULT_PAGE_SIZE = 20;

const SORTABLE_KEYS = new Set<keyof Company>([
  "name",
  "domain",
  "status",
  "analysis_status",
  "risk_score",
  "created_at",
  "last_analyzed_at",
]);

function compareValues(aValue: unknown, bValue: unknown) {
  if (aValue === bValue) {
    return 0;
  }

  if (aValue === null || aValue === undefined) {
    return 1;
  }

  if (bValue === null || bValue === undefined) {
    return -1;
  }

  if (typeof aValue === "number" && typeof bValue === "number") {
    return aValue - bValue;
  }

  if (typeof aValue === "string" && typeof bValue === "string") {
    const aDate = Date.parse(aValue);
    const bDate = Date.parse(bValue);

    if (!Number.isNaN(aDate) && !Number.isNaN(bDate)) {
      return aDate - bDate;
    }

    return aValue.localeCompare(bValue, undefined, { sensitivity: "base" });
  }

  return String(aValue).localeCompare(String(bValue), undefined, { sensitivity: "base" });
}

function parseRiskInput(value: string): number | undefined {
  if (value.trim() === "") {
    return undefined;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? undefined : parsed;
}

export default function DashboardPage() {
  const { getAccessToken, logout, isAuthenticated } = useAuth();
  const router = useRouter();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<CompanyStatus | "all">("all");
  const [riskMin, setRiskMin] = useState("0");
  const [riskMax, setRiskMax] = useState("100");
  const [sortedColumn, setSortedColumn] = useState<string | undefined>("created_at");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [deleteModalCompany, setDeleteModalCompany] = useState<Company | null>(null);
  const [isBulkUploadModalOpen, setIsBulkUploadModalOpen] = useState(false);
  const [bulkUploadLoading, setBulkUploadLoading] = useState(false);
  const [bulkUploadError, setBulkUploadError] = useState<string | null>(null);
  const [bulkUploadResult, setBulkUploadResult] = useState<{
    success_count: number;
    error_count: number;
    errors: Array<{ index: number; error: string }>;
  } | null>(null);
  const [isAutoApproving, setIsAutoApproving] = useState(false);

  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  const riskRangeError = useMemo(() => {
    const minValue = parseRiskInput(riskMin);
    const maxValue = parseRiskInput(riskMax);

    if (minValue !== undefined && maxValue !== undefined && minValue > maxValue) {
      return "Minimum risk score cannot exceed maximum.";
    }

    return null;
  }, [riskMin, riskMax]);

  const summaryCounts = useMemo(() => {
    const pendingCount = companies.filter((company) => company.status === "pending").length;
    const approvedCount = companies.filter((company) => company.status === "approved").length;
    const highRiskCount = companies.filter((company) => company.risk_score >= 70).length;

    return {
      pendingCount,
      approvedCount,
      highRiskCount,
    };
  }, [companies]);

  const sortedCompanies = useMemo(() => {
    if (!sortedColumn || !SORTABLE_KEYS.has(sortedColumn as keyof Company)) {
      return companies;
    }

    const data = [...companies];

    data.sort((a, b) => {
      const aValue = a[sortedColumn as keyof Company];
      const bValue = b[sortedColumn as keyof Company];
      const comparison = compareValues(aValue, bValue);
      return sortDirection === "asc" ? comparison : -comparison;
    });

    return data;
  }, [companies, sortDirection, sortedColumn]);

  const handleSort = useCallback((key: string, direction: SortDirection) => {
    setSortedColumn(key);
    setSortDirection(direction);
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handleClearFilters = useCallback(() => {
    setSearchTerm("");
    setSelectedStatus("all");
    setRiskMin("0");
    setRiskMax("100");
    setCurrentPage(1);
  }, []);

  const handleSearchChange = useCallback((value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  }, []);

  const handleStatusChange = useCallback((value: string) => {
    setSelectedStatus(value as CompanyStatus | "all");
    setCurrentPage(1);
  }, []);

  const handleRiskMinChange = useCallback((value: string) => {
    setRiskMin(value);
    setCurrentPage(1);
  }, []);

  const handleRiskMaxChange = useCallback((value: string) => {
    setRiskMax(value);
    setCurrentPage(1);
  }, []);

  const loadCompanies = useCallback(async () => {
    if (riskRangeError || !isAuthenticated || isLoggingOut) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = await getAccessToken();

      if (!token) {
        // Don't redirect here - let ProtectedLayout handle it
        // This prevents redirect loops when API is down
        setError("Unable to get authentication token. Please try logging in again.");
        setLoading(false);
        return;
      }

      const riskMinValue = parseRiskInput(riskMin);
      const riskMaxValue = parseRiskInput(riskMax);

      const response = await fetchCompanies(
        {
          page: currentPage,
          limit: DEFAULT_PAGE_SIZE,
          search: debouncedSearchTerm || undefined,
          status: selectedStatus,
          risk_min: riskMinValue,
          risk_max: riskMaxValue,
        },
        token,
      );

      if (response.pages > 0 && currentPage > response.pages) {
        setCurrentPage(response.pages);
        return;
      }

      setCompanies(response.items);
      setTotalPages(response.pages ?? 0);
      
      // Auto-approve eligible companies (analysis=COMPLETED, risk_score<=30, status=PENDING)
      // This handles companies that were analyzed before the auto-approve logic was added
      // Only run if we're not already auto-approving to prevent infinite loops
      if (!isAutoApproving) {
        const eligibleCompanies = response.items.filter(
          (company) =>
            company.analysis_status === "completed" &&
            company.risk_score <= 30 &&
            company.status === "pending"
        );
        
        if (eligibleCompanies.length > 0) {
          setIsAutoApproving(true);
          // Auto-approve eligible companies in the background (don't block UI)
          // Use refreshToken instead of calling loadCompanies directly to avoid infinite loops
          Promise.all(
            eligibleCompanies.map(async (company) => {
              try {
                await autoApproveIfEligible(company.id, token);
                console.log(`Auto-approved company: ${company.name} (risk_score: ${company.risk_score})`);
              } catch (err) {
                // Silently fail - company might have been updated by another process
                console.warn(`Failed to auto-approve company ${company.name}:`, err);
              }
            })
          ).then(() => {
            // Refresh the list after auto-approvals complete using refreshToken
            // This prevents infinite loops by using the existing refresh mechanism
            setIsAutoApproving(false);
            setRefreshToken((value) => value + 1);
          }).catch((err) => {
            console.error("Error during auto-approval batch:", err);
            setIsAutoApproving(false);
          });
        }
      }
    } catch (loadError) {
      console.error("Failed to load companies", loadError);
      
      // If we get a 401, the token is invalid - log out and let ProtectedLayout redirect
      if (loadError instanceof ApiError && loadError.statusCode === 401 && !isLoggingOut) {
        setIsLoggingOut(true);
        try {
          await logout();
        } catch (logoutError) {
          console.error("Failed to logout", logoutError);
        }
        return;
      }
      
      const message = loadError instanceof Error ? loadError.message : "Failed to load companies.";
      setError(message);
      setCompanies([]);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, debouncedSearchTerm, getAccessToken, isAuthenticated, isLoggingOut, logout, riskMax, riskMin, riskRangeError, selectedStatus, isAutoApproving]);

  useEffect(() => {
    // Only load companies if authenticated and not logging out
    // Add a delay to ensure auth state is stable and prevent race conditions
    if (isAuthenticated && !isLoggingOut) {
      const timer = setTimeout(() => {
        // Double-check we're still authenticated before loading
        if (isAuthenticated && !isLoggingOut) {
    void loadCompanies();
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [loadCompanies, refreshToken, isAuthenticated, isLoggingOut]);

  const handleDeleteClick = useCallback(
    (company: Company) => {
      setDeleteModalCompany(company);
    },
    [],
  );

  const handleDeleteConfirm = useCallback(
    async () => {
      if (!deleteModalCompany) {
        return;
      }

      try {
        setDeletingId(deleteModalCompany.id);
        const token = await getAccessToken();
        
        if (!token) {
          throw new Error("Authentication required. Please sign in again.");
        }

        await deleteCompany(deleteModalCompany.id, token);
        
        // Close modal and refresh the companies list
        setDeleteModalCompany(null);
        await loadCompanies();
      } catch (err) {
        console.error("Failed to delete company", err);
        const message = err instanceof Error ? err.message : "Failed to delete company. Please try again.";
        setError(message);
        // Keep modal open on error so user can try again
      } finally {
        setDeletingId(null);
      }
    },
    [deleteModalCompany, getAccessToken, loadCompanies],
  );

  const handleDeleteCancel = useCallback(() => {
    setDeleteModalCompany(null);
  }, []);

  const tableColumnsWithActions: TableColumn<Company>[] = useMemo(
    () => [
      ...tableColumns,
      {
        key: "actions",
        label: "Actions",
        align: "right",
        render: (_, row) => (
          <Button
            className={styles.dangerButton}
            onClick={() => handleDeleteClick(row)}
            disabled={deletingId === row.id}
            aria-label={`Delete ${row.name}`}
          >
            Delete
          </Button>
        ),
      },
    ],
    [deletingId, handleDeleteClick],
  );

  const handleCreateCompany = useCallback(
    async (data: CreateCompanyFormState) => {
      setCreateLoading(true);
      setCreateError(null);

      try {
        const token = await getAccessToken();

        if (!token) {
          setCreateError("Authentication required. Please sign in again.");
          return;
        }

        await createCompany(
          {
            name: data.name.trim(),
            domain: data.domain.trim(),
            website_url: data.website_url.trim() || undefined,
            email: data.email.trim(),
            phone: data.phone.trim() || undefined,
          },
          token,
        );

        setIsCreateModalOpen(false);
        setCreateError(null);
        setCurrentPage(1);
        setRefreshToken((value) => value + 1);
      } catch (createErr) {
        console.error("Failed to create company", createErr);
        const message = createErr instanceof Error ? createErr.message : "Failed to create company.";
        setCreateError(message);
      } finally {
        setCreateLoading(false);
      }
    },
    [getAccessToken],
  );

  const handleBulkUpload = useCallback(
    async (file: File) => {
      setBulkUploadLoading(true);
      setBulkUploadError(null);
      setBulkUploadResult(null);

      try {
        const token = await getAccessToken();

        if (!token) {
          setBulkUploadError("Authentication required. Please sign in again.");
          return;
        }

        const result = await bulkUploadCompanies(file, token);
        setBulkUploadResult(result);
        
        // Refresh companies list
        setCurrentPage(1);
        setRefreshToken((value) => value + 1);
      } catch (uploadErr) {
        console.error("Failed to upload companies", uploadErr);
        const message = uploadErr instanceof Error ? uploadErr.message : "Failed to upload companies.";
        setBulkUploadError(message);
      } finally {
        setBulkUploadLoading(false);
      }
    },
    [getAccessToken],
  );

  return (
    <ProtectedLayout>
      <div className={styles.page}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Companies</h1>
            <p className={styles.subtitle}>Monitor verification activity, review signals, and manage high-risk profiles.</p>
          </div>
          <div style={{ display: "flex", gap: "12px" }}>
            <Button variant="secondary" onClick={() => setIsBulkUploadModalOpen(true)}>
              Bulk Upload JSON
            </Button>
          <Button onClick={() => setIsCreateModalOpen(true)}>Create Company</Button>
          </div>
        </header>

        <FilterPanel
          searchTerm={searchTerm}
          onSearchChange={handleSearchChange}
          selectedStatus={selectedStatus}
          onStatusChange={handleStatusChange}
          riskMin={riskMin}
          onRiskMinChange={handleRiskMinChange}
          riskMax={riskMax}
          onRiskMaxChange={handleRiskMaxChange}
          onClearFilters={handleClearFilters}
          disabled={loading}
          riskRangeError={riskRangeError}
        />

        <SummaryCards
          pendingCount={summaryCounts.pendingCount}
          approvedCount={summaryCounts.approvedCount}
          highRiskCount={summaryCounts.highRiskCount}
        />

        <section aria-label="Companies table" className={styles.tableSection}>
          {loading ? (
            <LoadingSkeleton rows={8} columns={tableColumnsWithActions.length} />
          ) : error ? (
            <div className={styles.errorState}>
              <p>{error}</p>
              <Button
                onClick={() => {
                  void loadCompanies();
                }}
              >
                Retry
              </Button>
            </div>
          ) : (
            <>
              <Table
                columns={tableColumnsWithActions}
                data={sortedCompanies}
                sortedColumn={sortedColumn}
                sortDirection={sortDirection}
                onSort={handleSort}
                onRowClick={(row) => {
                  // Navigate to company detail page when row is clicked
                  // Stop propagation to prevent triggering when clicking the Delete button
                  if (row.id && typeof row.id === "string") {
                    router.push(`/dashboard/companies/${row.id}`);
                  }
                }}
                emptyState={
                  <div className={styles.emptyState}>
                    <p>No companies found.</p>
                    <p>Try adjusting your filters or create a new company.</p>
                    <Button onClick={() => setIsCreateModalOpen(true)}>Create Company</Button>
                  </div>
                }
              />
              <TablePagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
                className={styles.pagination}
                disabled={loading || totalPages <= 1}
              />
            </>
          )}
        </section>
      </div>

      {isCreateModalOpen ? (
        <CreateCompanyModal
          isOpen={isCreateModalOpen}
          onClose={() => {
            setIsCreateModalOpen(false);
            setCreateError(null);
          }}
          onSubmit={handleCreateCompany}
          loading={createLoading}
          error={createError}
        />
      ) : null}
      <DeleteCompanyModal
        isOpen={deleteModalCompany !== null}
        company={deleteModalCompany}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        isLoading={deletingId !== null}
      />
      {isBulkUploadModalOpen && (
        <BulkUploadModal
          isOpen={isBulkUploadModalOpen}
          onClose={() => {
            setIsBulkUploadModalOpen(false);
            setBulkUploadError(null);
            setBulkUploadResult(null);
          }}
          onUpload={handleBulkUpload}
          loading={bulkUploadLoading}
          error={bulkUploadError}
          result={bulkUploadResult}
        />
      )}
    </ProtectedLayout>
  );
}
