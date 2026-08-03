#!/usr/bin/env python3
"""
demo_audit.py -- retroactive cheat *triage* for CS2 GOTV demos.

WHAT THIS IS:
    A tool that reads a .dem file, computes behavioural statistics for every
    player, and tells you WHICH PLAYERS and WHICH TICKS are worth watching
    with your own eyes.

WHAT THIS IS NOT:
    A verdict machine. It does not decide who is cheating. Every metric here
    has false positives. Good players flick fast and hit heads. Treat the
    output as "go watch tick 47210" not as "this person cheats".

USAGE:
    pip install demoparser2 numpy pandas
    python demo_audit.py path/to/match.dem
    python demo_audit.py path/to/match.dem --csv out.csv

Then in CS2:  playdemo <demo>  ->  demoui  ->  demo_gototick <tick>
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# CONFIG -- tune these once you have a feel for your own lobbies
# ----------------------------------------------------------------------------

EYE_HEIGHT_STANDING = 64.0   # units above origin
TARGET_HEIGHT = 58.0         # aim point on the victim (upper chest / head-ish)

SNAP_DEGREES = 25.0          # a "flick" this big in one tick...
SNAP_SETTLE_DEGREES = 2.0    # ...landing this precisely on target = suspicious
SNAP_WINDOW_TICKS = 4        # how far back from the damage tick to look

SILENT_ERROR_DEGREES = 20.0  # damage landed while crosshair was this far off
SILENT_ISOLATION_SEC = 0.4   # only count shots not part of an ongoing spray

STICKY_DEGREES = 5.0         # crosshair "on" an enemy within this cone
STICKY_MIN_DISTANCE = 500.0  # ignore close-quarters, everyone's on target there

PITCH_LIMIT = 89.0           # legal client pitch range is [-89, 89]
SPIN_DEGREES_PER_TICK = 100.0

DOUBLETAP_RATIO = 0.6        # shot arrived at <60% of the weapon's cycle time

CHUNK_TICKS = 4000           # memory/speed tradeoff for the vectorised pass

DEFAULT_TICKRATE = 64.0      # Valve/Premier standard. demoparser2's
                             # parse_header() does not expose the real tick
                             # rate (verified: its keys carry no timing
                             # info), so this can only be a default -- pass
                             # --tickrate explicitly for 128-tick demos.

# Approximate seconds between shots at full auto. Used only for doubletap.
WEAPON_CYCLE = {
    "ak47": 0.0968, "m4a1": 0.0904, "m4a1_silencer": 0.09, "galilar": 0.09,
    "famas": 0.09, "sg556": 0.09, "aug": 0.09, "awp": 1.45, "ssg08": 1.25,
    "scar20": 0.25, "g3sg1": 0.25, "deagle": 0.224, "revolver": 0.4,
    "usp_silencer": 0.17, "hkp2000": 0.15, "glock": 0.15, "p250": 0.15,
    "fiveseven": 0.15, "tec9": 0.12, "cz75a": 0.09, "elite": 0.12,
    "mac10": 0.075, "mp9": 0.07, "mp7": 0.075, "mp5sd": 0.08, "ump45": 0.085,
    "p90": 0.07, "bizon": 0.08, "nova": 0.88, "xm1014": 0.25, "mag7": 0.85,
    "sawedoff": 0.85, "m249": 0.08, "negev": 0.07,
}

CORE_FIELDS = ["X", "Y", "Z", "pitch", "yaw", "health", "team_num"]
NICE_FIELDS = ["is_alive", "active_weapon_name", "velocity_X", "velocity_Y"]


# ----------------------------------------------------------------------------
# geometry
# ----------------------------------------------------------------------------

def forward_vectors(pitch_deg: np.ndarray, yaw_deg: np.ndarray) -> np.ndarray:
    """View angles -> unit forward vectors. Shape (..., 3)."""
    p = np.radians(pitch_deg)
    y = np.radians(yaw_deg)
    cp = np.cos(p)
    return np.stack([cp * np.cos(y), cp * np.sin(y), -np.sin(p)], axis=-1)


def angle_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Degrees between two stacks of (already-ish) vectors."""
    an = a / np.clip(np.linalg.norm(a, axis=-1, keepdims=True), 1e-9, None)
    bn = b / np.clip(np.linalg.norm(b, axis=-1, keepdims=True), 1e-9, None)
    return np.degrees(np.arccos(np.clip(np.sum(an * bn, axis=-1), -1.0, 1.0)))


def view_delta(p1, y1, p2, y2) -> np.ndarray:
    """Angular distance between two view angles, in degrees."""
    return angle_between(forward_vectors(p1, y1), forward_vectors(p2, y2))


# ----------------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------------

@dataclass
class Demo:
    path: str
    tickrate: float
    ticks: pd.DataFrame
    events: dict = field(default_factory=dict)
    players: dict = field(default_factory=dict)   # steamid -> name

    # pivoted arrays, filled by build_arrays()
    tick_ids: np.ndarray = None
    sids: list = None
    X: np.ndarray = None
    Y: np.ndarray = None
    Z: np.ndarray = None
    pitch: np.ndarray = None
    yaw: np.ndarray = None
    alive: np.ndarray = None
    team: np.ndarray = None
    row_of_tick: dict = None
    col_of_sid: dict = None


def load(path: str, tickrate: float | None = None) -> Demo:
    try:
        from demoparser2 import DemoParser
    except ImportError:
        sys.exit("Missing dependency. Run:  pip install demoparser2 numpy pandas")

    try:
        parser = DemoParser(path)
    except Exception as exc:
        sys.exit(f"Could not open '{path}': {exc}\n"
                  "Check the path and that it's an actual .dem file, not a "
                  ".dem.bz2 or a redirected download page.")

    fields = CORE_FIELDS + NICE_FIELDS
    try:
        ticks = parser.parse_ticks(fields)
    except Exception:
        print("[warn] optional tick fields rejected, falling back to core set")
        ticks = parser.parse_ticks(CORE_FIELDS)

    ticks = ticks.dropna(subset=["steamid", "tick", "X", "Y", "Z", "pitch", "yaw"])
    ticks["steamid"] = ticks["steamid"].astype("int64")

    if "is_alive" not in ticks.columns:
        ticks["is_alive"] = ticks["health"] > 0

    events = {}
    for name in ("weapon_fire", "player_hurt", "player_death"):
        try:
            df = parser.parse_event(name)
            events[name] = df if df is not None else pd.DataFrame()
        except Exception as exc:
            print(f"[warn] could not parse event {name}: {exc}")
            events[name] = pd.DataFrame()

    names = (ticks.groupby("steamid")["name"].agg(lambda s: s.dropna().iloc[0]
             if len(s.dropna()) else "?").to_dict())

    if tickrate is None:
        tickrate = DEFAULT_TICKRATE
        print(f"[warn] no --tickrate given, assuming {tickrate:.0f}. "
              "demoparser2's parse_header() does not expose playback ticks "
              "or playback time (confirmed against its actual header keys: "
              "addons, server_name, demo_file_stamp, network_protocol, "
              "map_name, fullpackets_version, allow_clientside_entities, "
              "allow_clientside_particles, demo_version_name, "
              "demo_version_guid, client_name, game_directory -- no tick "
              "rate among them), so it cannot be read from the demo. "
              "Pass --tickrate 128 for most FACEIT/community demos.")
    return Demo(path=path, tickrate=float(tickrate), ticks=ticks,
                events=events, players=names)


def build_arrays(d: Demo) -> None:
    """Pivot the long tick frame into (T x P) arrays for vectorised work."""
    t = d.ticks
    d.tick_ids = np.sort(t["tick"].unique())
    d.sids = sorted(t["steamid"].unique())
    d.row_of_tick = {v: i for i, v in enumerate(d.tick_ids)}
    d.col_of_sid = {v: i for i, v in enumerate(d.sids)}

    def pivot(col, fill=np.nan, dtype=float):
        m = (t.pivot_table(index="tick", columns="steamid", values=col,
                           aggfunc="first")
             .reindex(index=d.tick_ids, columns=d.sids))
        return m.to_numpy(dtype=dtype, na_value=fill) if dtype != float \
            else m.to_numpy(dtype=float)

    d.X, d.Y, d.Z = pivot("X"), pivot("Y"), pivot("Z")
    d.pitch, d.yaw = pivot("pitch"), pivot("yaw")
    d.team = pivot("team_num")
    alive = t.copy()
    alive["_a"] = alive["is_alive"].astype(float)
    d.alive = (alive.pivot_table(index="tick", columns="steamid", values="_a",
                                 aggfunc="first")
               .reindex(index=d.tick_ids, columns=d.sids)
               .fillna(0.0).to_numpy(dtype=float)) > 0.5


# ----------------------------------------------------------------------------
# analyzers
# ----------------------------------------------------------------------------

def col(d: Demo, sid) -> int | None:
    return d.col_of_sid.get(int(sid)) if pd.notna(sid) else None


def row(d: Demo, tick) -> int | None:
    return d.row_of_tick.get(int(tick)) if pd.notna(tick) else None


def analyse_damage_events(d: Demo) -> tuple[pd.DataFrame, list]:
    """Per-damage-instance: aim error, pre-shot flick size, silentaim check."""
    hurt = d.events.get("player_hurt", pd.DataFrame())
    if hurt.empty:
        return pd.DataFrame(), []

    acol = "attacker_steamid" if "attacker_steamid" in hurt.columns else None
    vcol = "user_steamid" if "user_steamid" in hurt.columns else None
    if not acol or not vcol:
        print("[warn] player_hurt lacks steamid columns; skipping aim analysis")
        return pd.DataFrame(), []

    rows = []
    flags = []
    for _, e in hurt.iterrows():
        r, a, v = row(d, e["tick"]), col(d, e[acol]), col(d, e[vcol])
        if r is None or a is None or v is None or a == v:
            continue
        if not np.isfinite(d.pitch[r, a]) or not np.isfinite(d.X[r, v]):
            continue

        eye = np.array([d.X[r, a], d.Y[r, a], d.Z[r, a] + EYE_HEIGHT_STANDING])
        tgt = np.array([d.X[r, v], d.Y[r, v], d.Z[r, v] + TARGET_HEIGHT])
        rel = tgt - eye
        dist = float(np.linalg.norm(rel))
        fwd = forward_vectors(np.array(d.pitch[r, a]), np.array(d.yaw[r, a]))
        err = float(angle_between(fwd, rel))

        # largest single-tick view movement in the ticks leading up to the hit
        flick = 0.0
        for k in range(1, SNAP_WINDOW_TICKS + 1):
            if r - k < 0:
                break
            p0, y0 = d.pitch[r - k, a], d.yaw[r - k, a]
            p1, y1 = d.pitch[r - k + 1, a], d.yaw[r - k + 1, a]
            if not (np.isfinite(p0) and np.isfinite(p1)):
                continue
            flick = max(flick, float(view_delta(np.array(p0), np.array(y0),
                                                np.array(p1), np.array(y1))))

        rows.append(dict(tick=int(e["tick"]), attacker=int(e[acol]),
                         victim=int(e[vcol]), dist=dist, err=err, flick=flick,
                         dmg=float(e.get("dmg_health", 0) or 0),
                         hitgroup=e.get("hitgroup", None)))

        if flick >= SNAP_DEGREES and err <= SNAP_SETTLE_DEGREES:
            flags.append(("SNAP", int(e["tick"]), int(e[acol]),
                          f"{flick:.0f} deg flick settling to {err:.1f} deg"))

    return pd.DataFrame(rows), flags


def analyse_silentaim(dmg: pd.DataFrame, d: Demo) -> list:
    """Damage landing while the crosshair pointed somewhere else entirely."""
    if dmg.empty:
        return []
    flags = []
    gap_ticks = SILENT_ISOLATION_SEC * d.tickrate
    for sid, g in dmg.groupby("attacker"):
        g = g.sort_values("tick")
        prev = -1e9
        for _, r in g.iterrows():
            isolated = (r["tick"] - prev) > gap_ticks
            prev = r["tick"]
            if isolated and r["err"] >= SILENT_ERROR_DEGREES:
                flags.append(("SILENT", int(r["tick"]), int(sid),
                              f"{r['err']:.0f} deg off target, still did "
                              f"{r['dmg']:.0f} dmg"))
    return flags


def analyse_sticky(d: Demo) -> dict:
    """Fraction of alive ticks with the crosshair inside a tight cone of an
    enemy at range. A proxy for aimlock / wall-tracking without map geometry."""
    T, P = d.X.shape
    on = np.zeros(P)
    tot = np.zeros(P)

    for s in range(0, T, CHUNK_TICKS):
        e = min(s + CHUNK_TICKS, T)
        px, py, pz = d.X[s:e], d.Y[s:e], d.Z[s:e]
        alive = d.alive[s:e]
        team = d.team[s:e]

        eye = np.stack([px, py, pz + EYE_HEIGHT_STANDING], axis=-1)   # (t,P,3)
        tgt = np.stack([px, py, pz + TARGET_HEIGHT], axis=-1)
        fwd = forward_vectors(d.pitch[s:e], d.yaw[s:e])               # (t,P,3)

        rel = tgt[:, None, :, :] - eye[:, :, None, :]                 # (t,P,P,3)
        dist = np.linalg.norm(rel, axis=-1)
        ang = angle_between(fwd[:, :, None, :], rel)

        valid = (alive[:, :, None] & alive[:, None, :]
                 & (team[:, :, None] != team[:, None, :])
                 & (dist > STICKY_MIN_DISTANCE) & np.isfinite(ang))
        for i in range(P):  # never compare a player against themselves
            valid[:, i, i] = False

        hit = valid & (ang < STICKY_DEGREES)
        on += hit.any(axis=2).sum(axis=0)
        tot += (valid.any(axis=2) & alive).sum(axis=0)

    return {d.sids[i]: (on[i] / tot[i] if tot[i] > 50 else np.nan)
            for i in range(P)}


def analyse_angles(d: Demo) -> tuple[dict, list]:
    """Impossible pitch and sustained spin -- classic antiaim / spinbot."""
    flags = []
    out = {}
    for i, sid in enumerate(d.sids):
        p = d.pitch[:, i]
        y = d.yaw[:, i]
        ok = np.isfinite(p) & np.isfinite(y) & d.alive[:, i]
        if ok.sum() < 50:
            out[sid] = dict(bad_pitch=0, spin_ticks=0)
            continue

        bad = int(np.sum(np.abs(p[ok]) > PITCH_LIMIT))

        dy = np.abs(np.diff(y))
        dy = np.minimum(dy, 360 - dy)
        alive_pair = d.alive[:-1, i] & d.alive[1:, i]
        spin = int(np.sum((dy > SPIN_DEGREES_PER_TICK) & alive_pair
                          & np.isfinite(dy)))

        out[sid] = dict(bad_pitch=bad, spin_ticks=spin)
        if bad > 0:
            idx = np.where(ok & (np.abs(p) > PITCH_LIMIT))[0]
            flags.append(("PITCH", int(d.tick_ids[idx[0]]), sid,
                          f"pitch outside legal range on {bad} ticks"))
        if spin > d.tickrate * 3:
            flags.append(("SPIN", int(d.tick_ids[0]), sid,
                          f"{spin} ticks of >{SPIN_DEGREES_PER_TICK:.0f} "
                          f"deg/tick yaw movement"))
    return out, flags


def analyse_firerate(d: Demo) -> list:
    """Shots arriving faster than the weapon physically allows."""
    fire = d.events.get("weapon_fire", pd.DataFrame())
    if fire.empty or "user_steamid" not in fire.columns:
        return []
    if "weapon" not in fire.columns:
        return []

    flags = []
    fire = fire.dropna(subset=["user_steamid", "tick"])
    for (sid, wpn), g in fire.groupby(["user_steamid", "weapon"]):
        key = str(wpn).replace("weapon_", "")
        cycle = WEAPON_CYCLE.get(key)
        if not cycle:
            continue
        ticks = np.sort(g["tick"].to_numpy(dtype=float))
        if len(ticks) < 2:
            continue
        gaps = np.diff(ticks) / d.tickrate
        bad = np.where((gaps > 0) & (gaps < cycle * DOUBLETAP_RATIO))[0]
        for b in bad:
            flags.append(("DOUBLETAP", int(ticks[b + 1]), int(sid),
                          f"{key} refired in {gaps[b]*1000:.0f} ms "
                          f"(min {cycle*1000:.0f} ms)"))
    return flags


# ----------------------------------------------------------------------------
# reporting
# ----------------------------------------------------------------------------

def zscore(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and np.isfinite(sd) and sd > 1e-9 \
        else s * 0.0


def build_report(d: Demo, dmg: pd.DataFrame, sticky: dict,
                 angles: dict, flags: list) -> pd.DataFrame:
    rows = []
    fire = d.events.get("weapon_fire", pd.DataFrame())
    shots = (fire.groupby("user_steamid").size().to_dict()
             if not fire.empty and "user_steamid" in fire.columns else {})

    for sid in d.sids:
        g = dmg[dmg["attacker"] == sid] if not dmg.empty else pd.DataFrame()
        n_shots = shots.get(sid, 0)
        hs = (g["hitgroup"] == 1).mean() if len(g) and "hitgroup" in g else np.nan

        rows.append(dict(
            steamid=sid,
            name=d.players.get(sid, "?"),
            shots=n_shots,
            hits=len(g),
            hit_pct=(len(g) / n_shots * 100) if n_shots else np.nan,
            hs_pct=hs * 100 if pd.notna(hs) else np.nan,
            median_aim_err=g["err"].median() if len(g) else np.nan,
            sub1deg_pct=(g["err"] < 1.0).mean() * 100 if len(g) else np.nan,
            median_flick=g["flick"].median() if len(g) else np.nan,
            sticky_pct=(sticky.get(sid, np.nan) or np.nan) * 100,
            bad_pitch=angles.get(sid, {}).get("bad_pitch", 0),
            spin_ticks=angles.get(sid, {}).get("spin_ticks", 0),
        ))

    rep = pd.DataFrame(rows)
    for c in ("hit_pct", "hs_pct", "sub1deg_pct", "sticky_pct"):
        rep[f"z_{c}"] = zscore(rep[c])
    rep["z_aim_err"] = -zscore(rep["median_aim_err"])   # lower error = higher z

    hard = pd.Series(0.0, index=rep.index)
    for kind, _, sid, _ in flags:
        w = {"SNAP": 1.0, "SILENT": 1.5, "DOUBLETAP": 2.0,
             "PITCH": 3.0, "SPIN": 3.0}.get(kind, 0.5)
        hard[rep.index[rep["steamid"] == sid]] += w
    rep["hard_flags"] = hard

    rep["triage"] = (rep[["z_hit_pct", "z_hs_pct", "z_sub1deg_pct",
                          "z_sticky_pct", "z_aim_err"]].fillna(0).sum(axis=1)
                     + rep["hard_flags"])
    return rep.sort_values("triage", ascending=False).reset_index(drop=True)


def print_report(d: Demo, rep: pd.DataFrame, flags: list) -> None:
    print("\n" + "=" * 74)
    print(f"DEMO: {d.path}")
    print(f"tickrate ~{d.tickrate:.0f}   players: {len(d.sids)}   "
          f"ticks: {len(d.tick_ids)}")
    print("=" * 74)

    cols = ["name", "shots", "hit_pct", "hs_pct", "median_aim_err",
            "sub1deg_pct", "median_flick", "sticky_pct", "hard_flags", "triage"]
    show = rep[cols].copy()
    show.columns = ["player", "shots", "hit%", "hs%", "aimErr",
                    "<1deg%", "flick", "sticky%", "flags", "TRIAGE"]
    print("\nPER-PLAYER SUMMARY (sorted by triage score, highest first)")
    print(show.to_string(index=False, float_format=lambda v: f"{v:7.2f}"))

    print("\nTRIAGE SCORE is a z-score sum WITHIN THIS LOBBY ONLY.")
    print("Someone always finishes first. A high score means 'watch them',")
    print("not 'they cheated'. Ignore scores under ~3.")

    if flags:
        print("\n" + "-" * 74)
        print(f"DISCRETE EVENTS TO REVIEW ({len(flags)})")
        print("-" * 74)
        for kind, tick, sid, note in sorted(flags, key=lambda f: f[1])[:60]:
            nm = d.players.get(sid, sid)
            print(f"  tick {tick:>7}  {kind:<10} {nm:<20} {note}")
        if len(flags) > 60:
            print(f"  ... and {len(flags) - 60} more (see --csv output)")
        print("\nIn game:  playdemo <demo>  then  demo_gototick <tick>")
    else:
        print("\nNo discrete events flagged.")

    print("\n" + "-" * 74)
    print("READ THIS BEFORE ACCUSING ANYONE")
    print("-" * 74)
    print("""\
  * DOUBLETAP and PITCH are the only near-unfakeable signals here. Everything
    else is behavioural and has real false-positive rates.
  * SILENT flags fire on desync/lag, on shots through smoke, and on any
    damage the demo timestamps a tick off. Watch them, don't count them.
  * GOTV records angles per tick. Sub-tick aim movement is smeared, so real
    flicks look bigger and cheat flicks can look smaller than they were.
  * A player with high sticky% may just be holding a long angle correctly.
  * This tool cannot see through walls -- it has no map geometry, so it
    cannot distinguish 'tracking a visible enemy' from 'tracking through a
    wall'. That is the single biggest gap versus a real anti-cheat.""")
    print()


# ----------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="CS2 demo cheat triage")
    ap.add_argument("demo", help="path to a .dem file")
    ap.add_argument("--csv", help="write full per-player table here")
    ap.add_argument("--events-csv", help="write every flagged event here")
    ap.add_argument("--tickrate", type=float, default=None,
                     help="server tick rate (default 64; use 128 for most "
                          "FACEIT/community demos). demoparser2 cannot tell "
                          "us this, so it must be supplied.")
    args = ap.parse_args()

    print(f"Parsing {args.demo} ...")
    d = load(args.demo, tickrate=args.tickrate)
    print(f"Parsed {len(d.ticks):,} player-ticks. Building arrays ...")
    build_arrays(d)

    print("Analysing damage events ...")
    dmg, flags = analyse_damage_events(d)
    print("Analysing silentaim ...")
    flags += analyse_silentaim(dmg, d)
    print("Analysing view angles ...")
    angles, angle_flags = analyse_angles(d)
    flags += angle_flags
    print("Analysing fire rates ...")
    flags += analyse_firerate(d)
    print("Analysing crosshair placement (slowest step) ...")
    sticky = analyse_sticky(d)

    rep = build_report(d, dmg, sticky, angles, flags)
    print_report(d, rep, flags)

    if args.csv:
        rep.to_csv(args.csv, index=False)
        print(f"Wrote {args.csv}")
    if args.events_csv:
        pd.DataFrame(flags, columns=["kind", "tick", "steamid", "note"]).to_csv(
            args.events_csv, index=False)
        print(f"Wrote {args.events_csv}")


if __name__ == "__main__":
    main()
