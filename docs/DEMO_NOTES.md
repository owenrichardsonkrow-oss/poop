# Demo data notes

Reference for the conventions and gotchas this project depends on. Correct
anything here that testing disproves — it was written from documentation, not
from a verified run.

## Coordinate and angle conventions

- Positions are in Hammer units. Roughly 1 unit ≈ 1.9 cm.
- A player's `X, Y, Z` is the **origin at their feet**, not their eyes.
- Eye height is ~64 units standing, ~46 crouched. The code uses a flat 64
  (`EYE_HEIGHT_STANDING`), which introduces error against crouched players.
  Fixing this needs a duck/crouch state field.
- `pitch`: **negative is up**, positive is down. Legal client range is
  [-89, 89]. Values outside that are only producible by a modified client.
- `yaw`: degrees, counter-clockwise from +X. Wraps; always take the shorter
  arc when differencing (`min(d, 360 - d)`).

Forward vector from angles:

```
p = radians(pitch); y = radians(yaw)
fx = cos(p) * cos(y)
fy = cos(p) * sin(y)
fz = -sin(p)
```

## Tickrate

Valve/Premier GOTV demos are normally 64 tick. Some third-party servers record
at 128. Pro/HLTV demos vary. Never assume — one tick at 64 is 15.6 ms, and
several detectors are timing-based, so a wrong tickrate silently corrupts them.

**Confirmed: `parse_header()` cannot tell you the tickrate.** Its actual
return keys (checked against the installed `demoparser2` extension) are
`addons`, `server_name`, `demo_file_stamp`, `network_protocol`, `map_name`,
`fullpackets_version`, `allow_clientside_entities`,
`allow_clientside_particles`, `demo_version_name`, `demo_version_guid`,
`client_name`, `game_directory` — no playback ticks, playback time, or tick
interval among them. `demo_audit.py` takes tickrate as an explicit
`--tickrate` flag (default 64) rather than trying to detect it.

## What subtick does to this

CS2 timestamps inputs *within* a tick. A shot fired at tick 1000.4 is processed
with sub-tick precision by the server, but the demo records the view angle at
tick boundaries. Consequences:

- A shot's recorded angle may not be the angle it was actually fired at.
- Very fast flicks are under-represented; the intermediate angles are lost.
- A one-tick offset between a `weapon_fire` event and the tick data is common.
  If aim-error numbers look systematically bad, try offsetting by ±1 tick.

## Events

Names follow the CS:GO event list closely. Useful ones:

| Event | Key fields |
|---|---|
| `weapon_fire` | `user_steamid`, `weapon`, `tick` |
| `player_hurt` | `attacker_steamid`, `user_steamid`, `dmg_health`, `hitgroup`, `weapon` |
| `player_death` | `attacker_steamid`, `user_steamid`, `headshot`, `weapon`, `penetrated` |
| `round_start` / `round_end` | `tick`, `winner` |

`hitgroup` values: 1 = head, 2 = chest, 3 = stomach, 4/5 = arms, 6/7 = legs.

Run `parser.list_game_events()` on a real demo to see what's actually present —
not every demo carries every event.

## Known sources of false positives

Keep this list current. Every detector must appear here.

- **SNAP** — legitimate flicks off a teammate's callout, or off sound cues.
  Also fires on a player who was already tracking and re-acquires after a
  smoke clears.
- **SILENT** — packet loss and desync move the recorded angle away from the
  fired angle. Also fires on wallbangs where the victim position at the
  recorded tick differs from the position at impact.
- **DOUBLETAP** — the cycle-time table is approximate and doesn't account for
  weapon switches, or for two `weapon_fire` events being logged for one shot
  by some parsers. Verify against a known-clean demo before trusting it.
- **STICKY** — a player correctly holding a long angle sits on an enemy's
  future position for a long time. Without visibility checking this metric is
  weak, and it disproportionately flags AWPers and anchors.
- **PITCH / SPIN** — the most reliable signals here, but a demo corruption or
  a parser bug can still produce out-of-range values. Confirm by watching.
