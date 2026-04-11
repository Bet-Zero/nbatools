import type { QueryResponse } from "../api/types";

interface Props {
  data: QueryResponse;
}

function statusClass(status: string): string {
  if (status === "ok") return "status-ok";
  if (status === "no_result") return "status-warn";
  return "status-err";
}

export default function ResultEnvelope({ data }: Props) {
  const metadata = data.result?.metadata;
  const contextParts: string[] = [];
  if (metadata) {
    if (typeof metadata.player === "string") contextParts.push(metadata.player);
    if (typeof metadata.team === "string") contextParts.push(metadata.team);
    if (typeof metadata.season === "string") contextParts.push(metadata.season);
    if (Array.isArray(metadata.players) && metadata.players.length)
      contextParts.push(metadata.players.join(", "));
    if (Array.isArray(metadata.teams) && metadata.teams.length)
      contextParts.push(metadata.teams.join(", "));
  }

  return (
    <div className="envelope">
      <Row label="Query">{data.query}</Row>
      <Row label="Status">
        <span className={statusClass(data.result_status)}>
          {data.result_status}
        </span>
        {data.result_reason && (
          <span className="muted"> ({data.result_reason})</span>
        )}
      </Row>
      {data.route && (
        <Row label="Route">
          <span className="pill">{data.route}</span>
        </Row>
      )}
      {data.current_through && (
        <Row label="Data through">{data.current_through}</Row>
      )}
      {contextParts.length > 0 && (
        <Row label="Context">{contextParts.join(" · ")}</Row>
      )}
      {data.notes.length > 0 && (
        <Row label="Notes">
          <BulletList items={data.notes} className="notes-list" />
        </Row>
      )}
      {data.caveats.length > 0 && (
        <Row label="Caveats">
          <BulletList
            items={data.caveats}
            className="notes-list caveats-list"
          />
        </Row>
      )}
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="envelope-row">
      <span className="envelope-label">{label}</span>
      <span className="envelope-value">{children}</span>
    </div>
  );
}

function BulletList({
  items,
  className,
}: {
  items: string[];
  className: string;
}) {
  return (
    <ul className={className}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}
