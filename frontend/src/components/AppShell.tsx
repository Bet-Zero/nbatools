import type { ReactNode } from "react";
import styles from "./AppShell.module.css";

interface AppShellProps {
  header: ReactNode;
  status?: ReactNode;
  query: ReactNode;
  secondary?: ReactNode;
  dialog?: ReactNode;
  children: ReactNode;
}

export default function AppShell({
  header,
  status,
  query,
  secondary,
  dialog,
  children,
}: AppShellProps) {
  return (
    <div className={styles.shell}>
      <div className={styles.container}>
        <header className={styles.header}>{header}</header>

        {status && (
          <section className={styles.statusRegion} aria-label="Data freshness">
            {status}
          </section>
        )}

        <div className={styles.workspace}>
          <main className={styles.primary} aria-label="NBA query workspace">
            <section className={styles.queryRegion} aria-label="Query controls">
              {query}
            </section>
            <section className={styles.mainRegion} aria-label="Query results">
              {children}
            </section>
          </main>

          {secondary && (
            <aside
              className={styles.secondary}
              aria-label="Saved queries, history, and tools"
            >
              {secondary}
            </aside>
          )}
        </div>
      </div>

      {dialog}
    </div>
  );
}
