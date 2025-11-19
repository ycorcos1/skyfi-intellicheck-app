import React from "react";
import styles from "./BaseLayout.module.css";

export interface BaseLayoutProps {
  children: React.ReactNode;
}

export function BaseLayout({ children }: BaseLayoutProps) {
  return (
    <div className={styles.container}>
      <main id="main-content" className={styles.main} role="main" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}


