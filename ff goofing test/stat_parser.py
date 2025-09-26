import csv
import json
import argparse
import re
from collections import OrderedDict

# ---------- helpers ----------

seen_ids = {}

def make_player_id(name, position):
    """Generate a stable player_id from name + position (season mode only)."""
    parts = name.split()
    if len(parts) == 0:
        base = "unknown"
    else:
        base = (parts[0] + parts[-1]).lower()
    base = re.sub(r'[^a-z0-9]', '', base)
    pid = f"{base}_{position.lower()}"

    if pid in seen_ids:
        other_name = seen_ids[pid]
        if other_name != name:
            print(f"⚠️ Duplicate player_id detected: {pid}")
            print(f" - Existing: {other_name}")
            print(f" - New:      {name}")
            confirm = input("Proceed and append suffix to resolve? [y/N]: ").strip().lower()
            if confirm != "y":
                print("❌ Aborted due to duplicate ID.")
                raise SystemExit(1)
            counter = 2
            new_pid = f"{pid}{counter}"
            while new_pid in seen_ids:
                counter += 1
                new_pid = f"{pid}{counter}"
            pid = new_pid
            print(f"✅ Resolved duplicate, assigned ID: {pid}")
    seen_ids[pid] = name
    return pid

def safe_int(val, default=0):
    try:
        return int(val)
    except:
        return default

def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default

expected_pos = {
    "passing": ["QB"],
    "rushing": ["RB", "FB"],
    "receiving": ["WR", "TE"],
    "defensive": ["CB", "LB", "S", "DL", "DE"],
    "kicking": ["K"],
    "punting": ["P"],
}

# ---------- SEASON PARSING ----------
def parse_season_csv(file_path, stat_type, season):
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith(("Rk,", "Rk\t")):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("No header row found in season file.")

    clean_lines = lines[header_idx:]
    delimiter = "\t" if "\t" in clean_lines[0] else ","
    reader = csv.DictReader(clean_lines, delimiter=delimiter)
    print("🔍 Detected headers (season):", reader.fieldnames)

    players = []
    for row in reader:
        name = (row.get("Player") or "").strip()
        pos = (row.get("Pos") or "").strip().upper()
        if not name or name.lower().startswith("league average"):
            continue

        team = (row.get("Team") or "").strip()
        pid = make_player_id(name, pos)

        player = {
            "player_id": pid,
            "name": name,
            "team": team,
            "position": pos,
            "age": safe_int(row.get("Age")),
            "games_played": safe_int(row.get("G")),
            "starts": safe_int(row.get("GS")),
            "season": season,
            "week": None,
        }

        if stat_type == "passing":
            record = row.get("QBrec") or row.get("Record") or "0-0-0"
            player["record"] = record
            player.update({
                "completions": safe_int(row.get("Cmp")),
                "attempts": safe_int(row.get("Att")),
                "cmp_pct": safe_float(row.get("Cmp%")),
                "pass_yards": safe_int(row.get("Yds")),
                "pass_td": safe_int(row.get("TD")),
                "interceptions": safe_int(row.get("Int")),
                "qb_rating": safe_float(row.get("Rate")),
            })
        elif stat_type == "rushing":
            player.update({
                "rush_attempts": safe_int(row.get("Att")),
                "rush_yards": safe_int(row.get("Yds")),
                "rush_avg": safe_float(row.get("Y/A") or row.get("Avg")),
                "rush_td": safe_int(row.get("TD")),
            })
        elif stat_type == "receiving":
            player.update({
                "targets": safe_int(row.get("Tgt")),
                "receptions": safe_int(row.get("Rec")),
                "rec_yards": safe_int(row.get("Yds")),
                "rec_avg": safe_float(row.get("Y/R") or row.get("Avg")),
                "rec_td": safe_int(row.get("TD")),
                "long": safe_int(row.get("Lng")),
            })

        players.append(player)

    return players

# ---------- WEEKLY PARSING ----------
def parse_weekly_csv(file_path, stat_type, players_registry, season, week):
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith(("Rk,", "Rk\t")):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("No header row found in weekly file.")

    clean_lines = lines[header_idx:]
    delimiter = "\t" if "\t" in clean_lines[0] else ","
    reader = csv.DictReader(clean_lines, delimiter=delimiter)
    print("🔍 Detected headers (weekly):", reader.fieldnames)

    players = []
    for row in reader:
        name = (row.get("Player") or "").strip()
        if not name or name.lower().startswith("league average"):
            continue

        team = (row.get("Team") or "").strip()
        pid = None
        for reg_pid, info in players_registry.items():
            if info["name"] == name:
                pid = reg_pid
                break
        if not pid:
            print(f"⚠️ No player_id found in Players registry for: {name}")
            confirm = input("Proceed by skipping this player? [y/N]: ").strip().lower()
            if confirm != "y":
                print("❌ Aborted due to missing player_id.")
                raise SystemExit(1)
            continue

        pos = players_registry[pid]["position"]

        player = {
            "player_id": pid,
            "name": name,
            "team": team,
            "position": pos,
            "age": safe_int(row.get("Age").split("-")[0]) if row.get("Age") else 0,
            "season": season,
            "week": int(week.replace("Week", "")),
            "week_id": week,
            "game_date": row.get("Date"),
            "result": row.get("Result"),
        }

        if stat_type == "passing":
            player.update({
                "completions": safe_int(row.get("Cmp")),
                "attempts": safe_int(row.get("Att")),
                "cmp_pct": safe_float(row.get("Cmp%")),
                "pass_yards": safe_int(row.get("YdsV")),
                "pass_td": safe_int(row.get("TD")),
                "interceptions": safe_int(row.get("Int")),
                "qb_rating": safe_float(row.get("Rate")),
            })
        elif stat_type == "rushing":
            player.update({
                "rush_attempts": safe_int(row.get("Att")),
                "rush_yards": safe_int(row.get("YdsV")),
                "rush_avg": safe_float(row.get("Y/A") or row.get("Avg")),
                "rush_td": safe_int(row.get("TD")),
            })
        elif stat_type == "receiving":
            player.update({
                "targets": safe_int(row.get("Tgt")),
                "receptions": safe_int(row.get("Rec")),
                "rec_yards": safe_int(row.get("YdsV")),
                "rec_avg": safe_float(row.get("Y/R") or row.get("Avg")),
                "rec_td": safe_int(row.get("TD")),
                "long": safe_int(row.get("Lng")),
            })

        players.append(player)

    return players

# ---------- MAIN ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse stat CSV into fantasy.json")
    parser.add_argument("--season", required=True, help="Season year")
    parser.add_argument("--week", help="Week number (for weekly stats)")
    parser.add_argument("--date", help="Week date in MM/DD/YYYY format")
    parser.add_argument("--file", required=True, help="CSV stat file to parse")
    parser.add_argument("stat_type", choices=expected_pos.keys(), help="Stat category")
    args = parser.parse_args()

    season = f"S{args.season}"
    file_path = args.file
    stat_type = args.stat_type.lower()

    with open("fantasy.json", "r", encoding="utf-8") as f:
        fantasy_data = json.load(f)

    players_registry = fantasy_data.setdefault("Players", {})

    if args.week:
        week = f"Week{args.week}"
        parsed_stats = parse_weekly_csv(file_path, stat_type, players_registry, season, week)
        season_path = fantasy_data.setdefault("Raw Stats", {}).setdefault("season by ID", {}).setdefault(season, OrderedDict())
        week_path = season_path.setdefault(week, {})
        week_path["week_id"] = week
        category_key = stat_type.capitalize()

        
        if category_key in week_path:
            print(f"⚠️ {category_key} stats already exist for {season} {week}.")
            confirm = input("Overwrite with new data? [y/N]: ").strip().lower()
            if confirm != "y":
                print("❌ Aborted.")
                raise SystemExit(1)

        week_path[category_key] = {p["player_id"]: p for p in parsed_stats}
        print(f"✅ Updated {season} {week} with {len(parsed_stats)} {stat_type} players.")

    else:
        parsed_stats = parse_season_csv(file_path, stat_type, season)
        for p in parsed_stats:
            pid = p["player_id"]
            if pid not in players_registry:
                players_registry[pid] = {
                    "name": p["name"],
                    "position": p["position"],
                    "team": p["team"],
                    "age": p["age"],
                }
            else:
                players_registry[pid]["team"] = p["team"]
                players_registry[pid]["age"] = p["age"]

        season_path = fantasy_data.setdefault("Raw Stats", {}).setdefault("season by ID", {}).setdefault(season, OrderedDict())
        category_key = stat_type.capitalize()
        totals_path = season_path.setdefault("Totals", {})
        totals_path["season_id"] = season
        totals_path["stat_type"] = stat_type

        # ⚠️ Warn on duplicate overwrite (season totals)
        if category_key in totals_path:
            print(f"⚠️ {category_key} Totals already exist for {season}.")
            confirm = input("Overwrite with new data? [y/N]: ").strip().lower()
            if confirm != "y":
                print("❌ Aborted to avoid overwrite.")
                raise SystemExit(1)

        totals_path[category_key] = {p["player_id"]: p for p in parsed_stats}
        print(f"✅ Updated {season} Totals with {len(parsed_stats)} {stat_type} players.")

    # enforce ordering: Weeks first, then Totals
    for season_id, season_data in fantasy_data.get("Raw Stats", {}).get("season by ID", {}).items():
        ordered = OrderedDict()
        for k in sorted([wk for wk in season_data.keys() if wk.startswith("Week")], key=lambda x: int(x.replace("Week", ""))):
            ordered[k] = season_data[k]
        if "Totals" in season_data:
            ordered["Totals"] = season_data["Totals"]
        fantasy_data["Raw Stats"]["season by ID"][season_id] = ordered

    with open("fantasy.json", "w", encoding="utf-8") as f:
        json.dump(fantasy_data, f, indent=2)
