import { Stat, type StatProps } from "./Stat";
import styles from "./StatBlock.module.css";

export interface StatBlockProps {
  stats: StatProps[];
  columns?: 1 | 2 | 3 | 4;
  className?: string;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

const COLUMN_CLASS: Record<NonNullable<StatBlockProps["columns"]>, string> = {
  1: styles.columns1,
  2: styles.columns2,
  3: styles.columns3,
  4: styles.columns4,
};

export function StatBlock({ stats, columns = 4, className }: StatBlockProps) {
  if (stats.length === 0) return null;

  return (
    <div className={joinClassNames(styles.block, COLUMN_CLASS[columns], className)}>
      {stats.map((stat, index) => (
        <Stat key={index} {...stat} />
      ))}
    </div>
  );
}
