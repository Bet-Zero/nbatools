import { type ReactNode } from "react";
import { Card, type CardProps } from "./Card";
import styles from "./ResultEnvelopeShell.module.css";

export interface ResultEnvelopeShellProps
  extends Omit<CardProps, "children"> {
  meta?: ReactNode;
  query?: ReactNode;
  context?: ReactNode;
  notices?: ReactNode;
  alternates?: ReactNode;
  children?: ReactNode;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

export function ResultEnvelopeShell({
  meta,
  query,
  context,
  notices,
  alternates,
  children,
  className,
  depth = "card",
  padding = "md",
  ...props
}: ResultEnvelopeShellProps) {
  return (
    <Card
      depth={depth}
      padding={padding}
      className={joinClassNames(styles.shell, className)}
      {...props}
    >
      {meta && <div className={styles.meta}>{meta}</div>}
      {query && <div className={styles.query}>{query}</div>}
      {context && <div className={styles.context}>{context}</div>}
      {notices && <div className={styles.notices}>{notices}</div>}
      {children}
      {alternates && <div className={styles.alternates}>{alternates}</div>}
    </Card>
  );
}
