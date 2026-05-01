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
  help?: string;
  semantic?: StatSemantic;
  size?: StatSize;
  className?: string;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

const STAT_HELP: Record<string, string> = {
  PTS: "Points",
  REB: "Rebounds",
  AST: "Assists",
  STL: "Steals",
  BLK: "Blocks",
  TOV: "Turnovers",
  MIN: "Minutes",
  "3PM": "Made three-pointers",
  "3P%": "Three-point percentage",
  "FG%": "Field goal percentage",
  "FT%": "Free throw percentage",
  "EFG%": "Effective field goal percentage",
  "TS%": "True shooting percentage",
  "USG%": "Usage percentage",
  "AST%": "Assist percentage",
  "REB%": "Rebound percentage",
  "TOV%": "Turnover percentage",
  "+/-": "Plus-minus",
};

function normalizeStatLabel(label: ReactNode): string | null {
  return typeof label === "string" ? label.trim().toUpperCase() : null;
}

export function Stat({
  label,
  value,
  context,
  help,
  semantic = "neutral",
  size = "md",
  className,
}: StatProps) {
  const resolvedHelp = help ?? STAT_HELP[normalizeStatLabel(label) ?? ""];
  const labelText = typeof label === "string" ? label : null;

  return (
    <div
      className={joinClassNames(
        styles.stat,
        styles[semantic],
        styles[size],
        className,
      )}
    >
      <span
        className={joinClassNames(styles.label, resolvedHelp && styles.helpLabel)}
        title={resolvedHelp}
        aria-label={
          resolvedHelp && labelText ? `${labelText}: ${resolvedHelp}` : undefined
        }
      >
        {label}
      </span>
      <span className={styles.value}>{value}</span>
      {context && <span className={styles.context}>{context}</span>}
    </div>
  );
}
