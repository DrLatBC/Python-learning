import json
import sys
import os

# ---------- IO ----------
def load_json(filename):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        return {"seasons": {}}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------- Normalization helpers ----------
def round_points(value):
    try:
        if value is None:
            return 0.0
        return round(float(value), 2)
    except (ValueError, TypeError):
        return 0.0

def normalize_opponent(opponent: str) -> str:
    if isinstance(opponent, str) and opponent.startswith("@"):
        return "@" + opponent[1:].upper()
    return opponent

def normalize_player_entry(entry: dict) -> dict:
    if not isinstance(entry, dict):
        return {"player": {}}

    player = entry.get("player", {})
    if not isinstance(player, dict):
        player = {}

    # Normalize fields
    player["name"] = (player.get("name") or "").strip()
    player["team"] = (player.get("team") or "").upper()
    player["position"] = (player.get("position") or "").upper()
    player["opponent"] = normalize_opponent(player.get("opponent", ""))
    player["proj"] = round_points(player.get("proj"))
    player["fpts"] = round_points(player.get("fpts"))

    entry["player"] = player
    # Preserve slot if present
    if "slot" in entry:
        entry["slot"] = entry["slot"]
    return entry

def is_stub_entry(entry: dict) -> bool:
    """
    A stub is anything with an empty/whitespace player name.
    (We don't drop real players who just scored 0.0.)
    """
    if not isinstance(entry, dict):
        return True
    player = entry.get("player", {})
    if not isinstance(player, dict):
        return True
    name = (player.get("name") or "").strip()
    team = (player.get("team") or "").strip()
    position = (player.get("position") or "").strip()

    # Classic placeholders are totally empty
    if name == "" and team == "" and position == "":
        return True

    # Empty name counts as stub even if numbers are present
    if name == "":
        return True

    return False

def clean_slot_list(entries):
    cleaned = []
    for e in entries or []:
        e = normalize_player_entry(e)
        if not is_stub_entry(e):
            cleaned.append(e)
    return cleaned

def compute_bench_totals(bench):
    proj = sum((p.get("player", {}).get("proj", 0.0) or 0.0) for p in bench)
    fpts = sum((p.get("player", {}).get("fpts", 0.0) or 0.0) for p in bench)
    return round_points(proj), round_points(fpts)

def normalize_team(team: dict) -> dict:
    team = dict(team or {})
    team["name"] = (team.get("name") or "").strip()
    team["manager"] = (team.get("manager") or "").strip()
    team["record"] = (team.get("record") or "").strip()
    team["score"] = round_points(team.get("score"))

    # Normalize and drop stubs across all lists
    starters = clean_slot_list(team.get("starters", []))
    bench = clean_slot_list(team.get("bench", []))
    ir = clean_slot_list(team.get("ir", []))

    team["starters"] = starters
    team["bench"] = bench
    team["ir"] = ir

    totals = dict(team.get("totals") or {})
    totals["proj"] = round_points(totals.get("proj"))
    totals["fpts"] = round_points(totals.get("fpts"))

    # Bench totals
    bproj, bfpts = compute_bench_totals(bench)
    totals["bench_proj"] = bproj
    totals["bench_fpts"] = bfpts
    team["totals"] = totals

    # If score is effectively null, backfill from totals.fpts (if > 0)
    if (team["score"] == 0.0) and totals.get("fpts", 0.0) > 0.0:
        team["score"] = totals["fpts"]

    return team

# ---------- Main op ----------
def add_game(master_file, new_game_file, year, week):
    data = load_json(master_file)
    new_game_data = load_json(new_game_file)

    # Allow either a single game object or a {"games":[...]} wrapper (take the first)
    if "home_team" not in new_game_data or "away_team" not in new_game_data:
        if isinstance(new_game_data.get("games"), list) and new_game_data["games"]:
            new_game_data = new_game_data["games"][0]
        else:
            raise ValueError(
                f"Invalid new_game file. Expected 'home_team' and 'away_team' keys. Found: {list(new_game_data.keys())}"
            )

    # Normalize teams (this also drops stubs)
    home_team = normalize_team(new_game_data["home_team"])
    away_team = normalize_team(new_game_data["away_team"])

    # Ensure season/week scaffolding
    seasons = data.setdefault("seasons", {})
    season = seasons.setdefault(str(year), {"weeks": {}})
    weeks = season.setdefault("weeks", {})
    week_bucket = weeks.setdefault(str(week), {"games": []})

    games = week_bucket["games"]

    # Duplicate check (same names in same week)
    for g in games:
        if g["home_team"]["name"] == home_team["name"] and g["away_team"]["name"] == away_team["name"]:
            raise ValueError(f"Duplicate game: {home_team['name']} vs {away_team['name']} already exists in Week {week}, {year}.")

    # Assign next game_id
    game_id = f"W{week}G{len(games) + 1}"

    # Append and save
    games.append({
        "home_team": home_team,
        "away_team": away_team,
        "game_id": game_id
    })
    save_json(master_file, data)

    print(
        f"✅ Game {game_id} added for Week {week}, {year}: "
        f"{home_team['name']} vs {away_team['name']} → saved to {master_file}"
    )

# ---------- CLI ----------
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python add_game.py <master_file.json> <new_game.json> <year> <week>")
        sys.exit(1)

    master_file = sys.argv[1]
    new_game_file = sys.argv[2]
    year = sys.argv[3]
    week = sys.argv[4]

    try:
        add_game(master_file, new_game_file, year, week)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
