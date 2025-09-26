# Fantasy JSON → JSONL ETL Script (league/season aware, improved)
# Usage: python etl.py <LEAGUE_ID> <SEASON> [--input fantasy.json] [--output-dir .]

import json, re, unicodedata, sys
from collections import defaultdict
from pathlib import Path

def norm(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def write_jsonl(path: Path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            clean = {k: v for k, v in r.items() if v is not None}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows → {path}")

def run(league_id: str, season_key: str, src: Path, out_dir: Path):
    data = json.loads(src.read_text(encoding="utf-8"))

    # locate league
    leagues = data.get("leagues", {})
    league = None
    league_name = None
    for lname, ldata in leagues.items():
        if ldata.get("league_id") == league_id:
            league = ldata
            league_name = lname
            break
    if league is None:
        raise ValueError(f"League {league_id} not found")

    seasons = league.get("seasons", {})
    if season_key not in seasons:
        raise ValueError(f"Season {season_key} not found in league {league_id}")

    season = seasons[season_key]

    teams = season.get("teams", [])
    games = season.get("games", {})
    transactions = season.get("transactions", [])
    draft = season.get("draft", {})

    id_by_name_norm = {norm(t["name"]): t["team_id"] for t in teams}

    # helper to attach metadata
    def with_meta(extra: dict) -> dict:
        return {
            "league_id": league_id,
            "league_name": league_name,
            "season": season_key,
            **extra,
        }

    matchups_rows, lineup_rows, tx_rows, draft_rows = [], [], [], []
    weekly_points = defaultdict(float)

    # Games → matchups + lineup slots + weekly player stats
    for week, wk in games.get("weeks", {}).items():
        wdate = wk.get("date")
        for g in wk.get("games", []):
            gid = g.get("game_id")

            def side_info(key):
                side = g.get(key, {})
                snap = side.get("name")
                tid = side.get("team_id") or id_by_name_norm.get(norm(snap))
                totals = side.get("totals", {})
                return side, tid, snap, totals.get("fpts", 0.0), totals.get("proj")

            a_side, a_id, a_name, a_score, _ = side_info("team_a")
            b_side, b_id, b_name, b_score, _ = side_info("team_b")
            winner = a_id if a_score > b_score else (b_id if b_score > a_score else "TIE")

            matchups_rows.append(with_meta({
                "week": int(week),
                "week_date": wdate,
                "game_id": gid,
                "team_a_id": a_id,
                "team_a_name_snapshot": a_name,
                "team_a_score": round(a_score, 2) if isinstance(a_score, (int, float)) else a_score,
                "team_b_id": b_id,
                "team_b_name_snapshot": b_name,
                "team_b_score": round(b_score, 2) if isinstance(b_score, (int, float)) else b_score,
                "winner_team_id": winner,
            }))

            def emit(side, tid, tname, bucket, entry):
                p = entry.get("player", {}) or {}
                snap_player = p.get("name")
                nplayer = norm(snap_player) if snap_player else ""
                row = with_meta({
                    "week": int(week),
                    "game_id": gid,
                    "team_id": tid,
                    "team_name_snapshot": tname,
                    "bucket": bucket,
                    "slot": entry.get("slot"),
                    "player_snapshot": snap_player,
                    "player_normalized": nplayer,
                    "nfl_team": p.get("team"),
                    "position": p.get("position"),
                    "opponent": p.get("opponent"),
                    "projected": p.get("proj"),
                    "points": p.get("fpts"),
                })
                lineup_rows.append(row)
                if nplayer and isinstance(p.get("fpts"), (int, float)):
                    weekly_points[(int(week), nplayer)] += float(p["fpts"])

            for e in a_side.get("starters", []):
                emit(a_side, a_id, a_name, "STARTER", e)
            for e in a_side.get("bench", []):
                emit(a_side, a_id, a_name, "BENCH", e)
            for e in a_side.get("ir", []):
                emit(a_side, a_id, a_name, "IR", e)
            for e in b_side.get("starters", []):
                emit(b_side, b_id, b_name, "STARTER", e)
            for e in b_side.get("bench", []):
                emit(b_side, b_id, b_name, "BENCH", e)
            for e in b_side.get("ir", []):
                emit(b_side, b_id, b_name, "IR", e)

    weekly_rows = [
        with_meta({"week": wk, "player_normalized": p, "points": round(pts, 2)})
        for (wk, p), pts in sorted(weekly_points.items())
    ]

    # Transactions
    for tx in transactions:
        base = with_meta({
            "date": tx.get("date"),
            "time": tx.get("time"),
            "type": tx.get("type"),
            "method": tx.get("method"),
            "team_id": tx.get("team_id"),
            "team_name_snapshot": tx.get("team_name"),
            "transaction_id": tx.get("transaction_id"),
        })
        if isinstance(tx.get("added"), dict):
            p = tx["added"]
            base.update({
                "added_player_snapshot": p.get("player"),
                "added_player_normalized": norm(p.get("player")) if p.get("player") else None,
                "added_team": p.get("team"),
                "added_position": p.get("position"),
                "added_cost": p.get("cost"),
            })
        if isinstance(tx.get("dropped"), dict):
            p = tx["dropped"]
            base.update({
                "dropped_player_snapshot": p.get("player"),
                "dropped_player_normalized": norm(p.get("player")) if p.get("player") else None,
                "dropped_team": p.get("team"),
                "dropped_position": p.get("position"),
            })
        for k in ("old_name","new_name","old_abbrev","new_abbrev","note"):
            if k in tx:
                base[k] = tx.get(k)
        tx_rows.append(base)

    # Draft
    for rnd, rdata in draft.get("rounds", {}).items():
        for pick in rdata.get("picks", []):
            pname = pick.get("player")
            draft_rows.append(with_meta({
                "round": int(rnd),
                "round_pick": pick.get("round_pick"),
                "overall": pick.get("overall"),
                "player_snapshot": pname,
                "player_normalized": norm(pname) if pname else None,
                "team_id": pick.get("team_id"),
                "team_name_snapshot": pick.get("team"),
            }))

    # Write all files with league/season prefix
    prefix = f"{league_id}_{season_key}_"
    write_jsonl(out_dir / f"{prefix}matchups.jsonl", matchups_rows)
    write_jsonl(out_dir / f"{prefix}lineup_slots.jsonl", lineup_rows)
    write_jsonl(out_dir / f"{prefix}weekly_player_stats.jsonl", weekly_rows)
    write_jsonl(out_dir / f"{prefix}transactions.jsonl", tx_rows)
    write_jsonl(out_dir / f"{prefix}draft_picks.jsonl", draft_rows)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python etl.py <LEAGUE_ID> <SEASON> [--input fantasy.json] [--output-dir .]")
        sys.exit(1)

    league_id = sys.argv[1]
    season_key = sys.argv[2]
    src = Path("fantasy.json")
    out_dir = Path(".")

    if "--input" in sys.argv:
        src = Path(sys.argv[sys.argv.index("--input") + 1])
    if "--output-dir" in sys.argv:
        out_dir = Path(sys.argv[sys.argv.index("--output-dir") + 1])

    run(league_id, season_key, src, out_dir)
