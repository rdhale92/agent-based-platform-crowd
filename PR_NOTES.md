# PR notes: whole-station geometry, NJT MultiLevel cars, free door choice, departing passengers

## Branch / commit
```
git checkout -b feature/whole-station-geometry
# replace simulator.py with the attached file
git add simulator.py
git commit -m "Use whole-station GeoJSON geometry; add MultiLevel cars, door choice and departing passengers"
git push -u origin feature/whole-station-geometry
```
Then open the PR on GitHub and paste the description below. (I could not open it myself: the repo is private.)

## PR description

**What changed**
- The polygon-image reader is replaced by a loader for `shapes_pcip_phase_1.geojson` (whole station, feet). It is downloaded next to the script on first run if missing. Platform 1-11 is chosen with a slider or `--platform N`.
- Trains: NJ Transit MultiLevel cars, 85 ft x 10 ft, one train per side of the platform, two platform-side doors per car. Cars-per-train and berth position are sliders.
- Alighting riders freely choose a door of their own car (walking distance to stairs + queue at the door + noise).
- Departing riders step off the stairs/escalators, choose a door of their train that is no longer letting people off, and board. Boarding opens `BOARDING_DELAY` (120 s) after arrival.
- Dashboard: platform / cars / berth / departing / boarding-delay sliders, a Boarded counter, blue departing riders, vector drawing of the station and cars, a Masks view of what the agents treat as wall.
- `python simulator.py --headless 600 --platform 5 --seed 1` runs without the GUI.

**Changes to the movement model** (all constants at the top): `PATIENCE_TICKS` (stuck riders stop avoiding crowds), `SWAP_OPPOSING_RIDERS`, `KEEP_CLEAR_PX` / `DEPARTING_MAX_CROWD`. Optional and off by default: `SQUEEZE_TICKS`, `MOUTH_SPACING_PX`, `STAIR_ENTRY_NEEDS_PLATFORM_ROOM = False`.

**Assumptions to review**
- Door positions (10 ft / 75 ft from the car's west end) and width (3 ft) are estimates; car length and width are published figures.
- Trains berth at the east end of the straight platform edge.
- Where the drawn walls completely close a stair/escalator mouth, an opening is cut through them (`OPEN_BLOCKED_VCE_MOUTHS`). 94 of 98 stairs/escalators are usable; the 4 that are not are on platform 7, behind a drawn wall line across the platform that is treated as solid. If that line is really a gate, platform 7 will behave very differently.
- Unnamed stairs/escalators in the GeoJSON are modelled as VCEs (`INCLUDE_UNNAMED_VCES`).
- A door is only used where at least `MIN_DOOR_DEPTH_PX` of open platform lies in front of it.
- "Eastern preference" now applies to the two easternmost usable stairs/escalators.

**Test results** (default settings: two 10-car trains, 60 alighting + 20 departing riders per car, seed 11, 450 s cap)

| Platform | Result |
|---|---|
| 5 | all 1,200 exited and 400 boarded by 273 s |
| 3 | all 1,080 exited and 360 boarded by 263 s |
| 4 | 1,140 / 1,140 exited, 374 / 380 boarded, 6 left |
| 8 | 1,172 / 1,200 exited, 388 / 400 boarded, 32 left |
| 6 | 972 / 1,140 exited, 372 / 380 boarded, 87 left; about 89 riders never get off the train (blocked doors) |
| 1, 2, 7, 9, 10, 11 | not run with the final defaults |

These are single-seed results and small code changes moved them by 10-15 points during development, so treat them as indicative only. Where riders are left, they are frozen in place (jams at stair mouths or doors), not slowly draining.
