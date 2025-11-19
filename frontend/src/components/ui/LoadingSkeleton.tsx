import styles from "./LoadingSkeleton.module.css";

export interface LoadingSkeletonProps {
  rows?: number;
  columns?: number;
}

export function LoadingSkeleton({ rows = 6, columns = 6 }: LoadingSkeletonProps) {
  return (
    <div className={styles.container} role="status" aria-live="polite" aria-busy="true">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className={styles.row}>
          {Array.from({ length: columns }).map((__, columnIndex) => (
            <div
              key={columnIndex}
              className={styles.cell}
              style={{
                width: `${Math.max(10, 30 - columnIndex * 3)}%`,
              }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export default LoadingSkeleton;

