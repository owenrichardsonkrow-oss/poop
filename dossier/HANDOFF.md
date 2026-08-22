# Handoff — teammate dossier project

For a local Claude Code session picking this up. Read this file first, then
`dossier/README.md` for the method.

Written 2026-08-20 by a Claude Code **web** session on branch
`claude/cs2-teammate-dossier-1dzvbj`.

---

## 1. What this project is

The user is about to become the **in-game leader** of a CS2 collegiate team.
He meets his four new teammates for the first time in roughly a week
(≈ 2026-08-29 — confirm with him). He wants a profile of each player so he
can write a stratbook that fits the roster he actually has, rather than
installing a system the players cannot execute.

This is **performance and playstyle profiling of his own teammates**. It is
consented-to team preparation, not investigation.

## 2. Hard constraints — read before writing anything

**This repository is PUBLIC** (`owenrichardsonkrow-oss/poop`). Filled-in
dossiers contain four real people's names, Steam IDs, and candid written
assessments of their weaknesses. None of that may be pushed.

`.gitignore` denies by default inside `dossier/`. Only these are tracked:

```
dossier/README.md
dossier/TEMPLATE_PLAYER.md
dossier/TEMPLATE_ROSTER.md
dossier/HANDOFF.md
```

Everything else in `dossier/` — including all `PLAYER_*.md` and `ROSTER.md`
— is ignored automatically. **Do not weaken these rules.** Before any push:

```powershell
git status --short
```

No `PLAYER_*` or `ROSTER.md` line may ever appear there.

**Do not confuse this with `demo_audit.py`.** That is a separate tool in the
same repo — a cheat-triage script — governed by `CLAUDE.md`, which forbids
verdict language. It has nothing to do with this folder, and it must never
be pointed at these teammates. Leave it alone.

**Never invent a statistic.** This is the most likely way to ruin this
project. If a Leetify profile is private, a lookup fails, or a number is not
available, write `unavailable` and say so. A blank field is useful; a
plausible fabricated number is worse than useless, because the user will
build role assignments on top of it and only find out during a scrim.

## 3. Current state

Done and committed (`b388675`):

| File | State |
|---|---|
| `dossier/README.md` | Complete. The method: three axes, signals, workflow. |
| `dossier/TEMPLATE_PLAYER.md` | Complete blank template. |
| `dossier/TEMPLATE_ROSTER.md` | Complete blank template + 6 decision rules. |

Present locally but **gitignored and empty of data**:

| File | State |
|---|---|
| `dossier/PLAYER_<handle>.md` x4 | Skeletons. Handle, Faceit URL, **Steam64 / SteamID3 / legacy ID, and Leetify URL** now recorded. All stats still blank. |
| `dossier/ROSTER.md` | Skeleton. No data. |

Nothing has been measured. No stat in this project has ever been collected.

## 4. Why this was handed off

The web session runs behind a strict network allowlist — only package
registries and GitHub are reachable. Every lookup this project needs was
refused at CONNECT with a 403:

```
faceitfinder.com     403      steamcommunity.com   403
leetify.com          403      api.steampowered.com 403
open.faceit.com      403      even example.com     403
```

A local session on the user's own machine has normal network access. That is
the entire reason this is being handed to you.

## 5. The job

1. ~~**Resolve the four Faceit handles to Steam64 IDs.**~~ **DONE** — the
   user supplied all four Leetify profile URLs on 2026-08-20. Each
   `PLAYER_*.md` skeleton now carries that player's Steam64, SteamID3,
   legacy ID and Leetify link.

   **But the handle-to-ID pairing is UNVERIFIED.** The two lists were
   supplied in separate messages and matched by *order*, not by any lookup —
   the web session could not reach Steam or Leetify to confirm. Each
   skeleton says so at the top. **Confirm the pairing before collecting
   anything**: open each Leetify link and check the profile is the player
   the filename names. Mis-paired IDs put every statistic on the wrong
   person, and nothing downstream would reveal it.

   **The four handles are deliberately not written in this file** — it is
   tracked in a public repo, and there is no reason to publish the
   association between four named people and a document about profiling
   them. Read them from the filenames of the gitignored skeletons:

   ```powershell
   Get-ChildItem dossier\PLAYER_*.md | Select-Object -ExpandProperty Name
   ```

   Each skeleton's Identity table already holds that player's Faceit URL,
   which follows `https://www.faceit.com/en/players/<handle>`.

2. **Pull the axis signals** for each from Leetify (or Noesis). Leetify
   profiles are publicly viewable by Steam ID *unless* the player has enabled
   the privacy toggle. Some of these four will likely be private — record
   that fact rather than working around it.

   The signals needed per axis are tabulated in `dossier/README.md`. Record
   **raw numbers**, not just your scores, so a read can be re-derived later.

3. **Fill each `PLAYER_*.md`.** Leave anything unmeasured blank.

4. **Score the three axes**, ranking the four against each other *first*,
   then sanity-checking against the absolute bands in `README.md`. Relative
   ranking is what matters — the user needs to know which of his players
   takes the most initiative, not how they compare to professionals.

5. **Watch 2–3 flagged rounds per player** if the user has demo access, using
   CS2Lens or CS2.CAM. `README.md` lists exactly what to look for. This is
   the part statistics cannot provide. Skip it if he has no demos; do not
   fake it.

6. **Fill `ROSTER.md`** and walk him through the six decision rules there.
   That is the actual deliverable — it converts profiles into stratbook
   shape.

## 6. Framing that must survive the handoff

- **Profiles are hypotheses, not verdicts.** Everything available before the
  first scrim is pug data, and pug behaviour is not team behaviour. A player
  who lurks in Premier may just have learned his randoms will not trade him.
  Each profile carries a "test in scrim" section — keep it filled in.
- **Write in the language of "looks like", not "is".**
- The user should be willing to show any player that player's own file. If a
  sentence would not survive that, rewrite it.
- Advise him to have the four link Leetify themselves rather than relying on
  public lookups. He meets them in a week, "I pulled stats to plan roles" is
  a normal thing to say, and it gets him their scrim demos later — which are
  worth more than every pug number combined. He may reasonably decide to
  prepare in advance from public data instead; that is his call to make.

## 7. Working with this user

From `CLAUDE.md`: competent gamer, self-described coding novice, on Windows.

- Give plain numbered instructions with full PowerShell commands, not
  fragments.
- Explain briefly *why*, not just *what*.
- He has explicitly asked for direct, critical feedback over validation. If
  a plan of his is weak, say so plainly.

## 8. Suggested first message to him

Confirm before doing the lookups:

1. Does he want profiles built from public data before the meeting, or would
   he rather ask the four to link Leetify first?
2. Does he have any demos of these players, or only their public stats?
3. Confirm the meeting date.
