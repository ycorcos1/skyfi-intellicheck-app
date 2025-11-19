import { Card } from "@/components/ui";
import type { Company, CompanyAnalysis, SubmittedData, DiscoveredData } from "@/types/company";
import { SignalsTable } from "./SignalsTable";
import styles from "./OverviewTab.module.css";

export interface OverviewTabProps {
  company: Company;
  analysis: CompanyAnalysis | null;
}

const SUBMITTED_FIELD_CONFIG: Array<{ key: keyof SubmittedData; label: string }> = [
  { key: "name", label: "Company Name" },
  { key: "domain", label: "Domain" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "website_url", label: "Website" },
];

const DISCOVERED_FIELD_CONFIG: Array<{ key: keyof DiscoveredData; label: string }> = [
  { key: "domain_age_months", label: "Domain Age" },
  { key: "whois_privacy_enabled", label: "WHOIS Privacy" },
  { key: "mx_records_valid", label: "MX Records" },
  { key: "website_reachable", label: "Website Reachable" },
  { key: "ssl_certificate_valid", label: "SSL Certificate" },
];

function formatValue(key: keyof SubmittedData | keyof DiscoveredData, value: unknown) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (typeof value === "number") {
    if (key === "domain_age_months") {
      return `${value} month${value === 1 ? "" : "s"}`;
    }

    return value.toLocaleString();
  }

  return String(value);
}

function buildSubmittedEntries(company: Company, analysis: CompanyAnalysis | null) {
  const submitted = analysis?.submitted_data ?? {};

  return SUBMITTED_FIELD_CONFIG.map((field) => {
    const fallback = company[field.key as keyof Company];
    const value = submitted[field.key] ?? (typeof fallback === "string" ? fallback : undefined);
    return {
      label: field.label,
      value: formatValue(field.key, value),
    };
  });
}

function buildDiscoveredEntries(analysis: CompanyAnalysis | null) {
  const discovered = analysis?.discovered_data ?? {};

  return DISCOVERED_FIELD_CONFIG.map((field) => {
    const value = discovered[field.key];
    return {
      label: field.label,
      value: formatValue(field.key, value),
    };
  });
}

export function OverviewTab({ company, analysis }: OverviewTabProps) {
  const submittedEntries = buildSubmittedEntries(company, analysis);
  const discoveredEntries = buildDiscoveredEntries(analysis);
  const summary = analysis?.llm_summary ?? "Once an analysis completes, a narrative summary will appear here highlighting the strongest risk signals and recommended follow-up actions.";

  return (
    <section className={styles.container} aria-labelledby="overview-heading">
      <div className={styles.columns}>
        <Card className={styles.columnCard} header={<h2 className={styles.columnTitle}>Submitted Data</h2>} bodyClassName={styles.columnBody}>
          <dl className={styles.definitionList}>
            {submittedEntries.map((entry) => (
              <div key={entry.label} className={styles.definitionRow}>
                <dt>{entry.label}</dt>
                <dd>{entry.value}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card className={styles.columnCard} header={<h2 className={styles.columnTitle}>Discovered Data</h2>} bodyClassName={styles.columnBody}>
          <dl className={styles.definitionList}>
            {discoveredEntries.map((entry) => (
              <div key={entry.label} className={styles.definitionRow}>
                <dt>{entry.label}</dt>
                <dd>{entry.value}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>

      <SignalsTable signals={analysis?.signals ?? []} />

      <Card className={styles.summaryCard} header={<h2 className={styles.summaryTitle}>AI Analysis Summary</h2>} bodyClassName={styles.summaryBody}>
        <p>{summary}</p>
      </Card>
    </section>
  );
}

export default OverviewTab;
