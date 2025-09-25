import json
import sys
import shutil
from pathlib import Path

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def migrate_add_team_ids(master_file, year):
    data = load_json(master_file)

    seasons = data.get("seasons", {})
    season = seasons.get(str(year))
    if not season:
        print(f"❌ Year {year} not found in seasons.")
        sys.exit(1)

    teams = season.get("teams")
    if not teams:
        print(f"❌ No 'teams' block found under {year}.")
        sys.exit(1)

    # Build alias map
    alias_to_id = {}
    for t in teams:
        tid = t["team_id"]
        alias_to_id[t["name"].lower()] = tid
        for alias in t.get("aliases", []):
            alias_to_id[alias.lower()] = tid

    unmatched = set()
    changes = 0

    # Iterate over weeks/games
    for week, week_data in season.get("weeks", {}).items():
        for game in week_data.get("games", []):
            for side in ("team_a", "team_b"):
                team = game.get(side, {})
                if "team_id" not in team:
                    name = team.get("name", "").lower()
                    tid = alias_to_id.get(name)
                    if tid:
                        team["team_id"] = tid
                        changes += 1
                    else:
                        unmatched.add(team.get("name"))

    if changes > 0:
        backup = Path(master_file).with_suffix(".bak")
        shutil.copy(master_file, backup)
        save_json(master_file, data)
        print(f"📦 Backup saved to {backup}")
        print(f"✅ Updated {changes} teams with team_id in {year}.")
    else:
        print("ℹ️ No changes written (everything already in sync).")

    if unmatched:
        print(f"⚠️ Unmatched teams: {sorted(unmatched)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python migrate_add_team_ids.py fantasy.json <year>")
        sys.exit(1)

    migrate_add_team_ids(sys.argv[1], sys.argv[2])
