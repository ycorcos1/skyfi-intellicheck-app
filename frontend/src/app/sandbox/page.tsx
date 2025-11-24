"use client";

import ProtectedLayout from "@/components/layout/ProtectedLayout";
import { Badge, BadgeVariant, Button, Card, Input, Select, SelectOption, Table, TableColumn, TablePagination } from "@/components/ui";
import { useMemo, useState } from "react";
import styles from "./page.module.css";

type MockCompany = {
  id: string;
  name: string;
  domain: string;
  status: "approved" | "pending" | "fraudulent" | "suspicious";
  risk: number;
  created: string;
  lastAnalyzed: string;
  analysisStatus: BadgeVariant;
};

const mockCompanies: MockCompany[] = [
  {
    id: "1",
    name: "NovaGeo Analytics Incorporated",
    domain: "novageoanalytics.io",
    status: "pending",
    risk: 68,
    created: "2025-01-15",
    lastAnalyzed: "2025-01-16",
    analysisStatus: "analysis-in-progress",
  },
  {
    id: "2",
    name: "GeoStream Technologies",
    domain: "geostreamtechnologies.com",
    status: "approved",
    risk: 14,
    created: "2025-01-12",
    lastAnalyzed: "2025-01-14",
    analysisStatus: "analysis-complete",
  },
  {
    id: "3",
    name: "OrbitSight Labs",
    domain: "orbitsight.ai",
    status: "suspicious",
    risk: 52,
    created: "2024-12-22",
    lastAnalyzed: "2025-01-03",
    analysisStatus: "analysis-warning",
  },
  {
    id: "4",
    name: "Skyward Ventures",
    domain: "skywardventures.co",
    status: "fraudulent",
    risk: 92,
    created: "2024-12-28",
    lastAnalyzed: "2025-01-10",
    analysisStatus: "analysis-warning",
  },
  {
    id: "5",
    name: "Atlas Mapping Solutions",
    domain: "atlasmapping.io",
    status: "approved",
    risk: 24,
    created: "2024-11-30",
    lastAnalyzed: "2024-12-15",
    analysisStatus: "analysis-complete",
  },
  {
    id: "6",
    name: "Lumen Cartographics",
    domain: "lumencarto.co",
    status: "pending",
    risk: 60,
    created: "2025-01-08",
    lastAnalyzed: "2025-01-09",
    analysisStatus: "analysis-in-progress",
  },
  {
    id: "7",
    name: "TerraScope Intelligence",
    domain: "terrascopeintelligence.net",
    status: "suspicious",
    risk: 74,
    created: "2024-12-05",
    lastAnalyzed: "2024-12-18",
    analysisStatus: "analysis-warning",
  },
  {
    id: "8",
    name: "Magellan Data Group",
    domain: "magellandatagroup.com",
    status: "approved",
    risk: 38,
    created: "2024-10-18",
    lastAnalyzed: "2024-12-01",
    analysisStatus: "analysis-pending",
  },
];

const statusOptions: SelectOption[] = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "suspicious", label: "Suspicious" },
  { value: "fraudulent", label: "Fraudulent" },
];

const PAGE_SIZE = 5;

const badgeLabels: Record<BadgeVariant, string> = {
  approved: "Approved",
  pending: "Pending",
  fraudulent: "Fraudulent",
  suspicious: "Suspicious",
  "analysis-pending": "Pending",
  "analysis-in-progress": "In Progress",
  "analysis-complete": "Complete",
  "analysis-warning": "Complete (Issues)",
};

const formatBadgeLabel = (variant: BadgeVariant) => {
  return badgeLabels[variant] ?? variant;
};

const tableColumns: TableColumn<MockCompany>[] = [
  { key: "name", label: "Company Name", sortable: true, truncate: 30 },
  { key: "domain", label: "Domain", sortable: true, truncate: 20 },
  {
    key: "status",
    label: "Status",
    sortable: true,
    render: (value) => {
      const variant = value as BadgeVariant;
      return <Badge variant={variant}>{formatBadgeLabel(variant)}</Badge>;
    },
  },
  {
    key: "analysisStatus",
    label: "Analysis",
    render: (value) => {
      const variant = value as BadgeVariant;
      return <Badge variant={variant}>{formatBadgeLabel(variant)}</Badge>;
    },
  },
  { key: "risk", label: "Risk Score", sortable: true, align: "center" },
  { key: "created", label: "Created", sortable: true },
  { key: "lastAnalyzed", label: "Last Analyzed", sortable: true },
];

function sortCompanies(data: MockCompany[], column?: string, direction: "asc" | "desc" = "asc") {
  if (!column) {
    return data;
  }

  const sorted = [...data].sort((a, b) => {
    const aValue = a[column as keyof MockCompany];
    const bValue = b[column as keyof MockCompany];

    if (typeof aValue === "number" && typeof bValue === "number") {
      return aValue - bValue;
    }

    return String(aValue).localeCompare(String(bValue), undefined, { sensitivity: "base" });
  });

  return direction === "asc" ? sorted : sorted.reverse();
}

export default function SandboxPage() {
  const [sortedColumn, setSortedColumn] = useState<string | undefined>("name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);

  const sortedCompanies = useMemo(
    () => sortCompanies(mockCompanies, sortedColumn, sortDirection),
    [sortDirection, sortedColumn],
  );

  const totalPages = Math.ceil(sortedCompanies.length / PAGE_SIZE);
  const paginatedCompanies = useMemo(
    () =>
      sortedCompanies.slice((currentPage - 1) * PAGE_SIZE, (currentPage - 1) * PAGE_SIZE + PAGE_SIZE),
    [currentPage, sortedCompanies],
  );

  const handleSort = (key: string, direction: "asc" | "desc") => {
    setSortedColumn(key);
    setSortDirection(direction);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <ProtectedLayout>
      <div className={styles.page}>
        <header className={styles.header}>
          <h1>UI Component Sandbox</h1>
          <p>Preview of core UI primitives for SkyFi IntelliCheck.</p>
        </header>

        <section className={styles.section}>
          <h2>Buttons</h2>
          <div className={styles.buttonGroup}>
            <Button variant="primary">Primary Action</Button>
            <Button variant="secondary">Secondary Action</Button>
            <Button variant="primary" disabled>
              Disabled
            </Button>
          </div>
        </section>

        <section className={styles.section}>
          <h2>Inputs</h2>
          <div className={styles.formGrid}>
            <Input id="company-name" label="Company Name" placeholder="Enter company name" />
            <Input id="domain" label="Domain" placeholder="example.com" hint="We'll verify the domain automatically." />
            <Input
              id="email"
              type="email"
              label="Contact Email"
              placeholder="operator@skyfi.com"
              error="Email domain must match the company domain."
            />
          </div>
        </section>

        <section className={styles.section}>
          <h2>Selects</h2>
          <div className={styles.formGrid}>
            <Select
              id="status-filter"
              label="Status Filter"
              placeholder="Select status"
              options={statusOptions}
            />
            <Select
              id="status-filter-error"
              label="Status Filter (Error State)"
              placeholder="Select status"
              options={statusOptions}
              error="Select a status before continuing."
            />
          </div>
        </section>

        <section className={styles.section}>
          <h2>Status Badges</h2>
          <div className={styles.badgeGroup}>
            <Badge variant="approved">Approved</Badge>
            <Badge variant="pending">Pending</Badge>
            <Badge variant="suspicious">Suspicious</Badge>
            <Badge variant="fraudulent">Fraudulent</Badge>
          </div>
          <div className={styles.badgeGroup}>
            <Badge variant="analysis-pending">Pending</Badge>
            <Badge variant="analysis-in-progress">In Progress</Badge>
            <Badge variant="analysis-complete">Complete</Badge>
            <Badge variant="analysis-warning">Complete (Issues)</Badge>
          </div>
        </section>

        <section className={styles.section}>
          <h2>Cards</h2>
          <div className={styles.cardGrid}>
            <Card header={<h3>Summary Card</h3>}>
              <p>
                Cards provide elevated containers with consistent padding, border radius, and shadow. Use them to group related
                content like metrics, forms, or detail views.
              </p>
            </Card>
            <Card>
              <h3>Card Without Header</h3>
              <p>This variant shows how content renders when the header prop is omitted.</p>
            </Card>
          </div>
        </section>

        <section className={styles.section}>
          <h2>Table Shell</h2>
          <div className={styles.tableWrapper}>
            <Table
              caption="Company Overview"
              columns={tableColumns}
              data={paginatedCompanies}
              sortedColumn={sortedColumn}
              sortDirection={sortDirection}
              onSort={handleSort}
              emptyState={<p>No companies to display. Adjust filters to see results.</p>}
            />
            <TablePagination currentPage={currentPage} totalPages={totalPages} onPageChange={handlePageChange} />
          </div>
        </section>
      </div>
    </ProtectedLayout>
  );
}

