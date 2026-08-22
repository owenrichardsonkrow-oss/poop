# Teammate dossiers

A method for typing the players on a roster so the stratbook can be built
around what they actually are, rather than what they say they are.

This is **performance and playstyle profiling**. It has nothing to do with
`demo_audit.py`, which lives in the same repo but answers a different
question. Do not mix them.

## Before you write anything: this repo is public

`owenrichardsonkrow-oss/poop` is a **public** GitHub repository. Filled-in
dossiers contain real people's names, Steam IDs, and candid assessments of
their weaknesses. None of that belongs on the open internet.

`.gitignore` is set to deny-by-default inside this folder: only `README.md`,
`TEMPLATE_PLAYER.md` and `TEMPLATE_ROSTER.md` are tracked. Anything else you
create in `dossier/` is ignored automatically, including `PLAYER_*.md` and
your working `ROSTER.md`.

Do not override this. If you want the filled-in files backed up somewhere,
keep them in a private location — a private repo, or a synced folder outside
this checkout. Verify before any push:

```powershell
git status --short
```

Nothing matching `dossier/PLAYER_*` or `dossier/ROSTER.md` should ever appear
in that output.

## The single most important rule

**A dossier is a hypothesis, not a verdict.**

Everything in the first pass comes from pug data — Premier and Faceit
matches played with strangers. Pug behaviour is not team behaviour. A player
who lurks every round in Premier may simply have learned that his random
teammates will not trade him. A player with terrible utility numbers may
have never been asked to throw any.

So:

- Write profiles in the language of "looks like", not "is".
- Every profile carries an explicit **test** — what you will watch for in
  the first two scrims to confirm or kill the read.
- Rewrite after real team play. Scrim data replaces pug data completely
  within a month; a dossier you never update stops being a read and becomes
  a prejudice.
- Show a player their own profile if they ask. If you would not be willing
  to, you have written it wrong.

## The three axes

Do not sort players into archetype buckets ("entry", "lurker", "support").
The labels are too coarse, they overlap, and players self-report them badly
— almost everyone believes they are an entry fragger.

Instead score each player 1–5 on three independent axes. The *combination*
is the archetype, and it falls out on its own.

### Axis 1 — Initiative

*Does this player create contact, or respond to it?*

| Signal | Where to get it | Reads high when |
|---|---|---|
| Opening-duel attempt rate | Leetify / Noesis | `(opening kills + opening deaths) / rounds` is large |
| T-side opening share | Leetify | He is in the first fight on T specifically |
| Trade participation | Demo review | He is consistently the second man into a fight |
| Time to first contact | Demo review | He meets the enemy early in the round |

Opening-duel attempt rate is the single cleanest number. Rough bands:
under 15% of rounds is low initiative, 15–25% is middling, over 25% is high.
Treat these as loose calibration only — see "Rank within the roster" below.

High initiative = space-taker, needs support and trades written around him.
Low initiative = anchor, trader, late-round player.

### Axis 2 — Aim shape

*How does this player win duels, not whether he wins them.*

| Signal | Where to get it | Tells you |
|---|---|---|
| Counter-strafe % | Leetify | Movement discipline; high = clean stop-and-shoot |
| Time to damage (TTD) | Leetify | Reaction speed; low = wins the reflex fight |
| HS% | Anywhere | Tap/burst tendency (noisy on its own) |
| Spray vs. first-bullet accuracy | Leetify | Close-range brawler vs. mid-range duellist |
| AWP round share | Leetify | Whether he is a real AWPer or an opportunist |

Three rough shapes fall out:

- **Close-range spray** — wins by getting on top of people. Write him short
  angles, fast hits, tight corners.
- **Mid-range tap / counter-strafe** — wins the disciplined stand-off. Write
  him long angles, mid control, opening picks.
- **Holding / off-angle** — wins by being somewhere first and not moving.
  Write him anchor spots and passive CT setups.

Rating and ADR do not go on this axis. You are typing, not ranking.

### Axis 3 — Discipline

*How much structure can this player execute?*

| Signal | Where to get it | Reads high when |
|---|---|---|
| Utility damage per round | Leetify | He actually throws nades |
| Flash assists per round | Leetify | He flashes for other people, not himself |
| Died with unused utility | Leetify | Low is good — he spends what he buys |
| Save / force decisions | Demo review | He saves when the round is gone |
| Rating variance across ~30 matches | Leetify | Low spread = steady, high spread = swingy |

This is the axis that decides **how thick your stratbook can be**, and it is
the one most people skip. Collegiate rosters are usually aim-rich and
util-poor.

### Rank within the roster first

For a five-man team, *relative* position matters more than absolute
benchmarks. You do not need to know whether your best entry is good by
professional standards — you need to know which of your five takes the most
initiative, because that is the player entries get written for.

So: rank your five against each other on each axis first, then sanity-check
against the absolute bands above. If all five rank low on initiative in
absolute terms, that is itself the finding, and it changes the stratbook
(see `ROSTER.md`).

## Where the data comes from

| Tool | Use it for | Do not use it for |
|---|---|---|
| [Leetify](https://leetify.com) (free tier is enough) | All aggregate stats above | Qualitative reads |
| [Noesis](https://www.noesis.gg/) | Alternative / cross-check on aggregates | — |
| [CS2Lens](https://www.cs2lens.com/about), [CS2.CAM](https://cs2.cam/) | Watching specific flagged rounds in 2D | Bulk stats — they are replay tools |
| `demo_audit.py` (this repo) | Nothing here, yet | Anything in this folder |

Do not re-derive numbers the commercial tools already give you for free.
Custom parsing is only worth it later, for team-specific questions the
public tools cannot answer — trade spacing, default setups, execute timing.

### Data tiers — which matches a profile is built from

Not all matches are equal. Build each profile in this order, and say in the
file which tier each number came from:

1. **Competitive** — HLTV-recorded matches, ESEA league seasons, Faceit
   tournaments and cups, Faceit hubs, and any other organised play. This is
   the base layer. A player who has it is typed from it.
2. **Faceit matchmaking** — the comparable pug pool. Fills the signals the
   competitive sample is missing, and is the base layer only for players
   with no competitive history.
3. **Valve Premier / Competitive** — last resort. Inflates ratings relative
   to Faceit for the players checked so far.

Twelve-month window. `DATA_ACCESS.md` §6–7 has the endpoints and the
classification rule for Faceit competition names.

## Week-one workflow

1. Collect Steam and Faceit IDs from all four teammates.
2. Ask everyone to link **Leetify** and share into a team dashboard. Frame it
   honestly: it is for practice planning and role assignment. Do this *with*
   them, not *on* them — you also get their scrim demos later this way, and
   those matter far more than pugs.
3. For each player, pull the axis signals above from their last ~30 matches.
   Record raw numbers in their dossier file, not just your scores.
4. Pick **2–3 rounds per player** that the stats flag, and watch only those
   in CS2Lens or CS2.CAM 2D view:
   - one round where he took the opening duel,
   - one clutch or last-alive situation,
   - one full T-side round on his best map.
   Ten focused minutes per player beats an hour of full demos.
5. Copy `TEMPLATE_PLAYER.md` to `PLAYER_<name>.md` and fill it in.
6. Copy `TEMPLATE_ROSTER.md` to `ROSTER.md` once all five are done, and
   derive the stratbook shape from the table there.

### What to look for in demo review

The stats cannot see any of this. This is the entire reason you watch:

- Does he **check corners or pre-aim** them? Tells you whether set executes
  will survive contact with his habits.
- After the plan breaks, does he **regroup or freelance**?
- Does he play **for the trade** — within reach of a teammate — or drift solo?
- Does he **use cover between angles**, or cross open ground?
- On CT, does he hold his spot or rotate early on sound?
- Under pressure in a clutch: does he play time and position, or force a duel?
- Does he **talk** through his death, or go quiet? (Audible in your own demos
  only, but worth noting where you have it.)

## Refresh cadence

- Rewrite from scrim data after the first two scrims. Pug profiles are dead
  the moment you have real team demos.
- Re-score monthly thereafter.
- Log every revision at the bottom of the player file, with the date and what
  changed your mind. If a read has never changed, be suspicious of it.
