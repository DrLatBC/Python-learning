import json
import argparse
from datetime import datetime

# ----------------------
# Helpers
# ----------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def parse_datetime(year, date_str, time_str):
    """Convert '09-24' and '7:41 pm' into a datetime for sorting."""
    return datetime.strptime(f"{year}-{date_str} {time_str}", "%Y-%m-%d %I:%M %p")

def reindex_transactions(transactions):
    """Regenerate transaction IDs sequentially, oldest first."""
    for i, t in enumerate(transactions, start=1):
        t["transaction_id"] = f"T{i:05d}"
    return transactions

def _norm(s):
    return (s or "").strip().lower()

def get_team_objects(data, year):
    """Return the list of team objects for the season, no matter the key name."""
    season = data.get("seasons", {}).get(str(year), {})
    teams = season.get("team_aliases")
    if isinstance(teams, list) and (not teams or isinstance(teams[0], dict)):
        return teams
    teams = season.get("teams")
    if isinstance(teams, list) and (not teams or isinstance(teams[0], dict)):
        return teams
    return []

def build_alias_map(data, year):
    """Build alias -> team_id mapping from team objects (name, aliases, abbrev)."""
    alias_to_id = {}
    for team in get_team_objects(data, year):
        tid = team.get("team_id")
        if not tid:
            continue
        # Primary name
        name = _norm(team.get("name"))
        if name:
            alias_to_id[name] = tid
        # Aliases
        for alias in team.get("aliases", []):
            a = _norm(alias)
            if a:
                alias_to_id[a] = tid
        # Abbrev
        ab = _norm(team.get("abbrev"))
        if ab:
            alias_to_id[ab] = tid
    return alias_to_id

def resolve_team_id(alias_to_id, team_name):
    if not team_name:
        return None
    return alias_to_id.get(_norm(team_name))

def alias_exists_globally(data, year, alias, owner_team_id=None):
    """Check if alias already exists on another team."""
    a_norm = _norm(alias)
    for team in get_team_objects(data, year):
        tid = team.get("team_id")
        if owner_team_id and tid == owner_team_id:
            continue
        if _norm(team.get("name")) == a_norm:
            return True
        for al in team.get("aliases", []) or []:
            if _norm(al) == a_norm:
                return True
    return False

def find_team_by_name_or_alias(data, year, target_name, target_abbrev=None):
    """Return team dict whose name/alias/abbrev matches target."""
    t_norm = _norm(target_name)
    a_norm = _norm(target_abbrev) if target_abbrev else None
    for team in get_team_objects(data, year):
        if _norm(team.get("name")) == t_norm:
            return team
        if a_norm and _norm(team.get("abbrev")) == a_norm:
            return team
        for al in team.get("aliases", []) or []:
            if _norm(al) == t_norm:
                return team
    return None

def apply_team_update(data, year, update):
    new_name   = update.get("new_name")
    old_name   = update.get("old_name")
    old_abbrev = update.get("old_abbrev")

    if not new_name:
        return

    team = find_team_by_name_or_alias(data, year, new_name)
    if not team:
        print(f"⚠️ team_update: could not find team for new_name='{new_name}'")
        return

    team.setdefault("aliases", [])

    # ✅ Always update to the new name
    if team.get("name") != new_name:
        team["name"] = new_name

    # ✅ Add old name into aliases (if safe)
    if old_name and _norm(old_name) not in [_norm(a) for a in team["aliases"]]:
        team["aliases"].append(old_name)

    # ✅ Add old abbrev into aliases too
    if old_abbrev and _norm(old_abbrev) not in [_norm(a) for a in team["aliases"]]:
        team["aliases"].append(old_abbrev)

def is_duplicate(existing, new_entry):
    """Return True if new_entry matches an existing transaction."""
    keys_to_check = ["date", "time", "type", "method"]

    for k in keys_to_check:
        if existing.get(k) != new_entry.get(k):
            return False

    # Prefer team_id match
    if existing.get("team_id") or new_entry.get("team_id"):
        if existing.get("team_id") != new_entry.get("team_id"):
            return False
    else:
        if existing.get("team_name") != new_entry.get("team_name"):
            return False

    if existing.get("added") != new_entry.get("added"):
        return False
    if existing.get("dropped") != new_entry.get("dropped"):
        return False

    if new_entry.get("type") == "team_update":
        for k in ("old_name", "new_name", "old_abbrev", "new_abbrev"):
            if existing.get(k) != new_entry.get(k):
                return False

    return True

# ----------------------
# Core logic
# ----------------------

def add_transactions(data, new_data, year):
    transactions = data["seasons"][str(year)]["transactions"]

    flat = []
    for t in transactions:
        dt = parse_datetime(year, t["date"], t["time"])
        flat.append((dt, t))

    alias_to_id = build_alias_map(data, year)

    added_count = 0  # ✅ track real additions

    for entry in new_data.get("transactions", []):
        for e in entry["entries"]:
            e["date"] = entry["date"]

            if e.get("team_name"):
                tid = resolve_team_id(alias_to_id, e["team_name"])
                if tid:
                    e["team_id"] = tid
                else:
                    print(f"⚠️ Unknown team '{e['team_name']}' @ {e['date']} {e.get('time','')}")

            if any(is_duplicate(t, e) for _, t in flat):
                print(f"⚠️ Skipped duplicate transaction for {e.get('team_name')} at {e['date']} {e['time']}")
                continue

            dt = parse_datetime(year, entry["date"], e["time"])
            flat.append((dt, e))
            added_count += 1  # ✅ increment only if truly added

            if e.get("type") == "team_update":
                apply_team_update(data, year, e)
                alias_to_id = build_alias_map(data, year)

    flat.sort(key=lambda x: x[0])
    sorted_entries = [t for _, t in flat]
    reindex_transactions(sorted_entries)

    data["seasons"][str(year)]["transactions"] = sorted_entries
    return added_count

def remove_transactions(data, year, ids_or_range):
    year = str(year)

    if "seasons" not in data or year not in data["seasons"] or "transactions" not in data["seasons"][year]:
        raise ValueError(f"No transactions found for season {year}")

    transactions = data["seasons"][year]["transactions"]

    # Expand input into a list of IDs
    ids_to_remove = set()
    if "-" in ids_or_range:  # range form
        start, end = ids_or_range.split("-")
        start_num = int(start[1:])
        end_num = int(end[1:])
        for i in range(start_num, end_num + 1):
            ids_to_remove.add(f"T{i:05d}")
    elif "," in ids_or_range:  # multiple IDs
        for tid in ids_or_range.split(","):
            ids_to_remove.add(tid.strip())
    else:  # single ID
        ids_to_remove.add(ids_or_range)

    # Filter out removed transactions
    remaining = [t for t in transactions if t.get("transaction_id") not in ids_to_remove]

    # Reindex after removal
    reindex_transactions(remaining)

    data["seasons"][year]["transactions"] = remaining

    print(f"🗑️ Removed {len(ids_to_remove)} transaction(s) from season {year}.")
    return True

# ----------------------
# Main CLI
# ----------------------

def main():
    parser = argparse.ArgumentParser(description="Add or remove transactions from master fantasy file.")
    parser.add_argument("master_file", help="Path to master fantasy.json file")
    parser.add_argument("mode", choices=["add", "remove"], help="Operation mode: add or remove")
    parser.add_argument("target", help="Path to new transactions file (for add) OR transaction_id(s)/range (for remove)")
    parser.add_argument("year", type=int, help="Season year, e.g. 2025")

    args = parser.parse_args()
    data = load_json(args.master_file)

    if "seasons" not in data:
        data["seasons"] = {}
    if str(args.year) not in data["seasons"]:
        data["seasons"][str(args.year)] = {}
    if "transactions" not in data["seasons"][str(args.year)]:
        data["seasons"][str(args.year)]["transactions"] = []

    if args.mode == "add":
        new_data = load_json(args.target)
        count = add_transactions(data, new_data, args.year)
        save_json(args.master_file, data)
        print(f"✅ Added {count} transaction groups into {args.master_file} for {args.year}.")
    elif args.mode == "remove":
        removed = remove_transactions(data, args.year, args.target)
        if removed:
            save_json(args.master_file, data)

if __name__ == "__main__":
    main()
