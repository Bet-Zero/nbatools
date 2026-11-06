import type { ReactNode } from "react";
import type { QueryResponse, SectionRow } from "../../../api/types";
import ResultHero from "../primitives/ResultHero";
import ResultTable, { type ResultTableColumn } from "../primitives/ResultTable";

const MEMBERSHIP: Record<string, string> = {
  member: "Verified member",
  not_member: "Verified nonmember of the requested team",
  unknown: "Membership unknown",
};
const PARTICIPATION: Record<string, string> = {
  played: "Played",
  did_not_play: "Explicitly did not play",
  not_member: "Not a member of the requested team",
  unknown: "Unknown — insufficient participation evidence",
};
const COLUMNS: ResultTableColumn<SectionRow>[] = [
  {
    key: "date",
    header: "Date",
    render: (row) => String(row.date ?? "Unknown"),
  },
  {
    key: "membership_state",
    header: "Membership",
    render: (row) =>
      MEMBERSHIP[String(row.membership_state)] ?? MEMBERSHIP.unknown,
  },
  {
    key: "member_team_id",
    header: "Verified NBA team",
    render: (row) =>
      String(
        row.member_team_abbr ??
          (row.member_team_id == null
            ? "Unknown"
            : `Team ${row.member_team_id}`),
      ),
  },
  {
    key: "participation_state",
    header: "Participation",
    render: (row) =>
      PARTICIPATION[String(row.participation_state)] ?? PARTICIPATION.unknown,
  },
];

export default function MembershipResult({
  data,
  afterHero,
}: {
  data: QueryResponse;
  afterHero?: ReactNode;
}) {
  const rows = data.result?.sections?.summary ?? [];
  if (rows.length === 0) return null;
  const row = rows[0];
  const member = MEMBERSHIP[String(row.membership_state)] ?? MEMBERSHIP.unknown;
  const player = row.player_name ? `${row.player_name}: ` : "";
  return (
    <section aria-label="Dated NBA membership result">
      <ResultHero
        sentence={`${player}${member} on ${row.date ?? "the requested date"}.`}
        tone="neutral"
      />
      {afterHero}
      <ResultTable
        rows={rows}
        columns={COLUMNS}
        ariaLabel="Membership and participation"
      />
      <p>
        Membership alone does not establish participation or an absence reason.
      </p>
    </section>
  );
}
