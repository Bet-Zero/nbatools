export function thresholdFilterValue(label: string, value: string): string | null {
  const match = label.match(/^(.+)\s+(min|max)$/i);
  if (!match) return null;

  const [, stat, direction] = match;
  const isExclusive = /\(exclusive\)/i.test(value);
  const threshold = compactThresholdValue(value);
  if (stat.trim().toLowerCase() === "opp pts") {
    if (direction.toLowerCase() === "min") {
      return isExclusive
        ? `Opp PTS > ${threshold}`
        : `Opp PTS >= ${threshold}`;
    }
    return isExclusive
      ? `Opp PTS < ${threshold}`
      : `Opp PTS <= ${threshold}`;
  }
  const suffix = statLabel(stat);
  if (direction.toLowerCase() === "min") {
    return isExclusive ? `> ${threshold} ${suffix}` : `${threshold}+ ${suffix}`;
  }
  return isExclusive ? `< ${threshold} ${suffix}` : `<= ${threshold} ${suffix}`;
}

function compactThresholdValue(value: string): string {
  const normalized = value.replace(/\s*\(exclusive\)\s*/gi, "").trim();
  const numeric = Number(normalized);
  if (!Number.isFinite(numeric)) return normalized;
  const rounded = Math.round(numeric);
  if (
    Math.abs(numeric - rounded) < 0.001 ||
    Math.abs(numeric - rounded - 0.0001) < 0.001
  ) {
    return String(rounded);
  }
  return Number(numeric.toFixed(1)).toString();
}

export function statLabel(stat: string): string {
  const normalized = stat.trim().toLowerCase();
  const labels: Record<string, string> = {
    ast: "AST",
    ast_avg: "APG",
    ast_per_game: "APG",
    blk: "BLK",
    blk_avg: "BPG",
    blk_per_game: "BPG",
    fg3a: "3PA",
    fg3a_total: "3PA",
    fg3m: "3PM",
    fg3m_total: "3PM",
    fga: "FGA",
    fga_total: "FGA",
    fgm: "FGM",
    fgm_total: "FGM",
    fta: "FTA",
    fta_total: "FTA",
    ftm: "FTM",
    ftm_total: "FTM",
    minutes: "Minutes",
    minutes_total: "Minutes",
    pf: "PF",
    pf_total: "PF",
    pts: "PTS",
    pts_avg: "PPG",
    pts_per_game: "PPG",
    "opp pts": "Opponent points",
    opponent_pts: "Opponent points",
    reb: "REB",
    reb_avg: "RPG",
    reb_per_game: "RPG",
    stl: "STL",
    stl_avg: "SPG",
    stl_per_game: "SPG",
    tov: "TOV",
  };
  return labels[normalized] ?? normalized.replace(/_/g, " ").toUpperCase();
}

