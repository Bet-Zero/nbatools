import { useState } from "react";
import type { QueryResponse } from "../api/types";
import { Button } from "../design-system";
import styles from "./RawJsonToggle.module.css";

interface Props {
  data: QueryResponse;
}

export default function RawJsonToggle({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className={styles.rawToggle}>
      <Button
        type="button"
        onClick={() => setOpen((v) => !v)}
        size="sm"
        variant="secondary"
      >
        {open ? "Hide Raw JSON" : "Show Raw JSON"}
      </Button>
      {open && (
        <pre className={styles.rawJson}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
}
