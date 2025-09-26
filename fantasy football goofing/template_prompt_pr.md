
Write Week {{WEEK_NUMBER}} power rankings for our league, using only /mnt/data/fantasy.json for data and honoring all rules in the System section above. The cutoff is the end of MNF for Week {{WEEK_NUMBER}} in America/New_York. If MNF timestamp is missing, use Monday 23:59:59 ET.

Records: pull season-to-date W–L for each team_id directly from /mnt/data/fantasy.json at the Week X cutoff. Display that exact value. Also recompute from box scores to validate, but do not replace the display value with a computed one.

Compute composite ranks per the weights provided.

Apply tie-breakers exactly as specified.

Select Awards using the eligibility rules and tie hierarchy.

Generate 3–5 deterministic League Nuggets; avoid duplicates week to week by seeding randomness with {{WEEK_NUMBER}}.

Keep every team blurb to 1–3 sentences with exactly one emoji.

Do not include PF/PA tables or raw data. No citations.

Render the result exactly in the OUTPUT TEMPLATE format.

NOTES FOR FUTURE YOU

If template_power_ranking.md exists, you may load and mirror its structure, but this document’s OUTPUT TEMPLATE is the source of truth when conflicts arise.

If the audit detects mismatches between computed records and stored records, trust your computed records and proceed, silently correcting the display.

If early in the season (e.g., Week 1), treat two-week form as whatever exists and scale weights proportionally to available weeks to avoid division by zero; keep the final ranking behavior stable.