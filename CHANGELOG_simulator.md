# Changelog: `simulator.py`

Everything I changed in simulator.py, measured against the file as I first saw it: your commit `ff3ee37` ("Clean out old stuff.", Oct 6), 1,586 lines. The file now has 1,744 lines and matches my local commit `fb8a786` (not pushed, as you asked). It has not changed since Oct 27: the platform 6 and platform 10 work since then was geojson only. Entries run oldest first. Dates are 2026, US Eastern, taken from my working files and the git history. I sent you entries 1 and 2 on Oct 10, entries 3 to 6 on Oct 26, and entry 7 on Oct 27.

## At a glance

- Net difference from your original: +207 / -54 lines, including your own door-position edit.
- 7 new names at module level, none removed:
  - Settings: `PLATFORM_LEVEL_ONLY`, `SKIP_PLANNED`, `DEPARTING_START_AT_VCE_EXIT`, `MOUTH_BACKLOG_MAX`, `DEADLOCK_SWAP_TICKS`, `DEADLOCK_SQUEEZE_TICKS`.
  - A lookup table: `MOUTH_DIRECTIONS`.
- 2 existing settings changed value: `DEFAULT_ZOOM` 1.5 to 1.0 (mine, you asked for it) and `DOOR_POSITIONS_FT` (yours, not mine). Every other setting is unchanged. I compared them value by value: all 83 settings in your Oct 13 upload are identical today.
- Functions changed: `load_station`, `build_scene`, `analyze_vces`, `build_routing_fields`, `Agent.__init__`, `PedestrianModel.__init__`, `_swap_partner`, `_spawn_departing` and the per-tick `step`. New: `_choose_door`, `_step_stair_boarder`.
- The new boarding behaviour is on by default and applies to every platform, not just platform 5.

| New setting | Default | Entry | 0 / False means |
|---|---|---|---|
| `PLATFORM_LEVEL_ONLY` | `True` | 1 | draw features at every level |
| `SKIP_PLANNED` | `True` | 1 | draw features marked planned |
| `DEPARTING_START_AT_VCE_EXIT` | `True` | 4 | old rule: boarders appear on the platform beyond the mouth |
| `DEADLOCK_SWAP_TICKS` | `450` | 5 | no deadlock swap |
| `DEADLOCK_SQUEEZE_TICKS` | `30` | 6 | no deadlock squeeze |
| `MOUTH_BACKLOG_MAX` | `2` | 7 | no throttle |

---

## 1. Oct 10: concourse-level and planned features are ignored

- `load_station` now skips every feature whose `"level"` is not `"platform"` (a feature with no `level` counts as platform) when `PLATFORM_LEVEL_ONLY` is on, and every feature with `"status": "planned"` when `SKIP_PLANNED` is on.
- At start-up it prints how many it skipped: `Station geometry: <path> - N of M features skipped (not platform level, or planned)`. For that it now keeps the path that `ensure_geojson` returns, so the message shows the real file.
- New paragraph in the module docstring describing both properties.
- Why: so the concourse and planned edits in the geojson take effect.

## 2. Oct 10: default zoom

`DEFAULT_ZOOM` 1.5 to 1.0, as you asked: the whole platform length is visible at start-up.

## Oct 13: your edit, not mine

`DOOR_POSITIONS_FT` (10.0, 75.0) to (3.0, 18.0, 67.0, 82.0). Your Oct 13 upload differed from the file I had sent on Oct 10 in this one line and nothing else. All my later work is built on your upload, and I have not touched that line. `DOORS_PER_CAR` follows from it (4 doors per car).

## 3. Oct 13 to 24: a stair or escalator can mark its mouth

- A stair or escalator polygon in the geojson may carry `"mouth": "west" | "east" | "north" | "south"`: the end where it meets the open platform. `build_scene` copies the property into each stair's record, and `analyze_vces` then considers only the end that faces that way (new lookup table `MOUTH_DIRECTIONS`).
- If the marked end cannot be reached from the platform, it prints a warning and falls back to the other end. Without the property nothing changes: the end is still worked out from the surrounding walls, and blocked mouths are still opened as before (`OPEN_BLOCKED_VCE_MOUTHS`).
- Why: platform 5's T-shaped stair is two flights, each entered from its outer end. The geojson now splits it (geojson entries 4 and 7), and the simulator has to know which end of each flight is the platform end.
- In use today: P5-S4 west and east, P6-S4 west and east, and escalator P6-S5 (platform 6, VCE 3).
- The `analyze_vces` docstring now documents the hint and what its entry, exit and source pixels mean.

## 4. Oct 13 to 24: boarding riders start where alighting riders vanish and walk up (`DEPARTING_START_AT_VCE_EXIT = True`)

- Before: a boarding rider appeared on the platform just beyond a stair mouth, picked a door at once and walked to it.
- Now: they appear on the exit line, the far end of the stair or escalator and the same cells where alighting riders vanish. They walk up it to the mouth, step off onto the platform just beyond it (a free cell with at most `DEPARTING_MAX_CROWD` neighbours), and only then pick a door that is no longer letting people off. Until there is room and a door, they wait at the mouth.
- Every stair and escalator now has a lane each way. A third occupancy layer, `'vce_up'`, holds boarding riders, so riders going up and riders going down never block each other.
- Under the hood:
  - Routing also produces `internal_up` for each stair (distance to the cells at the mouth).
  - `Agent` gets a `train` attribute.
  - `_choose_door` is split out of `_spawn_departing`, and `_spawn_departing` is rewritten.
  - New `_step_stair_boarder` moves a boarder along the stair; the per-tick `step` calls it for boarders still on a stair.
  - The comment on `DEPART_RATE` now says riders appear on the stairs.
- Visible side effect: the "In VCE" count on each stair card, and the red `CONGESTED_THRESHOLD` of 15, now include boarders on the stair. "Exited" still counts alighting riders only.
- Effect on timing: boarders now have to walk the stair, so platform 5 takes longer to clear: about 430 s with the old rule, 460 to 555 s with the new one depending on the seed (487 s on seed 1). Stepping off right at the mouth was worse, about 80 s slower than the old rule, so they step off onto the band just beyond it, where boarders used to appear. I measured platforms 5 and 3 most closely.
- Set `DEPARTING_START_AT_VCE_EXIT = False` for the old behaviour.

## 5. Oct 24: deadlock swap (`DEADLOCK_SWAP_TICKS = 450`)

- A rider who has made no progress for 450 moves (about 50 s) and finds no ordinary swap partner trades places with any opposing rider (alighting with boarding), even with several riders in the way and even across a keep-clear zone. `_swap_partner` gained a `desperate` mode for this. The ordinary swap rule is unchanged, and the new mode is only reached after 450 stalled moves.
- Why: with the new boarding rule, platform 5 seed 3 deadlocked for good (12 riders stuck) in an 11 px wide channel at the east end of train 2: alighters from a door still in use heading east against boarders heading west who may not enter the door's keep-clear zone. With the swap, platform 5 finished on every seed I tried.

## 6. Oct 26: deadlock squeeze (`DEADLOCK_SQUEEZE_TICKS = 30`)

- A boarding rider stuck for `DEADLOCK_SWAP_TICKS` also accepts 1 px less personal space, and 1 px less again for every 30 further stalled moves, down to a floor of 1 px. It only acts while `DEADLOCK_SWAP_TICKS` is on.
- Why: I added it for a jam on platform 3, where the mouth of VCE 8 (P3-S9) opens into a walled pocket whose only way out is a gap about 1 ft (2 px) wide. It turned out not to be what fixed that jam (entry 7 did), so it stays in as a last resort.

## 7. Oct 27: mouth backlog throttle (`MOUTH_BACKLOG_MAX = 2`)

- A stair or escalator starts no new boarding rider while 2 are already waiting at its mouth for room to step off.
- Why: on platform 3 the pocket in front of VCE 8's mouth filled with boarders and gridlocked, leaving 16 (seed 1) and 46 (seed 3) boarders stuck at the end of a run. With the throttle both seeds finish: 760 of 760 boarded, at 509 s and 520 s.

---

## Observed, not changed

- Platform 6, VCE 4 (from geojson entry 11): with VCE 3 now entered from its west end, about 80 more riders head for VCE 4 and its mouth gridlocks under the default entry rule (`STAIR_ENTRY_NEEDS_PLATFORM_ROOM = True`, `SQUEEZE_TICKS = 0`). In a 240 s run, seed 1, 1,083 riders had exited, against 1,543 before the change. Knobs I tried on platform 6: `STAIR_ENTRY_NEEDS_PLATFORM_ROOM = False` gave 1,121; `SQUEEZE_TICKS = 30` gave 861 (worse); `MOUTH_SPACING_PX = 2` gave 1,477 and fixed it (VCE 4 exits went from 8 to 386). I changed no defaults. `MOUTH_SPACING_PX = 2` is my suggestion, tested on platform 6 only.
- Platform 6, four lost doors (from geojson entry 8): the freight-elevator walls leave only 9 px of clear depth in front of four doors, and `MIN_DOOR_DEPTH_PX` is 10. Setting it to 9 would bring them back but changes door counts on other platforms, so I left it.
- Already true in your original code, not caused by my changes: in seed 1 runs of your original, 131 riders were left stuck on platform 2 and 4 on platform 4, and platform 6 had 674 riders unfinished at 1,500 s.

## Checks

- Settings: compared value by value. All 83 settings in your Oct 13 upload are unchanged, 5 names added since, none removed.
- Regression: with the four new behaviours switched off (`DEPARTING_START_AT_VCE_EXIT = False`, `MOUTH_BACKLOG_MAX = 0`, `DEADLOCK_SWAP_TICKS = 0`, `DEADLOCK_SQUEEZE_TICKS = 0`), today's file prints exactly the same headless output as your Oct 13 upload. I ran platform 3 (seed 1, 150 s), platform 5 (seed 2, 240 s) and platform 6 (seed 1, 240 s) on the geojson from before the T split.
- Oct 27: all 11 platforms built and ran for 60 s without errors. Platforms 1 to 4 and 6 to 11 had the same geometry as with your file, and only platform 5 differed (7 to 8 stairs).
