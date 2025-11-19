import { Card } from "@/components/ui";
import styles from "./SummaryCards.module.css";

export interface SummaryCardsProps {
  pendingCount: number;
  approvedCount: number;
  highRiskCount: number;
}

const CARD_CONFIG = [
  {
    key: "pending",
    label: "Pending",
    accentClassName: styles.pendingAccent,
    description: "Awaiting operator review",
    accessor: (counts: SummaryCardsProps) => counts.pendingCount,
  },
  {
    key: "approved",
    label: "Approved",
    accentClassName: styles.approvedAccent,
    description: "Ready for enterprise access",
    accessor: (counts: SummaryCardsProps) => counts.approvedCount,
  },
  {
    key: "highRisk",
    label: "High Risk",
    accentClassName: styles.highRiskAccent,
    description: "Score ≥ 70 requires immediate attention",
    accessor: (counts: SummaryCardsProps) => counts.highRiskCount,
  },
];

export function SummaryCards(props: SummaryCardsProps) {
  return (
    <section className={styles.container} aria-label="Company summary metrics">
      {CARD_CONFIG.map((card) => (
        <Card key={card.key} className={styles.card} bodyClassName={styles.cardBody}>
          <div className={card.accentClassName} aria-hidden />
          <div className={styles.cardContent}>
            <p className={styles.label}>{card.label}</p>
            <p className={styles.value}>{card.accessor(props).toLocaleString()}</p>
            <p className={styles.description}>{card.description}</p>
          </div>
        </Card>
      ))}
    </section>
  );
}

export default SummaryCards;

