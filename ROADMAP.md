# Roadmap

Ordered. Don't skip ahead — item 0 gates everything.

## 0. Make it run  ← START HERE

The script has never executed against a real demo. Get
`python demo_audit.py demos/match.dem --tickrate 64` to produce a report
without crashing.

- [x] Confirm the real demoparser2 tick property names; fix `CORE_FIELDS`.
      Checked against the compiled `demoparser2` extension's embedded prop
      table — `X`, `Y`, `Z`, `pitch`, `yaw`, `health`, `team_num`,
      `is_alive`, `active_weapon_name`, `velocity_X`, `velocity_Y` all exist
      as-is. No change needed. Still not confirmed against a real demo's
      actual values.
- [x] Confirm event column names on `player_hurt`, `weapon_fire`. Checked
      against the same embedded table: `player_hurt` has `userid`,
      `attacker`, `dmg_health`, `hitgroup`, `weapon`; `weapon_fire` has
      `userid`, `weapon`. Combined with demoparser2's own role-prefixing
      convention, this confirms `attacker_steamid` / `user_steamid` /
      `dmg_health` / `hitgroup` / `weapon` are correct. `player_death` not
      used by the current code, not checked.
- [x] Confirm `parse_header()` keys. Confirmed it returns exactly `addons`,
      `server_name`, `demo_file_stamp`, `network_protocol`, `map_name`,
      `fullpackets_version`, `allow_clientside_entities`,
      `allow_clientside_particles`, `demo_version_name`, `demo_version_guid`,
      `client_name`, `game_directory` — no tickrate/timing field exists.
      `detect_tickrate` was deleted; tickrate now comes from a required
      `--tickrate` flag (default 64).
- [ ] Check memory during `analyse_sticky` on a full 30-minute demo.
- [ ] Sanity-check the numbers: median aim error at the moment of damage should
      land somewhere in the low single digits of degrees for normal players. If
      it's 40, the eye-position or tick-alignment math is wrong.

## 1. Split into modules

Once it runs, break the single file up. Suggested layout:

```
cs2audit/
  __init__.py
  loading.py      # demoparser2 wrangling, field probing, pivoting
  geometry.py     # forward_vectors, angle_between, view_delta
  detectors/
    aim.py        # snap, silentaim, accuracy
    angles.py     # pitch limits, spin
    firerate.py   # doubletap
    placement.py  # sticky crosshair
  report.py       # z-scores, printing, CSV
cli.py
```

Keep `demo_audit.py` as a thin shim that still works, or the user's muscle
memory breaks.

## 2. Ground truth

Right now nothing is calibrated. The thresholds in CONFIG are guesses.

- [ ] Collect a set of demos with known outcomes — matches where a player was
      later VAC/Overwatch banned, and matches believed clean.
- [ ] Measure the actual distributions of each metric across them.
- [ ] Retune thresholds so the false-positive rate on clean demos is stated as
      a number in the README, not left implicit.
- [ ] If a detector can't be shown to separate the two sets, delete it. A
      detector that fires on everyone is worse than no detector.

This is the highest-value item on the list and the one most likely to be
skipped. Don't skip it.

## 3. Round and clip context

Make the output actionable rather than statistical.

- [ ] Parse `round_start` / `round_end` and report round numbers next to ticks.
- [ ] Group nearby flags into single "moments" instead of listing every tick.
- [ ] Emit a copy-pasteable list of `demo_gototick` commands.

## 4. Visibility checking (the big one)

The tool currently cannot distinguish tracking a visible enemy from tracking
one through a wall. That's the difference between "good crosshair placement"
and the clearest wallhack tell there is.

Two approaches, in increasing order of effort:

- **Nav mesh approximation.** `awpy` ships map data and has visibility
  helpers. Cheapest path, coarse results. Try this first.
- **Real collision geometry.** Extract `world_physics.vmdl_c` from the map VPK
  (Source2Viewer / VRF can decompile it), build a BVH, raycast eye-to-target.
  This is what CS2FOW does. Accurate, and a large project on its own.

Once visibility exists, the sticky-crosshair metric becomes far more meaningful:
measure crosshair-on-enemy time *while the enemy was not visible*, and measure
pre-aim at the moment an enemy first becomes visible.

## 5. Nice to have

- [ ] HTML report with a 2D map overlay of flagged moments.
- [ ] Batch mode over a folder of demos.
- [ ] Compare a player against their own historical baseline across demos,
      which is a much better reference than the nine strangers in one lobby.

## Explicitly out of scope

Detecting Invalid Input, Invalid CVar, Subtick Spam, Desubticking, Hyperscroll,
Nulls, DLL Injection, or Namechanger. The required data is not in a GOTV demo.
See CLAUDE.md.
