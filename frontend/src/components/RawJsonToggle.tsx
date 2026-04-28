import { useState } from "react";
import type { QueryResponse } from "../api/types";
import styles from "./RawJsonToggle.module.css";

interface Props {
  data: QueryResponse;
}

export default function RawJsonToggle({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className={styles.rawToggle}>
      <button
        type="button"
        className={styles.toggleButton}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide Raw JSON" : "Show Raw JSON"}
      </button>
      {open && (
        <pre className={styles.rawJson}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
}
