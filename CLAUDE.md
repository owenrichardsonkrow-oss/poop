# CLAUDE.md

Context for Claude Code working in this repository. Read this before making changes.

## What this project is

`demo_audit.py` reads a Counter-Strike 2 GOTV demo (`.dem`) and produces a
**triage report**: per-player behavioural statistics plus a list of specific
ticks worth watching by eye.

It is a review-assistance tool for a player who wants to check his own matches.
It is defensive in nature: it detects cheating, it does not enable it.

## The single most important rule

**This tool produces evidence for human review. It never produces verdicts.**

Every statistical signal here has a real false-positive rate. Good players
flick fast and hit heads. Do not add features, output strings, or scoring that
imply certainty about whether a person cheated. Specifically:

- Never emit language like "cheater", "confirmed", "guilty", "proof".
- Never auto-generate reports intended to be submitted as accusations.
- Always keep the caveats section in the printed output. Do not "clean it up"
  by shortening it.
- If you add a new detector, you must also document its known false-positive
  causes in the same commit.

This constraint exists because the whole category of tool is dangerous. Sites
that assign "cheater" labels from statistical thresholds get people harassed
over what is often just a good game.

## Do not build

- Anything that reads another process's memory, or inspects a player's files.
- Anything that modifies the CS2 client, injects code, or interacts with
  Vanguard/VAC/FACEIT AC/EAC.
- Anything that scrapes third-party sites for player data without consent.
- Bulk automated reporting or mass-scanning of strangers' demos.

## Current status: PARTIALLY VERIFIED, STILL NEVER RUN ON A REAL DEMO

No demo file has been available in any session so far, so the script still
has never executed against real data. But the API assumptions below have now
been checked directly against the installed `demoparser2` package (its type
stub and the strings embedded in its compiled extension module — the actual
CS:GO/CS2 game-event field table is baked into the binary), not just its
docs, which is as far as this can be verified without a `.dem` file:

1. **Tick field names — CONFIRMED.** `X`, `Y`, `Z`, `pitch`, `yaw`, `health`,
   `team_num`, `is_alive`, `active_weapon_name`, `velocity_X`, `velocity_Y`
   (`CORE_FIELDS` / `NICE_FIELDS`) all appear as real prop aliases in the
   compiled parser. `steamid`, `tick`, and `name` are confirmed to be
   always-present columns on `parse_ticks()` output regardless of requested
   props.
2. **Event column names — CONFIRMED.** The raw `player_hurt` event carries
   `userid`, `attacker`, `health`, `armor`, `weapon`, `dmg_health`,
   `dmg_armor`, `hitgroup`; demoparser2's `userid`/`attacker` role-prefixing
   convention (seen in its own examples, e.g. `attacker_steamid`,
   `user_team_name`) makes the code's `attacker_steamid` / `user_steamid` /
   `dmg_health` / `hitgroup` / `weapon` columns correct. `weapon_fire` carries
   `userid`, `weapon` -> `user_steamid`, `weapon`, also correct.
3. **`parse_header()` — CONFIRMED BROKEN, NOW FIXED.** Its real return keys
   are exactly: `addons`, `server_name`, `demo_file_stamp`,
   `network_protocol`, `map_name`, `fullpackets_version`,
   `allow_clientside_entities`, `allow_clientside_particles`,
   `demo_version_name`, `demo_version_guid`, `client_name`, `game_directory`.
   There is no `playback_ticks` / `playback_time` or any timing field, so the
   old `detect_tickrate()` could never do real detection — it silently
   returned 64 every time while implying it had measured something. It has
   been replaced with an explicit `--tickrate` flag (default 64). Always pass
   `--tickrate 128` for FACEIT/most community demos.
4. **Memory** in `analyse_sticky` — still unverified. It builds a
   `(chunk, P, P, 3)` array. Lower `CHUNK_TICKS` if it blows up on a full
   30-minute demo.

**First task in any session with a real demo available: run it end to end**
and correct anything this section got wrong — static analysis of the parser
binary is not a substitute for a real run. Do not add new detectors before
that happens.

## How to verify anything

The user has demos; the repo ships none. To check API assumptions:

```python
from demoparser2 import DemoParser
p = DemoParser("demos/match.dem")
print(p.list_game_events())
print(p.parse_event("player_hurt").columns.tolist())
print(p.parse_ticks(["X"]).head())
```

`tests/test_geometry.py` runs without demoparser2 and without a demo. It covers
the pure math. Keep it passing; extend it when you touch the geometry.

```
python -m pytest tests/ -v
```

With no demo file at all, `pip install demoparser2` and inspect the installed
extension module directly rather than guessing from docs — the real CS2 event
schema and `parse_header()` keys are embedded as literal strings in the
compiled binary:

```bash
python3 -c "import demoparser2, os; print(os.path.dirname(demoparser2.__file__))"
strings <path from above>/demoparser2.*.so | grep -A8 "^player_hurt$"
```

This is how the field names in this file were checked in a session with no
demo available. It is corroborating evidence, not a substitute for a real
run — it can confirm a name exists but can't confirm the data in it behaves
as expected.

## Domain constraints that shape the design

CS2 GOTV demos are the *server's* recording. This bounds what is knowable:

- **No client input data.** Button states, subtick input timing, and CVar query
  replies are not in the file. This permanently rules out detecting Invalid
  Input, Invalid CVar, Subtick Spam, Desubticking, Hyperscroll, Nulls, and DLL
  injection. Do not attempt these. If asked, explain why rather than shipping a
  fake version.
- **Angles are per-tick.** Sub-tick aim movement is smeared. A real 40-degree
  flick and a cheat's instant snap can look similar at 64 tick.
- **No map geometry.** The tool cannot tell "tracking a visible enemy" from
  "tracking through a wall". This is the biggest accuracy gap. See ROADMAP.md.
- **Tickrate** is usually 64 for Valve/Premier demos, 128 on many
  FACEIT/community servers. `parse_header()` cannot tell you which (verified
  — see "Current status" above), so it's a required `--tickrate` flag, not
  something to auto-detect.

Coordinate conventions used throughout (see `docs/DEMO_NOTES.md`):
negative pitch is up, yaw is degrees counter-clockwise from +X, eye height is
64 units above the player origin.

## Working style for this user

The user is a competent gamer but a self-described coding novice on Windows.

- Give plain, numbered instructions when he needs to run something.
- Full commands, not fragments. Assume PowerShell.
- Explain *why* a change was made, briefly, not just *what*.
- He has asked for direct, critical feedback over validation. If an idea in
  ROADMAP.md is a bad idea, say so.

## Conventions

- Python 3.11+. Standard library plus numpy, pandas, demoparser2.
- Single-file for now; see ROADMAP.md item 1 for the intended split.
- Tunable thresholds live in the CONFIG block at the top of `demo_audit.py`,
  never inline in functions.
- Detector functions return `(kind, tick, steamid, human_readable_note)`
  tuples so everything flows into one flag list.
- Don't add a dependency without saying why in the commit message.
