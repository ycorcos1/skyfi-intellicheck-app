import { Badge, type BadgeVariant } from "@/components/ui";
import type {
  AnalysisStatus,
  Company,
  CompanyAnalysis,
  CompanyStatus,
  CurrentStep,
} from "@/types/company";
import styles from "./CompanyHeader.module.css";

export interface CompanyHeaderProps {
  company: Company;
  latestAnalysis?: CompanyAnalysis | null;
  analysisProgressPercentage?: number | null;
}

const STATUS_LABELS: Record<CompanyStatus, string> = {
  approved: "Approved",
  pending: "Pending",
  suspicious: "Suspicious",
  fraudulent: "Fraudulent",
};

const STATUS_BADGE_VARIANTS: Record<CompanyStatus, BadgeVariant> = {
  approved: "approved",
  pending: "pending",
  suspicious: "suspicious",
  fraudulent: "fraudulent",
};

const ANALYSIS_STATUS_LABELS: Record<AnalysisStatus, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  complete: "Complete",
};

const ANALYSIS_BADGE_VARIANTS: Record<AnalysisStatus, BadgeVariant> = {
  pending: "analysis-pending",
  in_progress: "analysis-in-progress",
  complete: "analysis-complete",
};

const STEP_DESCRIPTIONS: Record<CurrentStep, string> = {
  whois: "WHOIS lookup",
  dns: "DNS checks",
  mx_validation: "MX validation",
  website_scrape: "Website scraping",
  llm_processing: "AI analysis",
  complete: "Complete",
};

function getRiskLevel(score: number) {
  if (score >= 70) {
    return { label: "High Risk", className: styles.riskHigh } as const;
  }

  if (score >= 40) {
    return { label: "Moderate Risk", className: styles.riskMedium } as const;
  }

  return { label: "Low Risk", className: styles.riskLow } as const;
}

function formatDate(value: string | null) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function formatAnalysisDetail(company: Company, analysis: CompanyAnalysis | null | undefined) {
  if (company.analysis_status === "in_progress") {
    const step = company.current_step ? STEP_DESCRIPTIONS[company.current_step] : "analysis";
    return `Processing: ${step}…`;
  }

  if (analysis) {
    const formatted = formatDate(analysis.created_at) ?? "an unknown date";
    const hasIssues = !analysis.is_complete || (analysis.failed_checks?.length ?? 0) > 0;
    return hasIssues ? `Last analyzed on ${formatted} — issues detected.` : `Last analyzed on ${formatted}.`;
  }

  if (company.analysis_status === "pending") {
    return "Analysis will begin shortly after creation.";
  }

  return "No recent analysis available.";
}

function clampProgress(value: number) {
  if (Number.isNaN(value)) {
    return 0;
  }

  return Math.min(100, Math.max(0, Math.round(value)));
}

export function CompanyHeader({
  company,
  latestAnalysis = null,
  analysisProgressPercentage = null,
}: CompanyHeaderProps) {
  const riskLevel = getRiskLevel(company.risk_score);
  const analysisDetail = formatAnalysisDetail(company, latestAnalysis);
  const showProgress =
    typeof analysisProgressPercentage === "number" &&
    (company.analysis_status === "pending" || company.analysis_status === "in_progress");
  const progressPercentage = showProgress ? clampProgress(analysisProgressPercentage) : null;
  const progressLabel =
    progressPercentage !== null
      ? `${progressPercentage}% complete${
          company.current_step && company.current_step !== "complete"
            ? ` · ${STEP_DESCRIPTIONS[company.current_step]}`
            : ""
        }`
      : null;

  return (
    <section className={styles.container} aria-labelledby="company-detail-heading">
      <div className={styles.primaryContent}>
        <div className={styles.titleRow}>
          <h1 id="company-detail-heading" className={styles.name}>
            {company.name}
          </h1>
          <Badge variant={STATUS_BADGE_VARIANTS[company.status]}>{STATUS_LABELS[company.status]}</Badge>
        </div>
        <p className={styles.domain}>
          <span className={styles.domainLabel}>Domain:</span>
          <span className={styles.domainValue}>{company.domain}</span>
        </p>
        <div className={styles.meta}>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Website</span>
            <span className={styles.metaValue}>{company.website_url || "—"}</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Contact</span>
            <span className={styles.metaValue}>{company.email}</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Last Analyzed</span>
            <span className={styles.metaValue}>{formatDate(company.last_analyzed_at) ?? "Pending"}</span>
          </div>
        </div>
      </div>

      <div className={styles.metrics}>
        <div className={`${styles.riskBadge} ${riskLevel.className}`} aria-live="polite">
          <span className={styles.riskScore}>{company.risk_score}</span>
          <span className={styles.riskLabel}>{riskLevel.label}</span>
        </div>
        <div className={styles.analysisStatus}>
          <Badge variant={ANALYSIS_BADGE_VARIANTS[company.analysis_status]} showAnimation>
            {ANALYSIS_STATUS_LABELS[company.analysis_status]}
          </Badge>
          {showProgress && progressPercentage !== null ? (
            <div className={styles.progress} role="status" aria-live="polite">
              <div className={styles.progressTrack} aria-hidden>
                <div className={styles.progressValue} style={{ width: `${progressPercentage}%` }} />
              </div>
              {progressLabel ? <span className={styles.progressLabel}>{progressLabel}</span> : null}
            </div>
          ) : null}
          <p className={styles.analysisDetail}>{analysisDetail}</p>
        </div>
      </div>
    </section>
  );
}

export default CompanyHeader;
