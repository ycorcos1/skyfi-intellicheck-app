import type { AnalysisSignal } from "@/types/company";
import styles from "./SignalsTable.module.css";

export interface SignalsTableProps {
  signals: AnalysisSignal[];
}

const STATUS_LABELS: Record<AnalysisSignal["status"], string> = {
  ok: "Ok",
  suspicious: "Suspicious",
  mismatch: "Mismatch",
  warning: "Warning",
};

export function SignalsTable({ signals }: SignalsTableProps) {
  if (signals.length === 0) {
    return (
      <div className={styles.emptyState}>
        <p>No signals generated for this analysis.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <table className={styles.table}>
        <caption className={styles.caption}>Risk Signals</caption>
        <thead>
          <tr>
            <th scope="col">Signal</th>
            <th scope="col">Observed Value</th>
            <th scope="col" className={styles.statusHeader}>
              Status
            </th>
            <th scope="col" className={styles.weightHeader}>
              Weight
            </th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => (
            <tr key={`${signal.field}-${signal.status}`}>
              <td className={styles.fieldCell}>
                <span className={styles.fieldLabel}>{signal.field.replace(/_/g, " ")}</span>
                {signal.description ? <span className={styles.fieldDescription}>{signal.description}</span> : null}
              </td>
              <td>{signal.value}</td>
              <td>
                <span className={`${styles.statusBadge} ${styles[signal.status]}`}>
                  {STATUS_LABELS[signal.status]}
                </span>
              </td>
              <td className={styles.weightCell}>{signal.weight ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default SignalsTable;
