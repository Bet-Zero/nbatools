import { useState } from "react";
import type { QueryResponse } from "../api/types";
import { Button, Card, SectionHeader } from "../design-system";
import styles from "./RawJsonToggle.module.css";

interface Props {
  data: QueryResponse;
  variant?: "card" | "inline";
}

export default function RawJsonToggle({ data, variant = "card" }: Props) {
  const [open, setOpen] = useState(false);

  const content = (
    <>
      <SectionHeader
        eyebrow="Developer output"
        title="Raw response"
        actions={
          <Button
            type="button"
            onClick={() => setOpen((v) => !v)}
            size="sm"
            variant="secondary"
          >
            {open ? "Hide Raw JSON" : "Show Raw JSON"}
          </Button>
        }
      />
      {open && (
        <pre className={styles.rawJson}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </>
  );

  if (variant === "inline") {
    return (
      <div
        className={[styles.rawToggle, styles.inline].join(" ")}
        data-shortcut-scope="ignore"
      >
        {content}
      </div>
    );
  }

  return (
    <Card
      className={styles.rawToggle}
      data-shortcut-scope="ignore"
      depth="input"
      padding="md"
    >
      {content}
    </Card>
  );
}
