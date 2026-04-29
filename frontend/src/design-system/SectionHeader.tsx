import { type ReactNode } from "react";
import styles from "./SectionHeader.module.css";

export interface SectionHeaderProps {
  title: ReactNode;
  eyebrow?: ReactNode;
  count?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

export function SectionHeader({
  title,
  eyebrow,
  count,
  actions,
  className,
}: SectionHeaderProps) {
  return (
    <div className={joinClassNames(styles.header, className)}>
      <div className={styles.titleGroup}>
        {eyebrow && <span className={styles.eyebrow}>{eyebrow}</span>}
        <span className={styles.title}>{title}</span>
        {count && <span className={styles.count}>{count}</span>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}
