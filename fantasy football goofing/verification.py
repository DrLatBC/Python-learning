def verify_game(game: dict, game_id: str, verbose=False):
    """
    Abort on:
      - missing team names
      - broken starter row (missing name/team/position)
      - ESPN missing projections: proj == 0 while fpts > 0
      - totals mismatch > ±0.2 (starters and bench)
    """
    issues = []

    def norm_str(x):
        return x.strip() if isinstance(x, str) else ""

    def r2(x):
        try:
            return round(float(x), 2)
        except Exception:
            return 0.0

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

        def near(a, b, tol=0.2):
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

    if not issues and verbose:
        print(f"✅ {game_id} verified clean.")
    return issues


if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 2:
        print("Usage: python verification.py <fantasy.json> [--verbose]")
        sys.exit(1)

    filename = sys.argv[1]
    verbose = "--verbose" in sys.argv

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_issues = []
    for year, year_data in data.get("seasons", {}).items():
        for week, week_data in year_data.get("weeks", {}).items():
            for game in week_data.get("games", []):
                gid = game.get("game_id", f"{year}W{week}G?")
                issues = verify_game(game, gid, verbose=verbose)
                all_issues.extend(issues)

    if all_issues:
        print("❌ Verification FAILED:")
        for issue in all_issues:
            print(" -", issue)
        sys.exit(1)
    else:
        print("✅ Verification PASSED: All checks clean.")
        sys.exit(0)
