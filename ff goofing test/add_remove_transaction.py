import json
import argparse
import re
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

def season_id_for(league_id: str, year: int | str) -> str:
    return f"{league_id}S{int(year)}"

def get_season_node(data: dict, league_id: str, year: int | str, create: bool = False) -> dict:
    year = int(year)
    sid = season_id_for(league_id, year)

    if create:
        leagues = data.setdefault("leagues by ID", {})
        league = leagues.setdefault(league_id, {"league_id": league_id})
        seasons = league.setdefault("seasons by ID", {})
        return seasons.setdefault(sid, {"season_id": sid, "year": year})

    # read-only / validate path
    leagues = data.get("leagues by ID", {})
    if league_id not in leagues:
        raise ValueError(f"League '{league_id}' not found (expected at data['leagues by ID']['{league_id}']).")

    seasons = leagues[league_id].get("seasons by ID", {})
    if sid not in seasons:
        raise ValueError(f"Season '{sid}' not found (expected at data['leagues by ID']['{league_id}']['seasons by ID']['{sid}']).")

    return seasons[sid]

def get_transactions_list(season: dict, create: bool = False) -> list:
    """
    Support both shapes:
      - season["transactions"] is a list
      - season["transactions"] is an object with .items (list)
    """
    if "transactions" not in season:
        if not create:
            return []
        season["transactions"] = []

    tx = season["transactions"]

    # normalize to a plain list internally
    if isinstance(tx, dict):
        if "items" not in tx:
            if not create:
                return []
            tx["items"] = []
        return tx["items"]

    if isinstance(tx, list):
        return tx

    # if it’s something unexpected, normalize to list
    if create:
        season["transactions"] = []
        return season["transactions"]

    return []

def parse_datetime(year, date_str, time_str):
    """Convert '09-24' and '7:41 pm' into a datetime for sorting."""
    return datetime.strptime(f"{year}-{date_str} {time_str}", "%Y-%m-%d %I:%M %p")

def reindex_transactions(transactions, league_id, year):
    """Regenerate transaction IDs sequentially, oldest first, with league/season prefix."""
    season_id = season_id_for(league_id, year)
    for i, t in enumerate(transactions, start=1):
        t["transaction_id"] = f"{season_id}T{i:05d}"
    return transactions

def _norm(s):
    return (s or "").strip().lower()

def get_team_objects(data, league_id, year):
    season = get_season_node(data, league_id, year, create=False)
    # prefer "teams", fallback to "team_aliases"
    teams = season.get("teams")
    if isinstance(teams, list):
        return teams
    teams = season.get("team_aliases")
    if isinstance(teams, list):
        return teams
    return []

def build_alias_map(data, league_id, year):
    alias_to_id = {}
    for team in get_team_objects(data, league_id, year):
        tid = team.get("team_id")
        if not tid:
            continue
        name = _norm(team.get("name"))
        if name:
            alias_to_id[name] = tid
        for alias in team.get("aliases", []) or []:
            a = _norm(alias)
            if a:
                alias_to_id[a] = tid
        ab = _norm(team.get("abbrev"))
        if ab:
            alias_to_id[ab] = tid
    return alias_to_id

TX_ID_RE = re.compile(r"^(L\d{3}S\d{4})T(\d{5})$")

def next_tx_id(transactions, league_id, year) -> str:
    season_id = season_id_for(league_id, year)
    max_n = 0
    for t in transactions:
        tid = str(t.get("transaction_id", ""))
        m = TX_ID_RE.match(tid)
        if m:
            max_n = max(max_n, int(m.group(2)))  # group(2) is the number part
    return f"{season_id}T{max_n + 1:05d}"


def validate_tx_ids_for_remove(transactions: list, ids: list[str]) -> list[int]:
    """Return sorted indices to delete; raise on bad IDs."""
    id_to_idx = { str(t.get("transaction_id", "")): i for i, t in enumerate(transactions) }
    bad = [tid for tid in ids if not TX_ID_RE.match(tid)]
    if bad:
        raise ValueError(
            f"Invalid transaction_id format: {', '.join(bad)} "
            "(expected L###SYYYYT00001 style)"
        )

    missing = [tid for tid in ids if tid not in id_to_idx]
    if missing:
        raise ValueError(f"transaction_id(s) not found: {', '.join(missing)}")

    return sorted((id_to_idx[tid] for tid in ids), reverse=True)

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

def find_team_by_name_or_alias(data, league_id, year, target_name, target_abbrev=None):
    t_norm = _norm(target_name)
    a_norm = _norm(target_abbrev) if target_abbrev else None
    for team in get_team_objects(data, league_id, year):
        if _norm(team.get("name")) == t_norm:
            return team
        if a_norm and _norm(team.get("abbrev")) == a_norm:
            return team
        for al in team.get("aliases", []) or []:
            if _norm(al) == t_norm:
                return team
    return None

def apply_team_update(data, league_id, year, update):
    new_name   = update.get("new_name")
    old_name   = update.get("old_name")
    old_abbrev = update.get("old_abbrev")
    if not new_name:
        return

    # find team in this season
    team = find_team_by_name_or_alias(data, league_id, year, new_name)
    if not team:
        print(f"⚠️ team_update: could not find team for new_name='{new_name}'")
        return

    team.setdefault("aliases", [])

    if team.get("name") != new_name:
        team["name"] = new_name

    def _has_alias(val):
        return _norm(val) in (_norm(a) for a in team["aliases"])

    if old_name and not _has_alias(old_name):
        team["aliases"].append(old_name)

    if old_abbrev and not _has_alias(old_abbrev):
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

def ensure_transaction_bucket(data, league_id, year):
    leagues = data.setdefault("leagues by ID", {})
    league = leagues.setdefault(league_id, {"league_id": league_id})

    seasons = league.setdefault("seasons by ID", {})
    season_id = f"{league_id}S{int(year)}"
    season = seasons.setdefault(season_id, {"season_id": season_id, "year": int(year)})

    txs = season.setdefault("transactions", [])
    return txs, season_id, season

# ----------------------
# Core logic
# ----------------------

def add_transactions(data, league_id, year, new_data):
    year = int(year)
    transactions, season_id, season = ensure_transaction_bucket(data, league_id, year)

    # Flatten + make a sortable list with existing entries
    flat = []
    for t in transactions:
        dt = parse_datetime(year, t["date"], t["time"])
        flat.append((dt, t))

    alias_to_id = build_alias_map(data, league_id, year)
    added_count = 0

    for entry in new_data.get("transactions", []):
        for e in entry.get("entries", []):
            e["date"] = entry["date"]

            if e.get("team_name"):
                tid = resolve_team_id(alias_to_id, e["team_name"])
                if tid:
                    e["team_id"] = tid
                else:
                    print(f"⚠️ Unknown team '{e['team_name']}' @ {e['date']} {e.get('time','')}")

            # duplicate check against existing+queued
            if any(is_duplicate(t, e) for _, t in flat):
                print(f"⚠️ Skipped duplicate transaction for {e.get('team_name')} at {e['date']} {e.get('time')}")
                continue

            dt = parse_datetime(year, entry["date"], e["time"])
            flat.append((dt, e))
            added_count += 1

            if e.get("type") == "team_update":
                apply_team_update(data, league_id, year, e)
                alias_to_id = build_alias_map(data, league_id, year)

    # sort oldest → newest, reindex IDs T00001...
    flat.sort(key=lambda x: x[0])
    sorted_entries = [t for _, t in flat]
    reindex_transactions(sorted_entries, league_id, year)

    # write back to this season, not root
    season["transactions"] = sorted_entries
    return added_count

def remove_transactions(data, ids_or_range):
    # Expand the input into a list of IDs
    s = ids_or_range.strip()
    if "-" in s and "," not in s:
        start, end = s.split("-", 1)
        start_match = TX_ID_RE.match(start)
        end_match = TX_ID_RE.match(end)
        if not start_match or not end_match:
            raise ValueError(
                f"Invalid range format. Expected IDs like L001S2025T00001-L001S2025T00005"
            )
        start_n = int(start_match.group(2))
        end_n = int(end_match.group(2))
        if end_n < start_n:
            raise ValueError("Invalid range (end before start).")
        prefix = start_match.group(1)  # L001S2025
        ids = [f"{prefix}T{n:05d}" for n in range(start_n, end_n + 1)]
    elif "," in s:
        ids = [x.strip() for x in s.split(",") if x.strip()]
    else:
        ids = [s]

    # Use the first ID to locate the season
    m = TX_ID_RE.match(ids[0])
    if not m:
        raise ValueError(f"Invalid transaction_id format: {ids[0]}")
    season_id = m.group(1)  # e.g., L001S2025
    league_id = season_id[:4]  # L001
    year = int(season_id[5:])  # 2025

    transactions, _, season = ensure_transaction_bucket(data, league_id, year)
    if not transactions:
        raise ValueError(f"No transactions found for season {season_id}.")

    indices = validate_tx_ids_for_remove(transactions, ids)
    for idx in indices:
        transactions.pop(idx)

    reindex_transactions(transactions, league_id, year)
    season["transactions"] = transactions
    return len(indices)



# ----------------------
# Main CLI
# ----------------------

def usage():
    print("Usage:")
    print("  Add:    python add_remove_transaction.py add <master_file.json> <league_id> <year> <new_tx.json>")
    print("  Remove: python add_remove_transaction.py remove <master_file.json> <transaction_id(s)|range>")
    sys.exit(1)


def main():
    import sys
    parser = argparse.ArgumentParser(
    description="Add or remove transactions from master fantasy file.",
    usage=(
        "python add_remove_transaction.py add <master_file.json> <league_id> <year> <new_tx.json>\n"
        "python add_remove_transaction.py remove <master_file.json> <transaction_id(s)|range>"
    )
)

    parser.add_argument("mode", choices=["add", "remove"], help="Operation mode")

    parser.add_argument("master_file", help="Path to master fantasy.json file")

    # Conditional args
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        parser.add_argument("league_id", help="League ID, e.g. L001")
        parser.add_argument("year", type=int, help="Season year, e.g. 2025")
    parser.add_argument("target", help="New tx file (add) OR transaction_id(s)/range (remove)")

    # ✅ if no args, just show usage and exit clean
    if len(sys.argv) == 1:
        parser.print_usage()
        sys.exit(0)

    args = parser.parse_args()


    try:
        data = load_json(args.master_file)

        if args.mode == "add":
            new_data = load_json(args.target)
            count = add_transactions(data, args.league_id, args.year, new_data)
            save_json(args.master_file, data)
            print(f"✅ Added {count} transaction(s) into {args.master_file} for {args.league_id} {args.year}.")
        elif args.mode == "remove":
            removed_count = remove_transactions(data, args.target)
            save_json(args.master_file, data)
            print(f"🗑️ Removed {removed_count} transaction(s).")
        else:
            usage()

    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e.filename}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {args.master_file if 'master_file' in locals() else 'input file'}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
