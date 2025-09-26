#!/usr/bin/env python3
import json
import sys
import os

def load_json(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} not found")
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def migrate_ids(data, dry_run=False, debug=False):
    mismatches = []

    leagues = data.get("leagues", {})
    for league_id, league in leagues.items():
        seasons = league.get("seasons BY ID", {})
        for season_id, season in seasons.items():
            games = season.get("games", {})
            weeks = games.get("weeks", {})

            for week, wkdata in weeks.items():
                week_games = wkdata.get("games", [])
                for idx, g in enumerate(week_games, start=1):
                    old_id = g.get("game_id", "")
                    expected_id = f"{season_id}W{week}G{idx}"

                    if debug:
                        print(f"[DEBUG] {season_id} Week {week} Game {idx}: old='{old_id}' expected='{expected_id}'")

                    if old_id != expected_id:
                        mismatches.append((season_id, week, old_id, expected_id))
                        if not dry_run:
                            g["game_id"] = expected_id

    return mismatches

def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate_game_ids.py <fantasy.json> [--dry-run]")
        sys.exit(1)

    filename = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    data = load_json(filename)

    # 👇 run with debug=True so we print all IDs
    mismatches = migrate_ids(data, dry_run=dry_run, debug=True)

    if mismatches:
        for season_id, week, old_id, expected_id in mismatches:
            print(f"  - {old_id} → {expected_id} (season={season_id}, week={week})")
        if dry_run:
            print("🔎 Dry run complete. No changes were written.")
        else:
            save_json(filename, data)
            print(f"✅ Migrated {len(mismatches)} game IDs and saved to {filename}")
    else:
        print("✨ All game IDs are already consistent.")


if __name__ == "__main__":
    main()
