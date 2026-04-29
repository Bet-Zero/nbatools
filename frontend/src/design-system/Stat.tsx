import { type ReactNode } from "react";
import styles from "./Stat.module.css";

export type StatSemantic =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "win"
  | "loss";

export type StatSize = "md" | "hero";

export interface StatProps {
  label: ReactNode;
  value: ReactNode;
  context?: ReactNode;
  semantic?: StatSemantic;
  size?: StatSize;
  className?: string;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

export function Stat({
  label,
  value,
  context,
  semantic = "neutral",
  size = "md",
  className,
}: StatProps) {
  return (
    <div
      className={joinClassNames(
        styles.stat,
        styles[semantic],
        styles[size],
        className,
      )}
    >
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{value}</span>
      {context && <span className={styles.context}>{context}</span>}
    </div>
  );
}
