import React from "react";
import styles from "./Badge.module.css";

export type BadgeVariant =
  | "approved"
  | "pending"
  | "fraudulent"
  | "rejected"
  | "revoked"
  | "analysis-pending"
  | "analysis-in-progress"
  | "analysis-completed"
  | "analysis-failed"
  | "analysis-incomplete";

export interface BadgeProps {
  variant: BadgeVariant;
  children: React.ReactNode;
  showAnimation?: boolean;
  className?: string;
}

function composeClassNames(...values: Array<string | undefined | false>) {
  return values.filter(Boolean).join(" ");
}

export function Badge({ variant, children, showAnimation = true, className }: BadgeProps) {
  const isAnimated = variant === "analysis-in-progress" && showAnimation;

  const badgeClassName = composeClassNames(styles.badge, styles[variant], isAnimated ? styles.pulse : undefined, className);

  return <span className={badgeClassName}>{children}</span>;
}

export default Badge;

