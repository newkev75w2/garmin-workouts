---
name: garmin-workout
description: >
  Plan gym, strength and running training from the user's own Garmin history — which sits
  locally in ~/Projects/garmin-workouts along with every completed session, weight, rep, run
  and VO2max reading they have logged. Use this skill whenever the user asks to create,
  design, build, plan or schedule a workout, lifting session, gym session, run, training day,
  training week, weekly schedule, routine, split, push/pull/leg day or programme — including
  for a named or future day ("design me a workout for Monday", "something for tomorrow") and
  WHETHER OR NOT THEY SAY THE WORD GARMIN. Also use it when they ask what to train ("what
  muscles should I train tomorrow?", "am I due a rest day?"), how to fit running and lifting
  around each other, how many times a week to train, how their running or cardio is going,
  what their VO2max is doing, whether a run should be easy or hard, how they are progressing
  on a lift or whether to add weight, and when they mention uploading or syncing anything to
  their watch. Because their real training data is on disk, never answer these from general
  knowledge and never ask what programme, split or goal they follow — read their actual
  history first and build from it.
---

# Garmin Strength Workout Builder

**Skill build: v1.13.0**

Generate custom gym workouts and write them as Python files the user uploads to Garmin Connect.
All workouts target a **fully equipped gym** (barbells, cables, machines, dumbbells, smith machine).
Default duration: **45–50 minutes**. Bodyweight exercises only if they genuinely fit (dips, pull-ups
on a cable-assist machine are fine; push-ups are not — the gym has better options).

The project lives at `~/Projects/garmin-workouts/`. Run every command from that directory.

**Before anything else: make sure you can actually reach it.** This project almost always sits
outside the current working directory, so file reads and shell commands against it fail with a
sandbox/permission error until access is granted. Don't try to work around that error, and don't
report it back as a dead end — request the directory:

> Use the directory-access tool (`request_directory`) with path `~/Projects/garmin-workouts`,
> then continue once the user approves.

Ask for the **project root**, not an individual file — every command needs sibling files
(`performance.json`, `history.json`, `workouts/`, the `garmin_workouts/` package), so per-file
access just fails again one step later. If access is refused, say plainly that the skill can't
run without it rather than pretending to have data.

Everything runs through one command, `garmin`, installed via `pip install -e .`:
- `garmin sync` — pulls **completed** sessions into `performance.json` (actual reps and weight)
- `garmin suggest` — which muscle groups to train next; `--as-of`, `--planned`, `--planned-date`
- `garmin coach` — verdicts per exercise; `--brief`, `--muscles`, `--prescribed`
- `garmin upload <file>` — validates then pushes; `--dry-run` checks without uploading
- `garmin validate <file>` — checks exercises against the real Garmin FIT SDK
- `garmin run` — running intensity distribution and VO2max trend; `--days`
- `garmin plan` — a week of strength and running together; `--goal`, `--start`
- `garmin login` — one-time interactive auth, caches a session so nothing else prompts

If `garmin` is not found, run `pip install -e .` from the project directory. The older
`python coach.py --suggest` form still works — the root scripts forward to the same code — so
prefer `garmin ...`, but don't treat the old form as broken if you see it.

The root scripts are argument parsing only. All logic lives in the `garmin_workouts/` package:
`store` (owns `performance.json`), `sync` (fetches from Garmin), `judging` (verdicts),
`planning` (muscle-group choice), `report` (terminal formatting), `workout`, `validation`,
`history`, `client` (auth), and `constants` — which holds every tuned threshold.

Change logic in the package, not in the root scripts. Tests are in `tests/` — run
`python -m pytest` after touching anything in the package.

**`progress.py` no longer exists** — it was folded into `garmin coach --prescribed`.

**Verifying which build is loaded.** If the user asks what version of the skill you have, or
says a recent change doesn't seem to be working, report the `Skill build:` version at the top of
this file. A conversation keeps the skill text it started with, so a chat opened before an update
will keep using the old instructions no matter how many times the file is reinstalled — the fix
is a new chat, not another reinstall. Comparing the reported build against what they expect
settles it in one question.

**Read the Troubleshooting section at the bottom before debugging anything environment-related.**
It documents real failures already hit and solved — don't rediscover them.

---

## Workflow

### Which flow are you in?

There are two, and they are not the same request. Getting this wrong is the most common failure
of this skill.

**Flow A — plan a week** ("plan my week", "what should I train this week", "how do I fit running
in"). Produces a *schedule*: which day, which muscle groups, easy or quality run. Run
`garmin plan`, present the week, and **stop there**. A schedule is not a workout. Do not write
any workout file, and do not invent exercises for the days.

Then say, in these words or close to them:

> "That's the shape of the week. Want me to build Monday's session? I'll give you three options
> to pick from."

**Flow B — build one session** ("build Monday's workout", "make me a chest day", or the user
accepting the offer above). This is the numbered Step 0–5 sequence below, and **Step 3 is not
optional**: offer three genuinely different options and wait for a choice before writing anything.

**Flow A always hands off to Flow B — once per day, one day at a time.** Never run Flow B for
seven days unprompted. A week of finished workouts the user never chose is exactly the complaint
this structure exists to prevent: they wanted options and got decisions.

If the user asks for a week and you find yourself listing exercises, you have skipped the
handoff — go back and offer.

---

### Step 0 — Pull performance and let it drive the programming

**Always do this before proposing exercises.** New workouts are built on what the user
actually lifted, not on generic templates.

```bash
cd ~/Projects/garmin-workouts
garmin sync                                    # refresh from Garmin (idempotent)
garmin coach --brief --muscles chest shoulders # verdicts for today's muscle groups
```

Each line comes back as:

```
BARBELL_BENCH_PRESS: 70.0kg x6/6 (2026-07-27, 4 sessions) [progressing] -> add 5.0kg -> 75.0kg x 6
```

Apply the verdict directly when choosing exercises and prescribing reps:

| Verdict | What it means | What to program |
|---|---|---|
| `ready` | Hit the rep target on every working set | Keep the exercise, take the suggested load jump, reps back to the bottom of the range |
| `progressing` | Load or reps trending up | Keep it, keep the progression going |
| `holding` | Target not hit on all sets yet | Keep it, same load, don't add volume |
| `stalled` | Same weight 3+ sessions, no rep gain | **Swap the variation** (e.g. barbell RDL → dumbbell RDL) or drop to a lower rep range |
| `regressed` | Meaningful drop vs the last clean session | Program it lighter and rebuild; don't pile on volume |
| `stale` | Not trained in 21+ days | Good candidate to bring back, but restart conservatively |
| `check-data` | The logged number is not trustworthy | **Never progress off this.** Mention it and ask what they actually lifted |
| `baseline` | Only one clean session | Repeat the same prescription to establish a trend |

Mention the two or three findings that actually shaped the workout — especially anything
`stalled` or `check-data` — so the user sees why it differs from last time. Don't dump the
whole table at them.

**Unlabelled sets.** `garmin coach` (no `--muscles` filter) ends with any sets that had
real weight and reps but no exercise name from the watch. These belong to no verdict, and
they're frequently the heaviest work of the session — the watch classifies heavy barbell
work poorly. Before acting on a `regressed` verdict, check whether that session has
unlabelled heavy sets that are probably the same lift. Ask the user rather than assuming.

If `performance.json` doesn't exist yet, say so and run `garmin sync` before continuing.

**Adherence — the prescription itself may be wrong.** `garmin coach` flags exercises where
what was asked for and what happened disagree twice running, as `ADHERENCE: asked for 10, got
7/7 twice — prescribe 7 next time, not 10`. Follow it. Repeating a target that has been missed
twice just repeats the miss, and the lifter reads it as failing rather than the number being
badly set. The same applies upward: consistently beating a target means it is too soft.

**Recovery.** `garmin suggest` prints a `Recovery:` line when sleep or Garmin's training
readiness is genuinely off. When it fires, prefer holding load or trimming a set over
progressing, and say why. When it says nothing, nothing is wrong — don't invent a caveat.

**Timed holds.** Planks and similar use `"seconds": 45` instead of `"reps"`. The watch runs the
timer correctly but still prompts for a rep count afterwards; that number is meaningless and the
analysis ignores it in favour of the recorded duration. Warn the user once that the rep prompt
on a plank can be skipped or filled with anything.

**Any question about a week, a schedule, or "what should I train this week" is a `garmin plan`
question, not a `garmin suggest` one.** `garmin suggest` answers "what next"; it names muscle
groups and nothing else. Use `garmin plan` and present the whole week.

When you do, always give **which day** and **when in the day**, and **always include the runs** —
a week that lists only lifting is not the week the tool produced:

> **Mon** — strength, core + shoulders (48 min)
> **Wed am** — quality run, 5x3min at ~93% max HR
> **Wed pm** — nothing; keep the day light around the run
> **Fri** — easy run, 30 min conversational

Time of day is only stated when it matters. A day holding two sessions is marked `am`/`pm` and
must stay that way — lift first, run second, six hours apart. A day with one session shows `—`,
meaning any time suits; don't invent a time for it.

**Respect the days the user says they can train.** If they say Monday to Friday, pass
`--weekdays mon-fri`. Never schedule onto a day they've ruled out, and never quietly exceed the
session count they asked for — `--strength 4 --runs 2` means exactly that.

**Sync before planning; don't ask them to.** `garmin plan` refreshes automatically when local
data is behind, so just run it. Asking the user to run `garmin sync` themselves is a step they
should never have to think about, and planning off stale data quietly produces last week's
advice — a run that moved their VO2max is exactly the thing that should change the plan.

**Let the tool pick the split, and say when it disagrees with the user.** `garmin plan` works
out the week's mix from their history: it caps how fast running volume grows, adds a quality
session instead of easy volume when VO2max has gone flat, and drops a strength session when
recovery is poor. `--strength N --runs M` overrides it. When the user overrides, the plan says
what it would have chosen — pass that on rather than silently agreeing. Being a coach means
having a view, not just accepting the request.

**Always say where to run, not just how long.** A duration means nothing standing at the door.
Convert it with `garmin distance <minutes>`, which uses their own logged pace, then suggest a
route shape:

- **Out and back on a linear route** (canal towpath, river path, seafront) is the default. Run
  half the time out, turn round. It needs no map, no measured loop, and self-corrects if the pace
  drifts — which matters more than picking a scenic route.
- **Laps of a park or a known loop** when they want to stay close to home, or for intervals where
  stopping to check a turn breaks the effort.
- Ask once where they usually run and reuse it.
Never state a distance between two landmarks as fact — you cannot verify it, and a confident
wrong number produces a run of the wrong length. Give the target distance and the halfway time;
the athlete turns round when the watch says so, which needs no map and cannot be wrong.

Do not try to build a Garmin course. Garmin Connect already has a course creator with round-trip
routing; generating routes would need an external mapping service and would be worse.

**A plan is a schedule, not a set of workouts — see "Which flow are you in?" above. After
presenting it, offer to build one day and wait.**

**Planning a week.** `garmin plan --goal vo2max` lays out seven days across both disciplines.
It encodes the interference constraints — legs never adjacent to a quality run, easy runs allowed
to share a day with upper-body work six hours apart, priority session first. Use it when the user
asks about a week, a schedule, or how to fit running and lifting together. Pass on its ramp
warning: if it says the plan is a step up from current volume, say so rather than presenting the
week as immediately achievable.

**Cardio is part of the picture.** `garmin run` shows how running effort is distributed across
heart-rate zones plus the VO2max trend. It matters to strength programming because heavy legs
and quality runs interfere with each other: don't put a heavy leg session the day before a hard
run, and if both fall on one day, the priority session goes first and the other stays easy and
short. An easy 20-30 min run pairs fine with a strength session hours apart.

**Weight is a suggestion, not a prescription in the file.** Garmin workout steps carry
exercise/sets/reps/rest only — there's no weight field — so target loads belong in the
conversation and in the workout `description`, never as a field in the exercise dict.

### Step 1 — Gather requirements

The user must provide:
- **At least 2 muscle groups** (e.g. chest + shoulders, back + biceps, quads + hamstrings)
- Duration if they want something other than the 45–50 min default

**If they haven't said which muscle groups — or they ask what they should train — don't
guess and don't ask blind. Run:**

```bash
garmin suggest
```

It reports every group's last-trained date, session count and set count, then recommends a
pairing based on recovery (nothing trained inside 48h) and volume deficit (sets relative to
the most-trained group). Lead with that recommendation and the reason, e.g.:

> "You haven't trained core in 10 days — 16 sets logged against 120 for legs. Suggest core +
> triceps, since everything else is still inside 48h. Want that, or something else?"

**If they name a future day, or mention a session they plan to do first, pass both in.**
Recovery is measured against the day being trained, not today, and a session that hasn't reached
Garmin yet still uses up recovery:

```bash
# "a workout for Monday, given I might train core and shoulders tomorrow"
garmin suggest --as-of 2026-08-10 --planned core shoulders --planned-date 2026-08-07
```

Work out the real dates before running it — don't pass "Monday". Without `--planned`, the tool has
no idea about the intended session and will happily prescribe the same muscles twice in a row.

Respect what it says:
- **`take a rest day`** — everything trained inside 48h. Say so rather than programming
  another session on top; offer a light/mobility option only if they push.
- **Volume deficit can outvote good programming.** A badly under-trained group keeps winning even
  right after it was trained, because deficit dominates the score. If the tool suggests repeating
  the group they just did while a major group (chest/back/legs) sits several days rested, say so
  and offer the major group instead — usually as the `note:` line already suggests. Don't just
  read the tool's output back.
- **The `note:` line** — when it fires, the pairing is two small groups and can't honestly
  fill 45–50 min without junk volume. Pass that on, along with the alternative it names.

The user can always override — if they ask for chest the day after chest, build it, but tell
them what the data says first.

### Step 2 — Check history before proposing options

Read `history.json` (via `history.last_session_for(slug)`, or just read the JSON directly) for
the most recent logged session matching this muscle-group slug. If one exists, use it to inform
progression instead of guessing from scratch:
- If an exercise repeats, nudge it forward — add a rep or two within its rep range, or add a set
  if it was already at the top of the range. Note the bump inline, e.g. "Incline DB Press 3×11
  (up from 3×10 last time)".
- If nothing is logged yet for this slug, proceed as normal — there's nothing to progress from.

This is volume/rep progression based on what was actually programmed before, not weight-based
progression — this project doesn't read back actual weight lifted from Garmin Connect's activity
data, so don't claim to know what weight the user used.

### Step 3 — Offer 3 workout options  (never skip this)

**Stop and offer. Do not write a file in this step.** Whether the user asked for a single session
or accepted a day from a weekly plan, they choose the exercises — you don't.

Present three distinct options. **Each option must use a meaningfully different set of exercises**
for the same muscle groups — not just the same movements with different rep counts. Think of it as
three different routes to train the same muscles: one might be barbell-led, one dumbbell/cable-led,
one machine-led, or they simply emphasise different angles and movement patterns.

**Exercise count is not fixed.** Let it fall out of the time budget and the design of each option —
a dense, short-rest circuit-style session might run 10–12 exercises, while a heavy compound day with
90s rests might only fit 6–7. Varying the count *between* options is a feature, not a flaw: it gives
the user a real structural choice, not just three flavours of the same shape. Say what each option
trades off (fewer heavier movements vs. more variety/volume) so the choice is informed. Just keep
total time in the target range and order things sensibly.

Label them A / B / C and list the exercises with sets×reps inline, plus a one-line note on what
each option is *for*. Example for chest + shoulders:

> **Option A** — Barbell-anchored, 7 exercises
> Barbell Bench Press 4×8 · Incline Barbell Bench Press 3×10 · Cable Crossover 3×12 · Barbell Shoulder Press 4×8 · Barbell Push Press 3×8 · Dumbbell Lateral Raise 3×15 · Bent-Over Lateral Raise 3×15
> *Heaviest option, fewer movements, longest rests — strength focus.*
>
> **Option B** — Dumbbell & cable, 8 exercises
> Incline Dumbbell Bench Press 4×10 · Dumbbell Bench Press 3×10 · Cable Crossover 3×12 · Incline Dumbbell Flye 3×12 · Arnold Press 3×10 · Seated Dumbbell Shoulder Press 3×10 · One Arm Cable Lateral Raise 3×15 · Front Raise 3×12
> *More volume, joint-friendlier, hits more angles.*
>
> **Option C** — Machine + free weight mix, 10 exercises
> Dumbbell Flye 4×12 · Smith Machine Bench Press 3×10 · Incline Dumbbell Bench Press 3×10 · Cable Crossover 3×15 · Seated Dumbbell Shoulder Press 4×10 · Dumbbell Lateral Raise 3×15 · Kneeling Rear Flye 3×12 · Face Pull 3×15 · Front Raise 3×12 · Seated Rear Lateral Raise 3×15
> *Highest exercise variety, shorter rests, most stable/controlled.*

Aim for as little overlap between options as possible so the user gets a real choice. Only use
exercise names that appear in the Exercise Reference table below — every entry there is verified
against Garmin's real FIT SDK, so there's no risk of picking something that fails validation later.

### Step 3a — Keep the session in one place at a time

Order exercises so each station is used once and left. Bench, bench, cable, bench means walking
away from a bench mid-session and finding it taken — the workout reads fine and runs badly.

`garmin validate` reports station revisits and prints a suggested order. Act on it.

**Group within the effort tier, don't reorder across it.** Heaviest compounds still come first,
while the lifter is fresh; grouping applies to what's left. If a heavy barbell lift and a cable
finisher are on different stations, that's one walk and it's fine — the problem is only ever
going *back*.

Station is inferred from the exercise name because Garmin's categories describe the movement, not
the kit: `BENCH_PRESS` covers both a barbell on a flat bench and a dumbbell press. The inference
is a heuristic and occasionally wrong (a kneeling cable flye may read as bench work) — if the user
says the order is off, believe them over the tool.

### Step 3b — Always link a demo for every exercise

**The user does not want to go hunting for form videos.** So never present a bare exercise name.
Once they pick an option — and whenever they ask about any single exercise — give each movement a
one-click demo link, as a markdown link on the exercise name itself:

```
[Reverse Grip Barbell Row](https://www.youtube.com/results?search_query=reverse+grip+barbell+row+proper+form) 4×8
```

Build the URL from the exercise name: strip a leading underscore, replace remaining `_` with
spaces, lowercase, URL-encode with `+`, append `+proper+form`. **Keep any digits** — Garmin writes
`_30_DEGREE_LAT_PULLDOWN`, and dropping the 30 turns it into "degree lat pulldown", which searches
for nothing useful. Correct result: `30+degree+lat+pulldown+proper+form`.

Do this for anything unfamiliar or newly introduced, and for the whole list on request. For the
three options in Step 3 keep the inline list readable — link there only when an option contains a
movement the user has never been prescribed before (check `history.json`), and say why it's new.

When the user asks about one specific exercise, also describe the movement in two or three lines —
setup, the working range, and the single most common mistake — so the link is confirmation rather
than the only source. Never claim to have watched a video or seen an image.

**Do not try to render exercise images inline.** The chat widget and artifact sandboxes only permit
a fixed CDN allowlist, so images from an exercise library are silently blocked; a page that looks
broken is worse than a link that works. A local page with real images exists on the
`exercise-previews` branch (`preview.py`) if the user ever asks for it back.

### Step 4 — Create the workout file

Once the user confirms a choice, write the workout to:
`~/Projects/garmin-workouts/workouts/<slug>_<N>.py`

Where:
- `<slug>` = muscle groups lowercased, spaces→underscores (e.g. `chest_shoulders`)
- `<N>` = next available integer (check existing files, never overwrite unless the user explicitly asks to replace a specific numbered file)

Then run `garmin validate workouts/<filename>.py` yourself (via shell) to confirm it's clean
before telling the user it's ready — don't just trust the reference table, actually check.

### Step 4c — Moving a session to a different day

**Uploaded workouts carry no date.** A workout on the watch is just a workout; the plan's "Tue:
triceps + chest" is advice, not a booking. So doing Wednesday's session on Thursday needs nothing
uploaded, deleted or rescheduled — just do it.

What *does* change is the spacing. Re-run the plan with the days that actually apply
(`garmin plan --weekdays ...`) and check two things: no leg session directly beside a quality run,
and each muscle group still getting 48 hours. Say plainly if the swap breaks one of those; say
plainly if it doesn't, rather than inventing a problem.

**On the watch's workout limit**: run `garmin workouts --watch` before uploading if the user has
been generating a lot. It reports how full Garmin Connect is against the watch's cap and lists
what is safest to remove — exact duplicates first, then never-completed workouts, then oldest.

The cap belongs to the device, not the account: everything synced to the watch counts, however it
got there. fenix 6 and 7 are documented at 25; the fenix 8 number is not confirmed, so the tool
assumes 25 and `GARMIN_WORKOUT_LIMIT` overrides it once the watch says otherwise.

`garmin plan` and `garmin upload` both check capacity themselves — the plan says whether the
week's sessions will fit before anything is built, and the upload warns before consuming a slot.
Pass that on when it appears; don't wait for the watch to refuse an upload.

`garmin workouts --cleanup` frees slots by deleting the safest candidates, but **always shows what
it will remove and requires the user to type `delete` first**. Never pass `--yes` on their behalf,
and never delete without showing the list — deletion is irreversible, and "never completed" rests
on a name match, so a renamed workout reads as unused.

It removes only as many as needed to leave five free slots, duplicates first, and **never touches
a workout that was actually completed** even when the account is over the limit. Making room by
deleting a session they did is the athlete's call, not the tool's.

There is also no scheduling trick that avoids the cap; uploaded workouts carry no date.

### Step 5 — Upload

Check whether `~/Projects/garmin-workouts/.garmin_session/` exists:
- **If it exists**: a session is cached, so no credentials are needed. Whether *you* can run the
  upload depends entirely on network reach — see Troubleshooting → "Can't reach Garmin from the
  sandbox". Verify with a quick `curl` before promising to run it; if blocked, give the user the
  command instead of pretending it'll work.
- **If it doesn't exist**: tell the user to run `python login.py` once themselves, in their own
  terminal (never ask them to paste a password into chat).

Command to hand over:
```
cd ~/Projects/garmin-workouts
garmin upload workouts/<filename>.py
```

---

## Duration Estimation

Target **2700–3000 seconds (45–50 min)** total.

Estimate per exercise: `sets × (45s work + rest_seconds)`

| Exercise type             | rest_seconds | Sets | ~Time  |
|---------------------------|-------------|------|--------|
| Compound (barbell/cable)  | 90s         | 4    | 9 min  |
| Moderate compound / DB    | 75s         | 3–4  | 7 min  |
| Cable / isolation         | 60s         | 3    | 5 min  |
| High-rep finisher         | 45s         | 3    | 4 min  |

Exercise count follows from this budget rather than a fixed rule — heavy long-rest sessions land
around 6–7 movements, denser short-rest ones can reach 10–12. Verify by running
`python -c "import upload; w=upload.load_workout('workouts/<file>.py'); print(upload.estimate_duration(w))"`
rather than eyeballing it.

---

## Rest Time Rules

**Maximum rest is 90 seconds.** Always set `rest_seconds` per exercise — never a blanket value.

| Exercise class                  | rest_seconds |
|---------------------------------|-------------|
| Compound (barbell / heavy cable)| 90          |
| Moderate compound / machine     | 75          |
| DB / cable isolation            | 60          |
| High-rep finisher (15–20 reps)  | 45          |

---

## Workout File Format

```python
# <Workout Name> — <muscle groups> (session N)
# Run: garmin upload workouts/<filename>.py

WORKOUT = {
    "name": "Chest & Shoulders 1",
    "description": "One-line description of the session focus",
    "exercises": [
        # Heavy compounds first, isolations last
        {"name": "BARBELL_BENCH_PRESS",           "category": "BENCH_PRESS",   "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "INCLINE_DUMBBELL_BENCH_PRESS",  "category": "BENCH_PRESS",   "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "CABLE_CROSSOVER",               "category": "FLYE",          "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "BARBELL_SHOULDER_PRESS",        "category": "SHOULDER_PRESS","sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "DUMBBELL_LATERAL_RAISE",        "category": "LATERAL_RAISE", "sets": 3, "reps": 15, "rest_seconds": 60},
    ],
}
```

For time-based sets, use `"seconds": 45` instead of `"reps"` (e.g. planks).

---

## Auto-increment Filenames

Before writing, check which numbered files already exist:
```python
from pathlib import Path
slug = "chest_shoulders"
n = 1
while Path(f"~/Projects/garmin-workouts/workouts/{slug}_{n}.py").exists():
    n += 1
filename = f"{slug}_{n}.py"
```

---

## Validation — always verify, never guess

`validate.py` reads the `*_exercise_name` enums straight out of the installed `garmin_fit_sdk`
package's source rather than trusting a hand-maintained table. Run it after writing any new
workout file:

```
garmin validate workouts/<filename>.py
```

`upload.py` also calls this automatically before pushing anything, so a bad name/category pair is
caught before upload rather than after. If you want an exercise that isn't in the reference table
below, don't guess a plausible-sounding name — run validate.py rather than assume.

---

## Exercise Reference

Every name below is a **confirmed, exact match** against the Garmin FIT SDK's real exercise enum
(verified programmatically, not guessed) — safe to use as-is. This is a curated subset for a
fully-equipped commercial gym, not the complete library (Garmin's list runs into the hundreds per
category, including many CrossFit/bodyweight/physio variants not relevant here). If you need
something not listed, run `validate.py` against it before using it.

### Chest
| Garmin name                    | category     |
|---------------------------------|--------------|
| BARBELL_BENCH_PRESS            | BENCH_PRESS  |
| INCLINE_BARBELL_BENCH_PRESS    | BENCH_PRESS  |
| DECLINE_DUMBBELL_BENCH_PRESS   | BENCH_PRESS  |
| DUMBBELL_BENCH_PRESS           | BENCH_PRESS  |
| INCLINE_DUMBBELL_BENCH_PRESS   | BENCH_PRESS  |
| SMITH_MACHINE_BENCH_PRESS      | BENCH_PRESS  |
| INCLINE_SMITH_MACHINE_BENCH_PRESS | BENCH_PRESS |
| CLOSE_GRIP_BARBELL_BENCH_PRESS | BENCH_PRESS  |
| CABLE_CROSSOVER                | FLYE         |
| DUMBBELL_FLYE                  | FLYE         |
| INCLINE_DUMBBELL_FLYE          | FLYE         |
| DECLINE_DUMBBELL_FLYE          | FLYE         |

### Shoulders
| Garmin name                    | category       |
|---------------------------------|----------------|
| BARBELL_SHOULDER_PRESS         | SHOULDER_PRESS |
| SEATED_BARBELL_SHOULDER_PRESS  | SHOULDER_PRESS |
| OVERHEAD_BARBELL_PRESS         | SHOULDER_PRESS |
| OVERHEAD_DUMBBELL_PRESS        | SHOULDER_PRESS |
| DUMBBELL_SHOULDER_PRESS        | SHOULDER_PRESS |
| SEATED_DUMBBELL_SHOULDER_PRESS | SHOULDER_PRESS |
| ARNOLD_PRESS                   | SHOULDER_PRESS |
| BARBELL_PUSH_PRESS             | SHOULDER_PRESS |
| DUMBBELL_PUSH_PRESS            | SHOULDER_PRESS |
| SMITH_MACHINE_OVERHEAD_PRESS   | SHOULDER_PRESS |
| MILITARY_PRESS                 | SHOULDER_PRESS |
| DUMBBELL_LATERAL_RAISE         | LATERAL_RAISE  |
| SEATED_LATERAL_RAISE           | LATERAL_RAISE  |
| ONE_ARM_CABLE_LATERAL_RAISE    | LATERAL_RAISE  |
| FRONT_RAISE                    | LATERAL_RAISE  |
| CABLE_FRONT_RAISE              | LATERAL_RAISE  |
| BENT_OVER_LATERAL_RAISE        | LATERAL_RAISE  |
| SEATED_REAR_LATERAL_RAISE      | LATERAL_RAISE  |
| KNEELING_REAR_FLYE             | FLYE           |
| FACE_PULL                      | ROW            |
| FACE_PULL_WITH_EXTERNAL_ROTATION | ROW          |

### Back
| Garmin name                  | category |
|-------------------------------|----------|
| BARBELL_ROW                  | ROW      |
| DUMBBELL_ROW                 | ROW      |
| SEATED_CABLE_ROW             | ROW      |
| T_BAR_ROW                    | ROW      |
| ONE_ARM_BENT_OVER_ROW        | ROW      |
| SEATED_DUMBBELL_ROW          | ROW      |
| CABLE_ROW_STANDING           | ROW      |
| CHEST_SUPPORTED_DUMBBELL_ROW | ROW      |
| PULL_UP                      | PULL_UP  |
| CHIN_UP                      | PULL_UP  |
| WIDE_GRIP_PULL_UP            | PULL_UP  |
| NEUTRAL_GRIP_PULL_UP         | PULL_UP  |
| WEIGHTED_PULL_UP             | PULL_UP  |
| LAT_PULLDOWN                 | PULL_UP  |
| WIDE_GRIP_LAT_PULLDOWN       | PULL_UP  |
| CLOSE_GRIP_LAT_PULLDOWN      | PULL_UP  |

### Legs
| Garmin name                       | category  |
|-------------------------------------|-----------|
| SQUAT                             | SQUAT     |
| BARBELL_BACK_SQUAT                | SQUAT     |
| BARBELL_FRONT_SQUAT               | SQUAT     |
| BARBELL_HACK_SQUAT                | SQUAT     |
| LEG_PRESS                         | SQUAT     |
| GOBLET_SQUAT                      | SQUAT     |
| DUMBBELL_SQUAT                    | SQUAT     |
| BARBELL_DEADLIFT                  | DEADLIFT  |
| ROMANIAN_DEADLIFT                 | DEADLIFT  |
| SUMO_DEADLIFT                     | DEADLIFT  |
| TRAP_BAR_DEADLIFT                 | DEADLIFT  |
| DUMBBELL_DEADLIFT                 | DEADLIFT  |
| RACK_PULL                         | DEADLIFT  |
| BARBELL_LUNGE                     | LUNGE     |
| DUMBBELL_LUNGE                    | LUNGE     |
| WALKING_LUNGE                     | LUNGE     |
| WALKING_DUMBBELL_LUNGE            | LUNGE     |
| BARBELL_REVERSE_LUNGE             | LUNGE     |
| BARBELL_BULGARIAN_SPLIT_SQUAT     | LUNGE     |
| DUMBBELL_BULGARIAN_SPLIT_SQUAT    | LUNGE     |
| HIP_RAISE                         | HIP_RAISE |
| BARBELL_HIP_THRUST_WITH_BENCH     | HIP_RAISE |
| BARBELL_HIP_THRUST_ON_FLOOR       | HIP_RAISE |
| STANDING_CALF_RAISE               | CALF_RAISE|
| STANDING_BARBELL_CALF_RAISE       | CALF_RAISE|
| STANDING_DUMBBELL_CALF_RAISE      | CALF_RAISE|
| SEATED_CALF_RAISE                 | CALF_RAISE|
| DONKEY_CALF_RAISE                 | CALF_RAISE|

### Arms
| Garmin name                            | category          |
|------------------------------------------|-------------------|
| BARBELL_BICEPS_CURL                    | CURL              |
| DUMBBELL_BICEPS_CURL                   | CURL              |
| SEATED_DUMBBELL_BICEPS_CURL            | CURL              |
| STANDING_DUMBBELL_BICEPS_CURL          | CURL              |
| INCLINE_DUMBBELL_BICEPS_CURL           | CURL              |
| CABLE_BICEPS_CURL                      | CURL              |
| DUMBBELL_HAMMER_CURL                   | CURL              |
| CABLE_HAMMER_CURL                      | CURL              |
| EZ_BAR_PREACHER_CURL                   | CURL              |
| STANDING_EZ_BAR_BICEPS_CURL            | CURL              |
| TRICEPS_PRESSDOWN                      | TRICEPS_EXTENSION |
| ROPE_PRESSDOWN                         | TRICEPS_EXTENSION |
| REVERSE_GRIP_TRICEPS_PRESSDOWN         | TRICEPS_EXTENSION |
| CABLE_OVERHEAD_TRICEPS_EXTENSION       | TRICEPS_EXTENSION |
| SEATED_DUMBBELL_OVERHEAD_TRICEPS_EXTENSION | TRICEPS_EXTENSION |
| OVERHEAD_DUMBBELL_TRICEPS_EXTENSION    | TRICEPS_EXTENSION |
| LYING_EZ_BAR_TRICEPS_EXTENSION         | TRICEPS_EXTENSION |
| CABLE_LYING_TRICEPS_EXTENSION          | TRICEPS_EXTENSION |
| BODY_WEIGHT_DIP                        | TRICEPS_EXTENSION |
| WEIGHTED_DIP                           | TRICEPS_EXTENSION |

### Core
| Garmin name              | category   |
|----------------------------|------------|
| PLANK                    | PLANK      |
| SIDE_PLANK                | PLANK      |
| CABLE_CRUNCH              | CRUNCH     |
| STANDING_CABLE_CRUNCH     | CRUNCH     |
| KNEELING_CABLE_CRUNCH     | CRUNCH     |
| HANGING_LEG_RAISE         | LEG_RAISE  |
| HANGING_KNEE_RAISE        | LEG_RAISE  |
| LYING_STRAIGHT_LEG_RAISE  | LEG_RAISE  |
| RUSSIAN_TWIST             | CORE       |
| CABLE_SIDE_BEND           | CORE       |
| BARBELL_ROLLOUT           | CORE       |

---

## Programming Guidelines (coach knowledge)

**Exercise order:** Always heavy compounds first (when the CNS is fresh), moderate compounds
second, isolations last. Never program deadlifts after squats in the same session.

**Rep ranges:**
- Heavy/compound: 6–8 reps, 4 sets, 90s rest
- Moderate: 10–12 reps, 3–4 sets, 60–75s rest
- Isolation/finisher: 12–15 reps, 3 sets, 45–60s rest

**Muscle group pairing logic:**
- Chest + Shoulders → push muscles, share OHP and bench mechanics
- Back + Biceps → pull muscles, biceps already get work on rows/pulldowns
- Quads + Hamstrings → full leg day, squat + deadlift variant
- Quads + Glutes → squat focus + hip thrust
- Chest + Triceps → triceps assist on all pressing
- Back + Rear Delts → rows hit rear delts naturally
- Chest + Abs → unrelated muscle groups, so chest work first at full intensity, then core

**Variety and progression across sessions:** Check `history.json` for the last logged session with
this slug (see Step 2) and use it. If nothing's logged, fall back to varying exercises from
whatever the most recent workout *file* for this slug used.

---

## Troubleshooting — known issues and their fixes

These are all real failures already hit and diagnosed. Check here first.

### "Outside the sandbox" / permission denied on the project files
Reading `performance.json`, `history.json` or anything else under `~/Projects/garmin-workouts/`
fails when that folder is outside the current working directory — which it usually is.

**Fix:** request access to the project root with the directory-access tool
(`request_directory`, path `~/Projects/garmin-workouts`), then retry. This is a one-time approval
per session, not something to code around.

Do **not**: guess at the data, fall back to generic programming, copy files elsewhere, or tell the
user the file is missing — it exists, it's just not reachable yet. `performance.json` is also
gitignored, so it will never appear via a git remote; the local folder is the only source.

### How the user should log weight on the watch

These come up often and the answer matters, because every verdict compares an exercise against
its own history — so **consistency matters far more than which convention**. Inconsistency
within one exercise is what produces `check-data` flags.

- **Dumbbells: log ONE dumbbell.** Most of this user's history already does (lateral raise
  7-12kg, hammer curl 10-12kg, shoulder press 14-18kg). `DUMBBELL_PUSH_PRESS` at 52kg is the
  odd one out — that is a pair total and breaks the trend for that exercise.
- **Bodyweight moves (dips, pull-ups): log total load — bodyweight plus anything added.**
  Garmin often pre-fills bodyweight, so this fights the watch least. Their dip history reads
  9, 76, 72, 19kg — a mix of both conventions, which is why it is untrustworthy.
  Whichever they pick, they must not alternate.
- **Assisted machines**: log the weight actually moved, not the assist.

If they change convention, say the affected exercise will read as a big jump or drop for one
session and may be flagged `check-data` — that is the guard working, not a bug.

### Exercise-name gotchas (caused a silent wrong-exercise bug)
Garmin's naming does not match gym vernacular. Confirmed traps:
- **No generic `LATERAL_RAISE`** — invalid on its own. Use `DUMBBELL_LATERAL_RAISE` etc.
- **No pec deck entry at all** (`PECK_DECK`/`PEC_DECK` both invalid). Substitute `DUMBBELL_FLYE`
  or `CABLE_CROSSOVER`.
- **`FACE_PULL` is category `ROW`**, not `LATERAL_RAISE`.
- **Rear delt fly is `KNEELING_REAR_FLYE`**, category `FLYE`. No "machine" variant exists.
- **No chest press machine entry** — substitute `DUMBBELL_BENCH_PRESS` or a smith machine variant.
- **Bulgarian split squat is category `LUNGE`**, not `SQUAT`.
- **Core is four separate categories** (`PLANK`, `CRUNCH`, `LEG_RAISE`, `CORE`), not one bucket.
- **No `DEAD_BUG` entry.**

**Fix / prevention:** never hand-guess a name. `validate.py` parses the installed SDK and suggests
close matches on failure. When substituting because no real entry exists, say so explicitly to the
user rather than silently swapping — they will notice and ask.

### `TypeError: __init__() got an unexpected keyword argument 'prompt_mfa'`
**Cause:** an old `garminconnect` (0.2.x) is installed. That version's `Garmin.__init__` only takes
`(email, password, is_cn)`; `prompt_mfa` is a modern-version feature.

**Root cause underneath it:** the user was on **Python 3.9** (via pyenv). Modern `garminconnect`
requires **3.10+**, so `pip install --upgrade garminconnect` silently did nothing and left 0.2.x in
place — producing the *identical* error again and wasting a round trip.

**Fix:**
```
python3 --version                 # confirm the real interpreter in use
pyenv install 3.12 && pyenv local 3.12
pip install --upgrade garminconnect curl_cffi garmin-fit-sdk
```
Then re-run `login.py`. **Always confirm the version actually changed** after an upgrade —
`pip show garminconnect` — before telling the user to retry.

**Also:** `login.py` and `upload.py` now introspect `Garmin.__init__` and only pass `prompt_mfa`
if supported, so this should degrade to a real error rather than a TypeError.

### Login fails on `garminconnect` 0.2.x even with correct code
`garminconnect` 0.2.x is built on **`garth`, which is deprecated**. Its maintainer has stated Garmin
changed their auth flow and **new logins through garth no longer work** — only previously-saved
sessions survive until they expire. No code change fixes this. The only path is upgrading to a
modern `garminconnect` on Python 3.10+.

### Can't reach Garmin from the sandbox
The assistant's shell is network-restricted to an allowlist that **does not include Garmin's
domains**. `connect.garmin.com`, `connectapi.garmin.com` and `sso.garmin.com` all return HTTP `000`
(connection never establishes). This is *not* a credentials problem — a cached session in
`.garmin_session/` is readable, the outbound connection is simply refused.

**Consequence:** the assistant cannot run `upload.py`. Don't promise to. Verify before claiming
either way:
```
curl -s -o /dev/null -w "%{http_code}\n" --max-time 6 https://connect.garmin.com
```
`000` = blocked, hand the user the command. Anything else = try it.

### Diagnosing library API mismatches generally
Before writing code against any version of these libraries, introspect what's actually installed
rather than trusting docs (GitHub master is often far ahead of the PyPI release the user has):
```
pip show garminconnect
python3 -c "import inspect, garminconnect; print(inspect.signature(garminconnect.Garmin.__init__)); print(inspect.signature(garminconnect.Garmin.login))"
```

### Deleting files
Deleting inside the user's folder needs explicit permission and will fail with "Operation not
permitted" until granted. Request it rather than reporting the delete as impossible. Better: avoid
creating stray files — check existing `workouts/` filenames *before* writing, so no cleanup is
needed.
