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
   python upload.py workouts/<filename>.py
   ```

Each generated workout has **at least 8 exercises**, ordered heaviest-compound
first, and **per-exercise rest times** (never a single blanket rest value) —
compounds top out at 90s, moderate lifts 75s, isolation 60s, high-rep
finishers 45s.

## Repo layout

| File | Purpose |
|---|---|
| `SKILL.md` | The skill definition Claude reads — workflow, exercise reference table, rest-time/duration rules, coach programming guidelines. |
| `login.py` | One-time interactive login. Caches a session to `.garmin_session/` (git-ignored) so you don't re-enter credentials every upload. |
| `upload.py` | Loads a workout file, validates it, converts it to Garmin's workout JSON schema, and pushes it via the `garminconnect`/`garth` API. Logs the session to `history.json` on success. |
| `validate.py` | Checks every exercise name/category in a workout file against Garmin's official FIT SDK enum list, so a typo'd exercise is caught before upload, not after. |
| `history.py` | Shared helpers for reading/writing `history.json` — what's been uploaded and when. |
| `progress.py` | Shows how prescribed sets/reps/rest for an exercise have changed across logged sessions. |
| `workouts/` | Generated workout files, one per session. |

## Setup

```bash
pip install -r requirements.txt --break-system-packages
python login.py
```

`login.py` prompts for your Garmin email/password (and MFA code if enabled)
interactively — credentials are never stored in code or passed as arguments,
only cached as a session token in `.garmin_session/`, which is git-ignored.

## Usage

Ask Claude to build a workout, confirm an option, then:

```bash
python upload.py workouts/<filename>.py
```

To see progression across sessions for a given exercise:

```bash
python progress.py "incline dumbbell bench"
```

## Notes

- Targets `sportTypeId: 5` (`strength_training`) in Garmin's workout schema.
- Built against the `garminconnect` Python library (>=0.3) and its underlying
  `garth` HTTP client — there's no official public Garmin workout-creation API,
  so this reverse-engineers the same POST the Garmin Connect web app makes.
- `upload.py` runs `validate.py` automatically before every push.
