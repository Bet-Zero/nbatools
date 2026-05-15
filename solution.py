import json

approved_ids = [
    "guards_fg_percentage_leaders", "centers_rebound_leaders_wave4",
    "fewest_points_allowed_team_leader", "most_points_allowed_team_leaders_wave4",
    "opponent_ppg_leaders_wave4", "personal_foul_leaders_wave4",
    "rookie_scoring_leaders_wave4", "starter_assist_leaders_wave4",
    "bench_scoring_leaders_wave4", "celtics_bench_scoring_boundary_wave4",
    "record_when_jokic_triple_double", "lakers_road_record_last_season",
    "heat_knicks_playoff_series_record_wave4", "lebron_durant_comparison_wave4",
    "biggest_scoring_games"
]

raw_data = {}
raw_path = "outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl"
with open(raw_path, 'r') as f:
    for line in f:
        item = json.loads(line)
        cid = item.get("case_id")
        if cid in approved_ids:
            raw_data[cid] = {
                "case_id": cid,
                "query": item.get("query"),
                "category": item.get("category"),
                "route": item.ge                "route": i  "result_status": item.get("res                "route": item.ge                "route": i  "resultutputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.jsonl"
try:
    with open(frontend_path, 'r') as f:
        for line in f:
            item = json.loads(line)
            cid = item.get("case_id")
            if cid:
                frontend_ids.add(cid)
except FileNotFoundError:
    pass

print(f"{'case_id':<40} | {'query':<30} | {'cat':<10} | {'route':<15} | {'status':<10} | {'fe_copy'}")
print("-" * 125)
for cid in approved_ids:
    d = raw_data.get(cid, {})
    query = d.get("query", "N/A")[:28] + ".." if len(str(d.get("query", ""))) > 28 else d.get("query", "N/A")
    cat = d.get("catego    cat = d.get(route = d.get("route", "N/A")
    status = d.get("    status = d.get("       fe_exists = "Yes" if cid in frontend_ids else "No"
    print(f"{cid:<40} | {query:<30} | {cat:<10} | {route:<15} | {status:<10} | {fe_exists}")
