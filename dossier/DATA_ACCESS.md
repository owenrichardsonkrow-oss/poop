# Data access playbook — where each README signal actually comes from

Verified 2026-08-22 from Owen's machine, by plain HTTP (curl) against public
pro profiles and Owen's own. No logins, no API keys. Everything marked
VERIFIED was observed in a real response; anything else says so.

Sits in `dossier/` so it is gitignored by default. Contains no player data.

## 0. Do not use the in-app Claude browser for this

The Claude desktop app crashed twice on 2026-08-22, each time seconds after
a Cloudflare "Just a moment..." page loaded in its built-in browser pane
(faceitfinder.com, then a csstats.gg `/watch/` link). Use curl, or Owen's
own Chrome. Never fan out subagents that drive the in-app browser.

## 1. Faceit handle -> Steam64 — VERIFIED

Faceit's own site API answers without authentication:

```powershell
$h = "<faceit-handle>"
(Invoke-RestMethod "https://www.faceit.com/api/users/v1/nicknames/$h" -UserAgent "Mozilla/5.0").payload.games.cs2.game_id
```

- Steam64 is `payload.games.cs2.game_id`. Also present: `payload.games.cs2.faceit_elo`, `skill_level`, `region`, `payload.country`.
- Wrong handle -> HTTP 404 `{"errors":[{"code":"err_nf0","message":"user not found"}]}`. Handles are the exact Faceit nickname, case-insensitive in practice (ZywOo resolved).
- Cross-check: `https://steamcommunity.com/profiles/<steam64>/?xml=1` returns `<steamID>` = current Steam display name.
- faceitfinder.com: Cloudflare-walled to curl (403) and to the in-app browser. Not needed.

## 2. Leetify public API v3 — VERIFIED

```powershell
$id = "<steam64>"
$p = Invoke-RestMethod "https://api-public.cs-prod.leetify.com/v3/profile?steam64_id=$id" -UserAgent "Mozilla/5.0"
```

- Never linked to Leetify -> HTTP 404, body `Not Found`. Write `unavailable (not on Leetify)`.
- Linked, public -> 200, ~34 KB JSON, `privacy_mode: "public"`.
- Linked, private -> UNVERIFIED. Expect `privacy_mode` != `"public"` and a thinned payload. Write `unavailable (Leetify private)` and do not guess.
- Legacy `api.leetify.com/api/profile/id/<id>` is dead (404 for everyone).
- Web profile `https://leetify.com/app/profile/<steam64>` is the human-readable view of the same data.

Fields observed (Owen's payload, 2026-08-22):

| JSON path | Meaning |
|---|---|
| `total_matches`, `winrate`, `first_match_date` | volume |
| `ranks.premier`, `ranks.faceit_elo`, `ranks.leetify` | ranks |
| `ranks.competitive[]` `{map_name, rank}` | per-map competitive rank |
| `rating.aim / positioning / utility / clutch / opening / ct_leetify / t_leetify` | Leetify's own composite scores |
| `stats.counter_strafing_good_shots_ratio` | counter-strafe % |
| `stats.reaction_time_ms` | time to damage analogue |
| `stats.spray_accuracy`, `stats.accuracy_enemy_spotted`, `stats.accuracy_head` | spray vs. first-bullet, HS accuracy |
| `stats.preaim` | crosshair placement (degrees off) |
| `stats.t_opening_duel_success_percentage`, `ct_opening_duel_success_percentage` | opening SUCCESS per side (not attempt rate) |
| `stats.t_opening_aggression_success_rate`, `ct_...` | opening aggression per side |
| `stats.trade_kill_opportunities_per_round`, `trade_kills_success_percentage`, `traded_deaths_success_percentage` | trade participation |
| `stats.flashbang_thrown`, `flashbang_hit_foe_per_flashbang`, `flashbang_leading_to_kill`, `flashbang_hit_friend_per_flashbang`, `flashbang_hit_foe_avg_duration` | flash quality |
| `stats.he_foes_damage_avg`, `he_friends_damage_avg` | HE damage |
| `stats.utility_on_death_avg` | $ of unused utility on death — the "died with unused utility" signal |
| `recent_matches[]` (100) `{finished_at, data_source: faceit|matchmaking, outcome, map_name, leetify_rating, preaim, reaction_time_ms, accuracy_*, spray_accuracy, score}` | per-match — compute rating spread over last 30 from `leetify_rating` |
| `recent_teammates[]` | who they queue with |

Not in the v3 payload: opening-duel ATTEMPT rate, T-side opening SHARE, AWP
round share, utility damage per round, flash assists per round, per-map
match counts / win %. Get those from csstats.gg.

## 3. csstats.gg — VERIFIED in a real browser, NOT reachable by curl

- curl (any UA) gets `<h1>Please login to view player stats` — bot gating, not a real login wall. A normal logged-out browser sees everything.
- So: Owen opens pages in his own Chrome. Do not use the in-app browser (see §0).
- Player page: `https://csstats.gg/player/<steam64>` — tabs STATS / GRAPHS / WEAPONS / MAPS / MATCHES / PLAYED WITH, filterable by Premier / Faceit. Premier ELO history and Faceit level shown.
- Match page: `https://csstats.gg/match/<id>` — per-player columns observed:
  - K D A +/- K/D ADR HS% KAST Rating
  - UTILITY: EF (enemies flashed), FA (flash assists), EBT (enemy blind time), UD (utility damage)
  - FIRST KILL: FKD (first-kill diff), then FK / FD in three pairs — read as total / T / CT (UNVERIFIED which order; hover the header in a browser to confirm)
  - TRADES: K / D then FK / FD pairs
  - 1VX: 1v5..1v1; MULTIKILLS: 5k..1k
- "Watch Demo" link: `https://csstats.gg/match/<id>/watch/<hash>` — Cloudflare-walled to automation; Owen reports demos are obtainable from here. UNVERIFIED by this session whether it is a `.dem` download or an in-browser 2D viewer.
- Premier demos are otherwise only downloadable by participants. csstats.gg is therefore the route to teammates' Premier demos, when csstats has the match.

## 4. Signal matrix

| README signal | Best source | Fallback |
|---|---|---|
| Opening-duel attempt rate | csstats MATCHES: sum(FK+FD) / rounds over ~30 matches | Leetify `rating.opening` (composite, not a rate) |
| Opening-duel success rate | Leetify `t/ct_opening_duel_success_percentage` | csstats FK/(FK+FD) |
| T-side opening share | csstats T-side FK+FD vs total | — |
| Trade participation | Leetify `trade_kill_opportunities_per_round`, `trade_kills_success_percentage` | csstats TRADES columns |
| Counter-strafe % | Leetify `stats.counter_strafing_good_shots_ratio` | — |
| Time to damage | Leetify `stats.reaction_time_ms` | — |
| HS% | csstats HS% (kills) or Leetify `accuracy_head` (shots) — different definitions, record which | — |
| Spray vs first-bullet | Leetify `spray_accuracy` vs `accuracy_enemy_spotted` | — |
| AWP round share | csstats WEAPONS tab (Owen's browser) | — |
| Utility damage / round | csstats UD summed / rounds | Leetify `he_foes_damage_avg` |
| Flash assists / round | csstats FA summed / rounds | Leetify `flashbang_leading_to_kill` |
| Died with unused utility | Leetify `stats.utility_on_death_avg` ($) | — |
| Save / force decisions | demo only | — |
| Rating spread ~30 matches | Leetify `recent_matches[].leetify_rating` | csstats MATCHES Rating column |
| Map pool (matches, win %) | csstats MAPS tab | Leetify `recent_matches[]` grouped by `map_name` (last 100 only) |

## 5. Etiquette

One Faceit call + one Leetify call per player is the whole automated
footprint. Everything csstats comes from Owen's own browser. No loops, no
scraping.

## 6. Data tiers (policy, 2026-08-22)

**Competitive matches are the base layer; pugs fill gaps.** Order of authority for any number in a profile:

1. **Official / league / tournament / hub** — HLTV-recorded matches, ESEA league seasons (Faceit championships named like `S58 NA Open… - Regular Season`), Faceit tournaments and cups, Faceit hubs, GamersClub championships, and any future third-party competition. A player who has these is typed from these.
2. **Faceit matchmaking** — the comparable pug pool. Used to fill signals the competitive sample does not contain, and for players with no competitive history.
3. **Valve Premier / Competitive** — last resort; systematically inflates rating vs Faceit for the players checked (Owen 1.18 → 1.04, Dafish 1.20 → 1.09).

Window: 12 months. Every profile states which tier each number came from.

## 7. Faceit match history and competition resolution — VERIFIED (curl only; PowerShell's web client is Cloudflare-blocked)

```
https://www.faceit.com/api/stats/v1/stats/time/users/<FACEIT_UUID>/games/cs2?size=100&page=<n>&from=<epoch_ms>
```
Per-match stat rows, newest first, paged. Fields: `matchId`, `competitionId`, `date` (ms), `i1` map, `i18` score, `i6` kills, `i7` assists, `i8` deaths, `i13` headshots, `i12` rounds, `i10` result, `c2` K/D, `c3` K/R, `c4` HS %, `c10` ADR, `i5` team name, `premade`. No competition name in the row.

```
https://www.faceit.com/api/match/v2/match/<matchId>
```
`payload.entity.type` (`championship` | `hub` | `matchmaking`), `payload.entity.name` (e.g. `S58 NA Open9-10 East A - Regular Season`), `payload.teams.faction1/2.name`, `payload.demoURLs` (Faceit demos — the league demo source). Resolve once per distinct `competitionId`.

csstats.gg's `modes=ESEA` tag misses current ESEA seasons named this way; classify from Faceit's entity name instead. GamersClub (`cs.gamersclub.gg/player/<id>`): profile shows level/rating/last match; aggregates are subscription-gated even when signed in.

## 8. Leetify per-match detail — VERIFIED (curl, unauthenticated, 2026-08-22)

This is the route to competitive-match opening duels, utility and mechanics for **every player in a match**, as long as one linked player was in it. It does not provide positions (csstats only).

```
https://api-public.cs-prod.leetify.com/v3/profile/matches?steam64_id=<steam64>
```
The linked player's 100 most recent matches (no paging found): `id` (Leetify uuid), `finished_at`, `data_source` (`faceit` | `matchmaking` | `matchmaking_competitive` | `matchmaking_wingman`), `data_source_match_id` (the Faceit match id for Faceit matches — join key to Faceit history), `map_name`, `team_scores`.

```
https://api.leetify.com/api/games/<leetify uuid>
```
All ten players: `playerStats[]` (kills/deaths/damage, KAST, HLTV and Leetify ratings by side, pre-aim, reaction time, time-to-kill, first-bullet accuracy, counter-strafe ratio, spray accuracy, flash/HE/molotov/smoke stats, utility on death, trade kill / traded death opportunities-attempts-successes, multikills) and `openingDuelPlayerStats[]` (attempt %, success %, trade %, aggression success — overall and per side). Also `details` (tickrate, gameMode), `gamePlayerRoundSkeletonStats`, `replayFile`.
`/v2/matches/<uuid>` on api-public is a smaller variant without the opening-duel block.

Use: take a linked player's list → keep `faceit` rows whose Faceit id is tiered league/tournament/hub in `raw/faceit_history/` → fetch each game → one row per player per match. Limit: 100 most recent per linked player, so for the Ashland three (only Dafish is linked) it reaches the NECC Spring 2026 season, not Fall 2025.

csstats cannot ingest Faceit matches by URL (the "add a match" box takes Steam IDs and Valve share codes only); Faceit's own demo download needs a logged-in scope and the listed CDN host does not resolve from here.
