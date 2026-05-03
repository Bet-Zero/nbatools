import type { ReactNode } from "react";
import styles from "./ResultShell.module.css";

interface Props {
  children: ReactNode;
}

/**
 * Outer wrapper for every result page. Provides consistent vertical
 * spacing between stacked patterns and mobile padding so individual
 * patterns do not have to manage page-level layout.
 *
 * The freshness banner is rendered at the App level, not inside this
 * shell. This wrapper is for the result content itself.
 */
export default function ResultShell({ children }: Props) {
  return <div className={styles.shell}>{children}</div>;
}
