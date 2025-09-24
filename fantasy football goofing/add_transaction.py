import json
import sys
import os

# --------- IO ---------
def load_json(filename):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        return {"seasons": {}}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --------- Normalization helpers ---------
def norm_str(x):
    return x.strip() if isinstance(x, str) else ""

def norm_team_abbrev(abbrev):
    return norm_str(abbrev).upper()

def norm_position(pos):
    p = norm_str(pos)
    return "D/ST" if p.replace(" ", "").upper() in {"DST", "D/ST"} else p.upper()

def norm_player(p):
    if not isinstance(p, dict):
        return {}
    return {
        "name": norm_str(p.get("name", "")),
        "team": norm_team_abbrev(p.get("team", "")),
        "position": norm_position(p.get("position", "")),
    }

def norm_player_list(lst):
    if not isinstance(lst, list):
        return []
    out = [norm_player(x) for x in lst if isinstance(x, dict)]
    return [x for x in out if any(x.values())]  # drop empty stubs

def player_key(p):
    return (
        p.get("name", "").lower(),
        p.get("team", "").upper(),
        p.get("position", "").upper(),
    )

def same_player_sets(a_list, b_list):
    return sorted(player_key(x) for x in a_list) == sorted(player_key(x) for x in b_list)

# --------- Validation ---------
def ensure_season_transactions(seasons, year):
    seasons.setdefault(year, {})
    seasons[year].setdefault(
        "transactions", {"waivers": [], "free_agents": [], "trades": []}
    )
    t = seasons[year]["transactions"]
    t.setdefault("waivers", [])
    t.setdefault("free_agents", [])
    t.setdefault("trades", [])
    return t

def validate_struct(new_txn):
    if not isinstance(new_txn, dict):
        raise ValueError("❌ New transaction JSON must be an object.")

    ttype = new_txn.get("type")
    if ttype not in {"waiver", "free_agent", "trade"}:
        raise ValueError("❌ Field 'type' must be one of: waiver, free_agent, trade.")

    present_sections = [k for k in ("waiver", "free_agent", "trade") if k in new_txn]
    if len(present_sections) != 1 or present_sections[0] != ttype:
        raise ValueError(
            f"❌ Provide exactly one section matching 'type'. Found: {present_sections}"
        )

    return ttype

# --------- ID helpers ---------
def next_id(bucket, prefix):
    existing_ids = [x.get("id") for x in bucket if "id" in x]
    nums = []
    for eid in existing_ids:
        if isinstance(eid, str) and eid.startswith(prefix):
            try:
                nums.append(int(eid[len(prefix):]))
            except ValueError:
                continue
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}{str(next_num).zfill(3)}"

# --------- Per-type handlers ---------
def normalize_waiver(payload):
    if not isinstance(payload, dict):
        raise ValueError("❌ waiver must be an object")

    date = norm_str(payload.get("date", ""))
    team = norm_str(payload.get("team", ""))
    adds = norm_player_list(payload.get("adds", []))
    drops = norm_player_list(payload.get("drops", []))
    notes = norm_str(payload.get("notes", ""))

    bid = payload.get("bid", None)
    if bid is not None:
        try:
            bid = int(bid)
        except Exception:
            raise ValueError("❌ waiver.bid must be an integer if provided")

    pr_before = payload.get("priority_before", None)
    if pr_before is not None:
        try:
            pr_before = int(pr_before)
        except Exception:
            raise ValueError("❌ waiver.priority_before must be an integer if provided")

    pr_after = payload.get("priority_after", None)
    if pr_after is not None:
        try:
            pr_after = int(pr_after)
        except Exception:
            raise ValueError("❌ waiver.priority_after must be an integer if provided")

    if not date:
        raise ValueError("❌ waiver.date is required")
    if not team:
        raise ValueError("❌ waiver.team is required")
    if not adds and not drops:
        raise ValueError("❌ waiver must include at least one add or drop")

    return {
        "date": date,
        "team": team,
        "adds": adds,
        "drops": drops,
        "bid": bid,
        "priority_before": pr_before,
        "priority_after": pr_after,
        "notes": notes,
    }

def normalize_free_agent(payload):
    if not isinstance(payload, dict):
        raise ValueError("❌ free_agent must be an object")

    date = norm_str(payload.get("date", ""))
    team = norm_str(payload.get("team", ""))
    adds = norm_player_list(payload.get("adds", []))
    drops = norm_player_list(payload.get("drops", []))
    notes = norm_str(payload.get("notes", ""))

    if not date:
        raise ValueError("❌ free_agent.date is required")
    if not team:
        raise ValueError("❌ free_agent.team is required")
    if not adds and not drops:
        raise ValueError("❌ free_agent must include at least one add or drop")

    return {"date": date, "team": team, "adds": adds, "drops": drops, "notes": notes}

def normalize_trade(payload):
    if not isinstance(payload, dict):
        raise ValueError("❌ trade must be an object")

    date = norm_str(payload.get("date", ""))
    teams = payload.get("teams", [])
    if not isinstance(teams, list) or len(teams) != 2:
        raise ValueError("❌ trade.teams must be a list of exactly two team names")

    ta = payload.get("team_a", {})
    tb = payload.get("team_b", {})

    def norm_side(side):
        name = norm_str(side.get("name", ""))
        if not name:
            raise ValueError("❌ trade team side missing 'name'")
        players_in = norm_player_list(side.get("players_in", []))
        players_out = norm_player_list(side.get("players_out", []))
        picks_in = side.get("picks_in", [])
        picks_out = side.get("picks_out", [])
        if not isinstance(picks_in, list) or not isinstance(picks_out, list):
            raise ValueError("❌ trade picks_in and picks_out must be lists")
        return {
            "name": name,
            "players_in": players_in,
            "players_out": players_out,
            "picks_in": picks_in,
            "picks_out": picks_out,
        }

    team_a = norm_side(ta)
    team_b = norm_side(tb)
    notes = norm_str(payload.get("notes", ""))

    if sorted([team_a["name"], team_b["name"]]) != sorted(
        [norm_str(teams[0]), norm_str(teams[1])]
    ):
        raise ValueError("❌ trade.teams must match team_a.name and team_b.name")

    if not date:
        raise ValueError("❌ trade.date is required")

    if not (
        team_a["players_out"]
        or team_b["players_out"]
        or team_a["picks_out"]
        or team_b["picks_out"]
    ):
        raise ValueError("❌ trade must include at least one outgoing asset")

    return {
        "date": date,
        "teams": [team_a["name"], team_b["name"]],
        "team_a": team_a,
        "team_b": team_b,
        "notes": notes,
    }

# --------- Dupe checks ---------
def is_dupe_waiver(existing, neww):
    return (
        existing.get("date") == neww.get("date")
        and existing.get("team") == neww.get("team")
        and same_player_sets(existing.get("adds", []), neww.get("adds", []))
        and same_player_sets(existing.get("drops", []), neww.get("drops", []))
        and (existing.get("bid") or 0) == (neww.get("bid") or 0)
    )

def is_dupe_free_agent(existing, newfa):
    return (
        existing.get("date") == newfa.get("date")
        and existing.get("team") == newfa.get("team")
        and same_player_sets(existing.get("adds", []), newfa.get("adds", []))
        and same_player_sets(existing.get("drops", []), newfa.get("drops", []))
    )

def is_dupe_trade(existing, newt):
    same_teams = sorted(existing.get("teams", [])) == sorted(newt.get("teams", []))
    if not same_teams or existing.get("date") != newt.get("date"):
        return False

    def side(x):
        return (
            sorted(player_key(p) for p in x.get("players_in", [])),
            sorted(player_key(p) for p in x.get("players_out", [])),
            sorted(x.get("picks_in", [])),
            sorted(x.get("picks_out", [])),
            x.get("name", ""),
        )

    ea, eb = existing.get("team_a", {}), existing.get("team_b", {})
    na, nb = newt.get("team_a", {}), newt.get("team_b", {})
    return (side(ea) == side(na) and side(eb) == side(nb)) or (
        side(ea) == side(nb) and side(eb) == side(na)
    )

# --------- Main add ---------
def add_transaction(master_file, txn_file, year):
    data = load_json(master_file)
    seasons = data.setdefault("seasons", {})
    year = str(year)

    tx_buckets = ensure_season_transactions(seasons, year)
    new_txn = load_json(txn_file)
    ttype = validate_struct(new_txn)

    if ttype == "waiver":
        waiver = normalize_waiver(new_txn["waiver"])
        for w in tx_buckets["waivers"]:
            if is_dupe_waiver(w, waiver):
                raise ValueError(
                    f"❌ Duplicate WAIVER on {waiver['date']} for {waiver['team']}"
                )
        waiver["id"] = next_id(tx_buckets["waivers"], "WAV")
        tx_buckets["waivers"].append(waiver)
        save_json(master_file, data)
        adds = ", ".join(
            f"{p['name']} ({p['team']} {p['position']})" for p in waiver["adds"]
        ) or "none"
        drops = ", ".join(
            f"{p['name']} ({p['team']} {p['position']})" for p in waiver["drops"]
        ) or "none"
        bid_txt = f", bid ${waiver['bid']}" if waiver.get("bid") is not None else ""
        print(
            f"✅ WAIVER [{waiver['id']}] added {waiver['date']} — {waiver['team']}: +[{adds}] / -[{drops}]{bid_txt}"
        )

    elif ttype == "free_agent":
        fa = normalize_free_agent(new_txn["free_agent"])
        for f in tx_buckets["free_agents"]:
            if is_dupe_free_agent(f, fa):
                raise ValueError(
                    f"❌ Duplicate FREE_AGENT on {fa['date']} for {fa['team']}"
                )
        fa["id"] = next_id(tx_buckets["free_agents"], "FA")
        tx_buckets["free_agents"].append(fa)
        save_json(master_file, data)
        adds = ", ".join(
            f"{p['name']} ({p['team']} {p['position']})" for p in fa["adds"]
        ) or "none"
        drops = ", ".join(
            f"{p['name']} ({p['team']} {p['position']})" for p in fa["drops"]
        ) or "none"
        print(
            f"✅ FREE_AGENT [{fa['id']}] added {fa['date']} — {fa['team']}: +[{adds}] / -[{drops}]"
        )

    else:  # trade
        trade = normalize_trade(new_txn["trade"])
        for tr in tx_buckets["trades"]:
            if is_dupe_trade(tr, trade):
                a, b = trade["teams"]
                raise ValueError(
                    f"❌ Duplicate TRADE on {trade['date']} between {a} and {b}"
                )
        trade["id"] = next_id(tx_buckets["trades"], "TR")
        tx_buckets["trades"].append(trade)
        save_json(master_file, data)
        a, b = trade["teams"]
        a_in = len(trade["team_a"]["players_in"]) + len(trade["team_a"]["picks_in"])
        b_in = len(trade["team_b"]["players_in"]) + len(trade["team_b"]["picks_in"])
        print(
            f"✅ TRADE [{trade['id']}] added {trade['date']} — {a} ⇄ {b} (packages: {a_in}↔{b_in})"
        )

# --------- CLI ---------
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python add_transaction.py <master_file.json> <new_transaction.json> <year>")
        sys.exit(1)
    master_file = sys.argv[1]
    txn_file = sys.argv[2]
    year = sys.argv[3]
    try:
        add_transaction(master_file, txn_file, year)
    except Exception as e:
        print(f"{e}")
        sys.exit(1)
