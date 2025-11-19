import styles from "./CompanyTabs.module.css";

export type CompanyTabKey = "overview" | "history" | "documents" | "notes";

export interface CompanyTabsProps {
  activeTab: CompanyTabKey;
  onTabChange: (tab: CompanyTabKey) => void;
}

const TABS: Array<{ key: CompanyTabKey; label: string; description: string }> = [
  { key: "overview", label: "Overview", description: "Signals, summary, and risk" },
  { key: "history", label: "Analysis History", description: "Versioned reports" },
  { key: "documents", label: "Documents", description: "Uploaded evidence" },
  { key: "notes", label: "Notes", description: "Internal operator notes" },
];

export function CompanyTabs({ activeTab, onTabChange }: CompanyTabsProps) {
  return (
    <nav className={styles.tabs} aria-label="Company detail sections">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={tab.key === activeTab ? `${styles.tab} ${styles.active}` : styles.tab}
          onClick={() => onTabChange(tab.key)}
          aria-current={tab.key === activeTab ? "page" : undefined}
        >
          <span className={styles.tabLabel}>{tab.label}</span>
          <span className={styles.tabDescription}>{tab.description}</span>
        </button>
      ))}
    </nav>
  );
}

export default CompanyTabs;
