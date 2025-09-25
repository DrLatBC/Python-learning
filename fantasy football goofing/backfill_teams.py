import json
import argparse

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_team_objects(data, year):
    """Return the list of team objects for the season, no matter the key name."""
    season = data.get("seasons", {}).get(str(year), {})
    # Prefer team_aliases if present
    teams = season.get("team_aliases")
    if isinstance(teams, list) and teams and isinstance(teams[0], dict):
        return teams
    # Fall back to teams
    teams = season.get("teams")
    if isinstance(teams, list) and (not teams or isinstance(teams[0], dict)):
        return teams
    return []

def build_alias_map(data, year):
    """Build alias -> team_id mapping from team objects (name, aliases, abbrev)."""
    alias_to_id = {}
    teams = get_team_objects(data, year)
    for team in teams:
        tid = team.get("team_id")
        if not tid:
            continue
        # primary name
        name = (team.get("name") or "").strip().lower()
        if name:
            alias_to_id[name] = tid
        # aliases array
        for alias in team.get("aliases", []):
            a = (alias or "").strip().lower()
            if a:
                alias_to_id[a] = tid
        # abbrev (if present)
        ab = (team.get("abbrev") or "").strip().lower()
        if ab:
            alias_to_id[ab] = tid
    return alias_to_id

def backfill_team_ids(data, year, debug=False):
    year = str(year)
    season = data.get("seasons", {}).get(year, {})
    txs = season.get("transactions", [])
    if not isinstance(txs, list):
        raise ValueError(f"No transactions list found for season {year}")

    alias_to_id = build_alias_map(data, year)
    if debug:
        print(f"DEBUG: alias map size = {len(alias_to_id)}")
        if alias_to_id:
            sample = list(alias_to_id.items())[:10]
            print("DEBUG: alias samples:", sample)

    updated = 0
    skipped = 0
    for tx in txs:
        # only fill when missing
        if tx.get("team_id"):
            continue
        team_name = (tx.get("team_name") or "").strip().lower()
        if not team_name:
            skipped += 1
            continue
        tid = alias_to_id.get(team_name)
        if tid:
            tx["team_id"] = tid
            updated += 1
        else:
            print(f"⚠️ Could not resolve team '{tx.get('team_name')}' in {tx.get('date')} {tx.get('time')} (id {tx.get('transaction_id')})")
            skipped += 1

    return updated, skipped

def main():
    parser = argparse.ArgumentParser(description="Backfill team_id in transactions based on team aliases/teams.")
    parser.add_argument("master_file", help="Path to master fantasy.json file")
    parser.add_argument("year", type=int, help="Season year, e.g. 2025")
    parser.add_argument("--debug", action="store_true", help="Print alias map info")
    args = parser.parse_args()

    data = load_json(args.master_file)
    updated, skipped = backfill_team_ids(data, args.year, debug=args.debug)
    save_json(args.master_file, data)

    print(f"✅ Backfilled {updated} transaction(s) with team_id.")
    if skipped:
        print(f"⚠️ Skipped {skipped} transaction(s) (unknown team names).")

if __name__ == "__main__":
    main()
