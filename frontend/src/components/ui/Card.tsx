import React from "react";
import styles from "./Card.module.css";

export interface CardProps {
  children: React.ReactNode;
  header?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

function composeClassNames(...values: Array<string | undefined | false>) {
  return values.filter(Boolean).join(" ");
}

export function Card({ children, header, className, bodyClassName }: CardProps) {
  return (
    <section className={composeClassNames(styles.card, className)}>
      {header ? <header className={styles.header}>{header}</header> : null}
      <div className={composeClassNames(styles.body, bodyClassName)}>{children}</div>
    </section>
  );
}

export default Card;

