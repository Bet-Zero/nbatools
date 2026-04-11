import { useState } from "react";
import type { QueryResponse } from "../api/types";

interface Props {
  data: QueryResponse;
}

export default function RawJsonToggle({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="raw-toggle">
      <button
        type="button"
        className="toggle-btn"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide Raw JSON" : "Show Raw JSON"}
      </button>
      {open && (
        <pre className="raw-json active">{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
}
