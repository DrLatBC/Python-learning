import json
import sys

def season_id_for(league_id: str, year: int | str) -> str:
    return f"{league_id}S{int(year)}"

def migrate_transactions(data):
    leagues = data.get("leagues by ID", {})
    for league_id, league in leagues.items():
        seasons = league.get("seasons by ID", {})
        for season_id, season in seasons.items():
            year = season.get("year")
            if not year:
                continue

            transactions = season.get("transactions", [])
            if not isinstance(transactions, list):
                continue

            season_prefix = season_id_for(league_id, year)
            for i, tx in enumerate(transactions, start=1):
                old_id = tx.get("transaction_id")
                new_id = f"{season_prefix}T{i:05d}"
                tx["transaction_id"] = new_id
                print(f"{old_id} → {new_id}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python migrate_tx_ids.py <fantasy.json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    migrate_transactions(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Migration complete. File updated: {path}")

if __name__ == "__main__":
    main()
