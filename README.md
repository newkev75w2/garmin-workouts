# garmin-workouts

Generate custom gym strength workouts and push them straight to Garmin Connect,
via a Claude Code skill.

Ask Claude for a workout ("build me a chest and shoulders workout for garmin"),
pick from three options, and it writes a Python file you upload with one
command. No manual JSON, no fumbling through the Garmin Connect workout builder.

## How the skill works

The skill lives in [`SKILL.md`](SKILL.md) and is packaged as a `.skill` file
that gets loaded into Claude Code / Claude Desktop. It triggers whenever you
ask to create a Garmin gym/strength workout.

0. **Claude pulls your recent performance first** (`garmin sync` + `garmin coach`) and
   programs off what you actually lifted — see [Closing the loop](#closing-the-loop).
1. **You provide at least 2 muscle groups** (e.g. "chest and shoulders").
   Duration defaults to 45–50 minutes unless you ask for something else.
2. **Claude offers 3 options**, each covering a genuinely different set of
   exercises for the same muscle groups (e.g. barbell-anchored vs.
   dumbbell/cable-focused vs. machine + free-weight mix) — not the same
   exercises with different rep schemes. Every workout is built for a fully
   equipped gym; bodyweight movements are used sparingly.
3. **You pick one.** Claude writes it to `workouts/<slug>_<n>.py`, where
   `<n>` auto-increments so nothing gets overwritten (a second chest day
   becomes `chest_shoulders_2.py`, and so on).
4. **You run the upload command** it gives you:
   ```bash
   garmin upload workouts/<filename>.py
   ```

The three options differ in **shape**, not just exercise choice: a heavy option
of 5–7 movements with long rests, a standard 8–9, and a dense 10–12 with short
rests. All land in the same 45–50 minutes — what changes is how the time is
spent. Exercises are ordered heaviest-compound first, grouped so you don't walk
back to a station you already left, with **per-exercise rest times** (never one
blanket value): compounds 90s, moderate lifts 75s, isolation 60s, finishers 45s.

## Closing the loop

Uploading a workout is only half of it. `garmin sync` pulls **completed** sessions
back down from Garmin Connect — actual reps and weight, per set — and `garmin coach`
judges them, so the next workout is built on real numbers instead of guesswork.

```bash
garmin sync             # pull completed sessions into performance.json
garmin coach            # verdict + next step for every exercise
garmin suggest          # which muscle groups to train next, and why
garmin coach --brief --muscles chest shoulders   # what the skill reads
```

`garmin suggest` answers "what should I train today?" from the log rather than habit —
it ranks every group by recovery (nothing trained inside 48h is offered) and by
volume deficit against your most-trained group:

```
group      last         days  sessions   sets  status
core       2026-07-27     10         3     16  recovered
triceps    2026-08-03      3         6     47  recovered
legs       2026-08-06      0         9    120  needs rest

Suggested next session: core + triceps
  why: core has 16 sets logged vs 120 for your most-trained group, last hit 10 days ago
  note: both are small groups — fine as a short accessory session, or wait a day
        and pair core with chest (rested 1d)
```

It will tell you to take a rest day if everything is inside 48h, and flags when a
pairing is two small groups that can't fill a session without junk volume.

Each exercise gets one of: `progressing`, `ready` (earned a load jump),
`holding`, `stalled` (same weight 3+ sessions — change the variation),
`regressed`, `stale` (untrained 21+ days), `baseline`, or `check-data`.

### It assumes the log is messy, because it is

Weights are typed in by hand on the watch, and that record has real errors in
it. From a 20-session log: a leg press reading `120, 16, 130, 150, 200, 140` kg;
a 431 kg push-up; dips logged as `9, 76, 72, 19` kg because Garmin sometimes
stores bodyweight and sometimes the added or assist load.

Taken at face value that data calls about a fifth of all exercises "regressed"
and would have you cutting load you never lost. So before judging anything,
the analysis:

- excludes sessions whose top weight falls outside 60–180% of that exercise's
  own median, and anything past an absolute plausibility ceiling
- ignores sessions where most sets were logged without a weight
- judges `BODY_WEIGHT_*` movements on reps alone
- requires a drop to clear **both** 10% and one load increment before calling it
  a regression, so a single pin on a cable stack isn't read as decline

Suspect figures aren't silently dropped — they surface as `check-data` with the
reason, and never feed progression. Everything is compared against an exercise's
own history, never across exercises.

`performance.json` is gitignored by default, since it's your actual training
data and this repo is public.

## Repo layout

`pip install -e .` provides the `garmin` command; everything it does lives in the
`garmin_workouts/` package, so it can be tested without going near the network.
The root scripts are thin shims kept so older `python coach.py` style commands
still work.

| File | Purpose |
|---|---|
| `SKILL.md` | The skill definition Claude reads — workflow, exercise reference table, rest-time/duration rules, coach programming guidelines. |
| `pyproject.toml` | Package metadata, dependencies, the `garmin` entry point and pytest config. |
| `garmin_workouts/cli.py` | The `garmin` command and all its subcommands. |
| `garmin_workouts/paths.py` | Where data lives — the checkout when run from one, `~/.garmin-workouts` when installed. |
| `coach.py`, `sync.py`, `upload.py`, `validate.py`, `login.py` | Shims forwarding to `garmin <subcommand>`, kept for backwards compatibility. |
| `garmin_workouts/constants.py` | Every tuned threshold and lookup table, in one documented place. |
| `garmin_workouts/store.py` | Owns `performance.json` — reads it, shapes sessions per exercise, flags what can't be trusted. |
| `garmin_workouts/sync.py` | Fetches completed sessions from Garmin and hands them to the store. |
| `garmin_workouts/judging.py` | Turns one exercise's history into a verdict and a next step. |
| `garmin_workouts/planning.py` | Picks which muscle groups to train next, from recovery and volume. |
| `garmin_workouts/report.py` | Formats results for the terminal, kept apart so wording can't change conclusions. |
| `garmin_workouts/workout.py` | Loads a workout file and builds Garmin's workout JSON payload. |
| `garmin_workouts/validation.py` | FIT SDK exercise-name validation. |
| `garmin_workouts/history.py` | Reading/writing `history.json` — what's been uploaded and when. |
| `garmin_workouts/client.py` | Authenticated-client setup, plus the interactive first-time login flow. |
| `tests/` | Synthetic-fixture tests pinning the analysis guards. |
| `workouts/` | Generated workout files, one per session. |

## Tests

```bash
pip install -e ".[dev]"
python -m pytest
```

The suite runs on synthetic fixtures, never on `performance.json` — that file is
personal and gitignored, so depending on it would make the tests unrunnable for
anyone else and change their meaning after every sync.

What they cover is deliberately narrow: the guards described above. Those
thresholds were fitted by hand against a real log, and the failure mode if one
drifts is not a crash but confident, wrong coaching advice — so each real
mis-logging case (the 16kg leg press, the 431kg push-up, the bodyweight dips,
the one-pin cable drop) has a test naming what it protects against.

## Setup

```bash
pip install -e .
garmin login
```

That installs the dependencies and puts a `garmin` command on your path. If you'd
rather not install, `pip install -r requirements.txt` still works and every command
below has a `python <script>.py` equivalent.

`login.py` prompts for your Garmin email/password (and MFA code if enabled)
interactively — credentials are never stored in code or passed as arguments,
only cached as a session token in `.garmin_session/`, which is git-ignored.

## Usage

Ask Claude to build a workout, confirm an option, then:

```bash
garmin upload workouts/<filename>.py
```

To see what was *programmed* for an exercise over time (as opposed to what you
actually lifted, which is what `coach.py` reports):

```bash
garmin coach --prescribed "incline dumbbell bench"
```

## Notes

- Targets `sportTypeId: 5` (`strength_training`) in Garmin's workout schema.
- Built against the `garminconnect` Python library (>=0.3) and its underlying
  `garth` HTTP client — there's no official public Garmin workout-creation API,
  so this reverse-engineers the same POST the Garmin Connect web app makes.
- `upload.py` runs `validate.py` automatically before every push.
