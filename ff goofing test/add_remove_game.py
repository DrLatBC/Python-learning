#!/usr/bin/env python3
import json
import sys
import os

# --------------------------------------
# IO
# --------------------------------------
def load_json(filename):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        return {"leagues by ID": {}}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --------------------------------------
# Helpers / normalization
# --------------------------------------
DEFAULT_STARTER_SLOTS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "D/ST", "K"]

def parse_record(record_str):
    """Return (wins, losses, ties) from a 'W-L-T' string, or (0,0,0)."""
    try:
        parts = record_str.split("-")
        w, l, t = (int(x) for x in (parts + ["0", "0"])[:3])
        return w, l, t
    except Exception:
        return 0, 0, 0
    
def clean_record_str(record_str: str) -> str:
    """Extract just the 'W-L-T' part from messy record strings and log if changed."""
    if not isinstance(record_str, str):
        return ""
    raw = record_str.strip()
    if not raw:
        return ""
    part = raw.split(",")[0].strip()
    tokens = part.split()
    cleaned = tokens[0] if tokens else ""
    if cleaned != raw:
        print(f"🧹 Cleaned record: '{raw}' → '{cleaned}'")
    return cleaned

def maybe_update_team_record(season, team):
    """If the ingested record has more games played, update team record in teams list."""
    teams_section = season.get("teams", [])
    tid = team.get("team_id")
    new_record = team.get("record", "")

    if not tid or not new_record:
        return

    new_w, new_l, new_t = parse_record(new_record)
    new_total = new_w + new_l + new_t

    for t in teams_section:
        if t.get("team_id") == tid:
            old_w, old_l, old_t = parse_record(t.get("record", ""))
            old_total = old_w + old_l + old_t
            if new_total > old_total:
                t["record"] = new_record
                print(f"🔄 Updated {t['name']} record: {old_w}-{old_l}-{old_t} → {new_record}")
            break

def apply_team_update(season, update):
    """
    Handle team_update transactions: add old name/abbrev to aliases.
    """
    aliases = season.get("team_aliases", [])

    new_name = update.get("new_name")
    old_name = update.get("old_name")
    old_abbrev = update.get("old_abbrev")

    for team in aliases:
        if team.get("name") == new_name:
            if old_name and old_name not in team.get("aliases", []):
                team.setdefault("aliases", []).append(old_name)
            if old_abbrev and old_abbrev not in team.get("aliases", []):
                team.setdefault("aliases", []).append(old_abbrev)
            break

def normalize_position(pos_raw):
    pos_raw = norm_str(pos_raw)
    return "D/ST" if pos_raw.replace(" ", "").upper() in {"DST", "D/ST"} else pos_raw.upper()


def calculate_team_totals(team: dict):
    """Recalculate team totals and warn if starters differ by >10 points."""
    starters = team.get("starters", [])
    bench = team.get("bench", [])

    # unrounded sums
    s_proj_sum = sum((p.get("player", {}) or {}).get("proj", 0.0) for p in starters)
    s_fpts_sum = sum((p.get("player", {}) or {}).get("fpts", 0.0) for p in starters)
    b_proj_sum = sum((p.get("player", {}) or {}).get("proj", 0.0) for p in bench)
    b_fpts_sum = sum((p.get("player", {}) or {}).get("fpts", 0.0) for p in bench)

    recomputed = {
        "proj": round(s_proj_sum, 2),
        "fpts": round(s_fpts_sum, 2),
        "bench_proj": round(b_proj_sum, 2),
        "bench_fpts": round(b_fpts_sum, 2),
    }

    # detect large mismatches (starters only)
    big_diff = False
    old_totals = team.get("totals", {})
    for key in ("proj", "fpts"):  # ✅ only starters
        try:
            old_val = float(old_totals.get(key, 0.0))
            new_val = float(recomputed[key])
            if abs(old_val - new_val) > 10:
                big_diff = True
                break
        except Exception:
            continue

    if big_diff:
        print(
            f"⚠️ Large totals mismatch for {team.get('name','[unknown]')}: "
            f"old={{'proj': {old_totals.get('proj')}, 'fpts': {old_totals.get('fpts')}}}, "
            f"new={{'proj': {recomputed['proj']}, 'fpts': {recomputed['fpts']}}}"
        )

    # overwrite totals
    team["totals"] = recomputed

def r2(x):
    try:
        return round(float(x), 2)
    except Exception:
        return 0.0

def normalize_opponent(opp: str) -> str:
    if not isinstance(opp, str):
        return ""
    opp = opp.strip()
    if not opp:
        return ""
    if opp.startswith("@"):
        return "@" + opp[1:].upper()
    return opp.upper()

def norm_str(x):
    return x.strip() if isinstance(x, str) else ""

def drop_stub_player_entry(entry):
    """Decide if an entry is a stub (for BENCH/IR) and should be dropped."""
    if not isinstance(entry, dict):
        return True
    p = entry.get("player", {})
    if not isinstance(p, dict):
        return True
    name = norm_str(p.get("name", ""))
    team = norm_str(p.get("team", ""))
    pos  = norm_str(p.get("position", ""))
    return not (name or team or pos)

def normalize_player_entry(entry):
    """Normalize a W1-style player entry: {'slot':..., 'player':{...}}"""
    if not isinstance(entry, dict):
        return entry

    # ensure 'player' exists
    player = entry.get("player", {})
    if not isinstance(player, dict):
        player = {}

    # normalize fields
    player["name"] = norm_str(player.get("name", ""))
    player["team"] = norm_str(player.get("team", "")).upper()
    # keep "D/ST" exact otherwise uppercase
    pos_raw = norm_str(player.get("position", ""))
    player["position"] = "D/ST" if pos_raw.replace(" ", "").upper() in {"DST", "D/ST"} else pos_raw.upper()

    # normalize opponent
    if "opponent" in player:
        player["opponent"] = normalize_opponent(player.get("opponent", ""))

    # numbers
    player["proj"] = r2(player.get("proj"))
    player["fpts"] = r2(player.get("fpts"))

    # slot must be a string (may be missing; fixed later)
    entry["slot"] = norm_str(entry.get("slot", "")) or "BENCH"
    entry["player"] = player
    return entry

def normalize_team(team: dict, side: str, game_id: str, alias_to_id: dict):
    # 🔁 Promote box_score fields if present
    if "box_score" in team and isinstance(team["box_score"], dict):
        box = team.pop("box_score")
        for key in ("starters", "bench", "ir"):
            if key in box:
                team[key] = box[key]

    loud_warnings = []
    team = dict(team) if isinstance(team, dict) else {}

    # ✅ Normalize shallow fields
    team["name"] = norm_str(team.get("name", ""))
    team["record"] = clean_record_str(team.get("record", ""))

    # ✅ Assign team_id from aliases
    name_key = team["name"].strip().lower()
    team_id = alias_to_id.get(name_key)
    if not team_id:
        raise ValueError(f"[{game_id} {side}] Unknown team name '{team['name']}'. Add to team_aliases.")
    team["team_id"] = team_id

    # 🚮 Drop unwanted fields (manager, score, division, rank) but warn only if present & meaningful
    for junk in ("manager", "score", "division", "rank"):
        if junk in team:
            val = team[junk]
            if val not in (None, "", 0):
                loud_warnings.append(f"⚠️ [{game_id} {side}] Stripped '{junk}' (value={val!r}) on ingest.")
            team.pop(junk, None)

    # 🔁 Wrap raw player dicts into W1-style format
    def wrap_raw_players(players):
        wrapped = []
        for p in players:
            if isinstance(p, dict) and "player" not in p:
                pos = p.get("position")
                if not pos:
                    print(f"⚠️ Warning: Missing position for player {p.get('name', '[unknown]')}")
                wrapped.append({
                    "slot": None,
                    "player": {
                        "name": p.get("name", ""),
                        "team": p.get("team", ""),
                        "position": pos or "???",
                        "opponent": p.get("opponent", ""),
                        "proj": p.get("projected_points", 0.0),
                        "fpts": p.get("actual_points", 0.0)
                    }
                })
            else:
                wrapped.append(p)
        return wrapped

    team["starters"] = wrap_raw_players(team.get("starters", []))
    team["bench"]    = wrap_raw_players(team.get("bench", []))
    team["ir"]       = wrap_raw_players(team.get("ir", []))

    # ✅ Normalize player entries
    starters = [normalize_player_entry(x) for x in team.get("starters", []) if isinstance(x, dict)]
    bench    = [normalize_player_entry(x) for x in team.get("bench", []) if isinstance(x, dict)]
    ir       = [normalize_player_entry(x) for x in team.get("ir", []) if isinstance(x, dict)]

    # ❌ Drop stubs from bench and IR
    before_bench = len(bench)
    before_ir = len(ir)
    bench = [x for x in bench if not drop_stub_player_entry(x)]
    ir    = [x for x in ir    if not drop_stub_player_entry(x)]
    if len(bench) != before_bench:
        loud_warnings.append(f"⚠️ [{game_id} {side}] Dropped {before_bench - len(bench)} BENCH stub(s).")
    if len(ir) != before_ir:
        loud_warnings.append(f"⚠️ [{game_id} {side}] Dropped {before_ir - len(ir)} IR stub(s).")

    # 🎯 Auto-assign slots if missing
    missing_slots = any(s.get("slot") is None for s in starters)
    if missing_slots:
        loud_warnings.append(f"⚠️ [{game_id} {side}] Starter slots missing — auto-assigned default W1 order.")
        for i, s in enumerate(starters):
            s["slot"] = DEFAULT_STARTER_SLOTS[i] if i < len(DEFAULT_STARTER_SLOTS) else "FLEX"

    # 💾 Store normalized rosters
    team["starters"] = starters
    team["bench"] = bench
    team["ir"] = ir

    # ✅ Recalculate totals
    calculate_team_totals(team)

    return team, loud_warnings


def verify_game(game: dict, game_id: str):
    """
    Abort on:
      - missing team names (manager ignored now)
      - broken starter row (missing name/team/position)
      - ESPN missing projections: proj == 0 while fpts > 0
      - totals mismatch > ±0.05 (starters and bench)
    """
    issues = []

    def chk_team(side_key):
        side = game.get(side_key, {})
        name = norm_str(side.get("name", ""))
        if not name:
            issues.append(f"{game_id} {side_key}: Missing team name")

        starters = side.get("starters", [])
        bench = side.get("bench", [])
        totals = side.get("totals", {})

        # Broken starter rows
        for i, s in enumerate(starters):
            p = s.get("player", {})
            nm = norm_str(p.get("name", ""))
            tm = norm_str(p.get("team", ""))
            pos = norm_str(p.get("position", ""))
            if not (nm and tm and pos):
                issues.append(f"{game_id} {side_key}: Broken starter row #{i+1} (name/team/position missing)")
            # ESPN missing projections
            proj = p.get("proj", 0.0)
            fpts = p.get("fpts", 0.0)
            if r2(proj) == 0.0 and r2(fpts) > 0.0:
                issues.append(f"{game_id} {side_key}: ESPN missing projection for '{nm}' (proj=0.0, fpts={r2(fpts)})")

        # Totals checks (recompute now, unrounded then round once)
        s_proj_sum = sum((x.get("player", {}) or {}).get("proj", 0.0) for x in starters)
        s_fpts_sum = sum((x.get("player", {}) or {}).get("fpts", 0.0) for x in starters)
        b_proj_sum = sum((x.get("player", {}) or {}).get("proj", 0.0) for x in bench)
        b_fpts_sum = sum((x.get("player", {}) or {}).get("fpts", 0.0) for x in bench)

        t_proj = r2(s_proj_sum)
        t_fpts = r2(s_fpts_sum)
        tb_proj = r2(b_proj_sum)
        tb_fpts = r2(b_fpts_sum)

        def near(a, b, tol=0.05):
            try:
                return abs(float(a) - float(b)) <= tol
            except Exception:
                return False

        if not near(totals.get("proj", None), t_proj):
            issues.append(f"{game_id} {side_key}: Starters projected total mismatch (totals={totals.get('proj')}, sum={t_proj})")
        if not near(totals.get("fpts", None), t_fpts):
            issues.append(f"{game_id} {side_key}: Starters fpts total mismatch (totals={totals.get('fpts')}, sum={t_fpts})")
        if not near(totals.get("bench_proj", None), tb_proj):
            issues.append(f"{game_id} {side_key}: Bench projected total mismatch (totals={totals.get('bench_proj')}, sum={tb_proj})")
        if not near(totals.get("bench_fpts", None), tb_fpts):
            issues.append(f"{game_id} {side_key}: Bench fpts total mismatch (totals={totals.get('bench_fpts')}, sum={tb_fpts})")

    chk_team("team_a")
    chk_team("team_b")
    return issues

# --------------------------------------
# Game add/remove
# --------------------------------------
def ensure_week_bucket(data, league_id, year, week, date_str):
    leagues = data.setdefault("leagues by ID", {})
    league = leagues.setdefault(league_id, {"league_id": league_id})

    seasons = league.setdefault("seasons by ID", {})
    season_id = f"{league_id}S{year}"
    season = seasons.setdefault(season_id, {"season_id": season_id, "year": int(year)})

    games = season.setdefault("games", {})
    weeks = games.setdefault("weeks", {})
    wk = weeks.setdefault(str(week), {"games": [], "date": date_str})

    # keep date in sync with whatever you passed on this call
    wk["date"] = date_str
    return wk["games"]

def generate_game_id(games, league_id, year, week):
    existing_ids = [g.get("game_id", "") for g in games]
    gnums = [
        int(gid.split("G")[-1])
        for gid in existing_ids
        if gid.startswith(f"{league_id}S{year}W{week}G")
    ]
    next_gnum = max(gnums, default=0) + 1
    return f"{league_id}S{year}W{week}G{next_gnum}"


def add_game(master_file, new_game_file, league_id, full_date, week):
    # 1. Extract year from the full date string
    year = full_date.split("-")[0]

    # 2. Load JSON
    data = load_json(master_file)

    # 3. Ensure the week bucket exists and set the date
    games = ensure_week_bucket(data, league_id, year, week, full_date)

    # 4. Grab the season node
    season_id = f"{league_id}S{year}"
    season = data["leagues by ID"][league_id]["seasons by ID"][season_id]

    # 5. Build alias → team_id mapping from season teams
    alias_to_id = {}
    teams_section = season.get("teams", [])
    for team in teams_section:
        tid = team.get("team_id")
        name = team.get("name", "").strip().lower()
        if tid and name:
            alias_to_id[name] = tid
        for alias in team.get("aliases", []):
            alias_to_id[alias.strip().lower()] = tid

    # 6. Use a temp ID for context while normalizing
    temp_id = f"S{year}W{week}G?"

    # 7. Load the new game file
    new_game_data = load_json(new_game_file)
    if not isinstance(new_game_data, dict):
        raise ValueError("new_game.json must be an object")
    if not {"team_a", "team_b"} <= set(new_game_data.keys()):
        raise ValueError("new_game.json must contain 'team_a' and 'team_b'")

    # 8. Strip out any 'score' fields
    new_game_data["team_a"].pop("score", None)
    new_game_data["team_b"].pop("score", None)

    # 9. Normalize both teams
    team_a, warn_a = normalize_team(new_game_data["team_a"], "team_a", temp_id, alias_to_id)
    team_b, warn_b = normalize_team(new_game_data["team_b"], "team_b", temp_id, alias_to_id)

    # 10. Recalculate totals
    calculate_team_totals(team_a)
    calculate_team_totals(team_b)

    # 11. Update records if needed (now season-scoped!)
    maybe_update_team_record(season, team_a)
    maybe_update_team_record(season, team_b)

    # 12. Build the final game entry
    game_id = generate_game_id(games,league_id, year, week)
    new_game = {"game_id": game_id, "team_a": team_a, "team_b": team_b}

    # 13. Verify and fail fast on issues
    issues = verify_game(new_game, game_id)
    if issues:
        out = "\n - " + "\n - ".join(issues)
        raise ValueError(f"Verification FAILED:{out}")

    # 14. Print any non-fatal warnings
    for w in (warn_a + warn_b):
        print(w)

    # 15. Check for duplicate matchups
    for g in games:
        if g.get("team_a", {}).get("name") == team_a["name"] and g.get("team_b", {}).get("name") == team_b["name"]:
            raise ValueError(f"Duplicate matchup in Week {week}: {team_a['name']} vs {team_b['name']}")

    # 16. Save and log
    games.append(new_game)
    save_json(master_file, data)
    print(f"✅ Game {game_id} added for Week {week}, {year} ({full_date}): "
          f"{team_a['name']} vs {team_b['name']} → saved to {master_file}")

def preview_remove(games, game_id, season_id, week):
    idx = next((i for i, g in enumerate(games) if g.get("game_id") == game_id), None)
    if idx is None:
        raise ValueError(f"No game with id '{game_id}' found in Week {week}.")

    g = games[idx]
    a = g.get("team_a", {}).get("name", "<unknown A>")
    b = g.get("team_b", {}).get("name", "<unknown B>")
    print(f"🔎 Preview remove {game_id} (Week {week}): {a} vs {b}")

    if idx < len(games) - 1:
        print("  • Reindex plan for following games:")
        for j in range(idx + 1, len(games)):
            old = games[j].get("game_id")
            new = f"{season_id}W{week}G{j+1}"
            print(f"    - {old} → {new}")
    else:
        print("  • No subsequent games to reindex.")


def apply_remove(master_file, data, games, season_id, year, week, game_id):
    idx = next((i for i, g in enumerate(games) if g.get("game_id") == game_id), None)
    if idx is None:
        raise ValueError(f"No game with id '{game_id}' found in Week {week}.")

    removed = games.pop(idx)

    # Reindex remaining games with the correct season prefix
    for j, g in enumerate(games, start=1):
        g["game_id"] = f"{season_id}W{week}G{j}"

    save_json(master_file, data)

    a = removed.get("team_a", {}).get("name", "<unknown A>")
    b = removed.get("team_b", {}).get("name", "<unknown B>")
    print(f"🗑️ Removed {game_id} (Week {week}): {a} vs {b} → saved to {master_file}")
    if idx < len(games):
        print("🔁 Reindexed subsequent game IDs successfully.")


def remove_game(master_file, game_id, non_interactive=False):
    data = load_json(master_file)

    # Parse league, season, week from game_id
    try:
        league_id = game_id.split("S")[0]           # L001
        season_id = game_id.split("W")[0]           # L001S2025
        year = season_id[-4:]                       # 2025
        week = int(game_id.split("W")[1].split("G")[0])  # 3
    except Exception:
        raise ValueError(f"Invalid game_id format: {game_id}")

    # Clean checks instead of KeyErrors
    leagues = data.get("leagues by ID", {})
    if league_id not in leagues:
        raise ValueError(f"League '{league_id}' not found in master file")

    seasons = leagues[league_id].get("seasons by ID", {})
    if season_id not in seasons:
        raise ValueError(f"Season '{season_id}' not found in league {league_id}")

    games_root = seasons[season_id].get("games", {})
    weeks = games_root.get("weeks", {})
    if str(week) not in weeks:
        raise ValueError(f"Week {week} not found for season {season_id}")

    games = weeks[str(week)]["games"]

    # Preview removal
    preview_remove(games, game_id, season_id, week)

    confirm = "y" if non_interactive else input("Type 'y' to confirm removal and reindexing: ").strip().lower()
    if confirm == "y":
        apply_remove(master_file, data, games, season_id, year, week, game_id)
    else:
        print("❎ Removal canceled. No changes written.")

# --------------------------------------
# CLI
# --------------------------------------
def usage():
    print("Usage:")
    print("  Add:    python add_remove_game.py add <master_file.json> <new_game.json> <league_id> <YYYY-MM-DD> <week>")
    print("  Remove: python add_remove_game.py remove <master_file.json> <game_id> [--yes]")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()

    cmd = sys.argv[1].lower()

    if cmd == "add":
        if len(sys.argv) != 7:
            usage()
        _, _, master_file, new_game_file, league_id, full_date, week = sys.argv
        try:
            add_game(master_file, new_game_file, league_id, full_date, int(week))
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif cmd == "remove":
        if len(sys.argv) not in (4, 5):
            usage()

        master_file = sys.argv[2]
        game_id = sys.argv[3]
        non_interactive = (len(sys.argv) == 5 and sys.argv[4] == "--yes")

        try:
            remove_game(master_file, game_id, non_interactive=non_interactive)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    else:
        usage()
