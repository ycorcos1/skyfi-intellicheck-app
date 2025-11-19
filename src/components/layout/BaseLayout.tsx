import React from "react";
import styles from "./BaseLayout.module.css";

export interface BaseLayoutProps {
  children: React.ReactNode;
}

export function BaseLayout({ children }: BaseLayoutProps) {
  return (
    <div className={styles.container}>
      <main className={styles.main}>{children}</main>
    </div>
  );
}


