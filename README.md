# cs2-demo-audit

Reads a Counter-Strike 2 GOTV demo and tells you **which players and which
ticks are worth watching**. It does not decide who is cheating.

## Status

The geometry layer is tested and passing. The demo-parsing layer's field
names have been checked against the installed `demoparser2` package directly
and are believed correct, but the tool has **never been run against a real
demo file** — see `ROADMAP.md` item 0 and `CLAUDE.md` for exactly what's
verified and what isn't.

## Setup (Windows / PowerShell)

1. Install Python 3.11 or newer from python.org. Tick "Add Python to PATH".
2. Open PowerShell in this folder and create an environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If step 2 is blocked, run once:
   `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Confirm the environment works:

   ```powershell
   python -m pytest tests\ -v
   ```

   All tests should pass. They need no demo file.

## Getting a demo

- **Premier / Competitive**: in CS2, Watch → Your Matches → download.
  Available for about 30 days after the match.
- **FACEIT**: the match room page has a demo download link.

Put the `.dem` in `demos\`.

## Running

```powershell
python demo_audit.py demos\match.dem --tickrate 64
python demo_audit.py demos\match.dem --tickrate 128 --csv report.csv --events-csv flags.csv
```

`--tickrate` matters: it's 64 for Valve/Premier demos, usually 128 on
FACEIT/community servers. The demo file itself doesn't expose this, so pass
the right one or several of the timing-based detectors (SPIN, DOUBLETAP) will
silently use the wrong thresholds.

Then to review a flagged moment, in CS2's console:

```
playdemo match
demoui
demo_gototick 47210
```

## Reading the output

**Per-player table** — one row per player, sorted by triage score.

| Column | Meaning |
|---|---|
| `hit%` | damaging shots ÷ shots fired |
| `hs%` | fraction of damage instances to the head |
| `aimErr` | median degrees between crosshair and victim when damage landed |
| `<1deg%` | fraction of damage instances with near-perfect crosshair placement |
| `flick` | median largest single-tick view movement before a damaging shot |
| `sticky%` | share of time the crosshair sat within 5° of a distant enemy |
| `flags` | weighted count of discrete flagged events |
| `TRIAGE` | sum of z-scores plus flags |

**The triage score is relative to this lobby only.** Someone always finishes
first. A score below about 3 means nothing at all.

**Flagged events** are the actually useful output: specific ticks to watch.

| Flag | Signal | Reliability |
|---|---|---|
| `PITCH` | view pitch outside the legal ±89° range | very high |
| `SPIN` | sustained extreme yaw velocity | very high |
| `DOUBLETAP` | weapon refired faster than its cycle time | high |
| `SNAP` | large flick settling instantly onto a target | moderate |
| `SILENT` | damage landed while the crosshair pointed elsewhere | low |

`PITCH` and `SPIN` are near-unfakeable — a normal client cannot produce them.
Everything else is behavioural and needs your eyes on it.

## What it can't do

CS2 demos are the server's recording and contain no client input data. That
permanently rules out detecting invalid inputs, CVar tampering, subtick spam,
desubticking, hyperscroll, nulls, and DLL injection — roughly ten of the
seventeen checks a live server-side anti-cheat can run.

It also has no map geometry, so it cannot distinguish tracking a visible enemy
from tracking one through a wall. That's the largest accuracy gap and the
subject of `ROADMAP.md` item 4.

## Layout

```
demo_audit.py       the tool
CLAUDE.md           context for Claude Code — read this before editing
ROADMAP.md          prioritised work, in order
docs/DEMO_NOTES.md  coordinate conventions, event fields, false-positive log
tests/              pure-math tests, no demo required
demos/              put .dem files here (gitignored)
dossier/            teammate playstyle profiling — unrelated to the tool
```

## Not part of the tool: `dossier/`

`dossier/` holds a method and blank templates for **performance and playstyle
profiling of your own teammates** — typing players so a stratbook can be built
around them. It is a separate project that happens to live in the same repo.
It does not use `demo_audit.py`, and `demo_audit.py` must never be pointed at
teammates. See `dossier/README.md`.

Filled-in dossiers are gitignored; this repo is public.

## A word on using this

Statistical cheat detection gets people harassed over what was often just a
good game. Use this to decide what to watch, then watch it. Report through
official channels based on what you saw, not on a number this script printed.
