# Changelog: `shapes_pcip_phase_1.geojson`

Everything I changed in the geojson, measured against the file as I first saw it: your commit `ff3ee37` ("Clean out old stuff.", Oct 6), 3,005 features. The file now has 3,018 features and matches my local commit `f278ab7` (not pushed, as you asked). Entries run oldest first. Dates are 2026, US Eastern, taken from my working files and the git history.

## At a glance

- 91 existing features edited, 13 features added, none deleted.
  - 39 changed from `"level": "platform"` to `"level": "concourse"`.
  - 49 given `"status": "planned"`.
  - 3 other edits: the two T-stair polygons (65 and 74) cut down to their west flight, and escalator 75 given `"mouth": "west"`.
- Platform 5: 37 edited + 7 added. Platform 6: 44 edited + 6 added. Platform 10: 10 edited. Nothing else in the file was touched.
- No existing feature was moved or reordered, and no coordinate of an existing feature changed except the two T-stair polygons. New features are appended at the end (indices 3005 to 3017), so every old index still points at the same feature.

## How the simulator treats these properties

- `"level": "concourse"`: the simulator ignores the feature (`PLATFORM_LEVEL_ONLY`).
- `"status": "planned"`: ignored too (`SKIP_PLANNED`).
- `"mouth": "west" | "east" | "north" | "south"` on a stair or escalator: the end that meets the open platform (see the simulator changelog).
- "VCE n" below is the simulator's west-to-east numbering of the stairs and escalators on that platform at the time you asked. It shifts when stairs are split or marked planned, so I give the `vce_name` where there is one.

---

## 1. Oct 8: Platform 5, first corrections (8 features)

- `status: planned` (on the plans, not built): 70 (P5-S9, then VCE 6) and 71 (unnamed stair, then VCE 8).
- `level: concourse`:
  - 109 (P5-S10, then VCE 7), a concourse stair rather than a platform stair.
  - 644, the elevator left of VCE 8.
  - 2986 and 2987, enclosures left of VCE 8.
  - 2572, a wall left of VCE 8 on the concourse outline.
  - 2581, a wall above VCE 10 on the mezzanine boundary.

## 2. Oct 8: Platform 5, walls around the planned stairs and around elevator 644 (26 features)

- `status: planned`, 16 walls:
  - around VCE 6 (P5-S9): 1718, 1719, 1720, 1722, 1730, 1732, 1811, 1819, 1820, 1821, 1832, and 2557, which closes the east end of its block.
  - around VCE 8: 1952, 1953, 1954, 1955.
- `level: concourse`, 10 walls around elevator 644: 1939, 1940, 1943 (the shaft) and 1941, 1942, 1944, 1945, 1948, 1949, 1950 (the room attached to the shaft's east side).

## 3. Oct 10: Platform 5, leftovers and a gap (2 edited, 2 added)

- `level: concourse`: 1843 and 1844, two diagonal walls on the west side of P5-S10 that were left behind when it moved up (entry 1).
- Added 3005 and 3006: two short platform-level walls (`#525252`) that close the 1.7 ft and 1.5 ft gaps between the C-shaped enclosure wall 2498 and the car of the westernmost platform 5 elevator (647). 3005 is the north end (x = -70.5, y 2.7 to 4.4); 3006 is the south end (x = -69.9, y -5.8 to -4.3). Their `source` field says they are not in the PCIP drawing.

## 4. Oct 12: Platform 5, T-shaped stair P5-S4 split into two flights (1 edited, 2 added)

- 65 stays where it is and becomes `P5-S4 west` with `"mouth": "west"`. Its polygon is cut down to the west flight (x -19.2 to -8.8).
- Added 3007, `P5-S4 east`, `"mouth": "east"` (x 2.7 to 16.1).
- Added 3008, `P5-S4 stem`, `level: concourse`: the overhead trunk running north across the platform. The simulator ignores it, so people can walk under it.
- The three pieces tile the original T exactly (same total area). Their `source` fields say they were split from it.
- Why: the real stair is two flights off an overhead stem. The simulator needs one stair per flight and a walkable floor under the stem. Platform 5 goes from 7 to 8 stairs and escalators.

## 5. Oct 28: Platform 10, walls and pens to concourse level (10 features)

All `level: concourse`:

- 2504, the backwards-C wall west of VCE 1.
- 2485 and 2486 (first pen) and 2487 (second pen): enclosure polygons between VCE 1 and VCE 2/3.
- 2509 and 2510, the C-shaped wall east of VCE 2/3.
- 2535 (vertical wall at x = 350 with a hook) and 2534 (the long hairpin with the zigzag), the L- and S-shaped walls west of VCE 4/5.
- Same evening: 2590, the diagonal wall between exits 8 and 9, and 2577, the full-width wall just east of exit 7.

Left alone and flagged: 1411, a thin L-shaped enclosure (x 364.6 to 370.3, y 225.2 to 229.3) that is the other candidate for "the L" but is not on the concourse outline; 2885, a tiny enclosure inside the backwards C; and the columns inside the pens.

Effect: platform 10's stairs, mouths and exits are unchanged. The evening batch made two north-edge doors usable (train 1, car 1, x about 857 and 872), 48 to 50 doors.

## 6. Oct 28: Platform 5, three missing freight-elevator walls (3 added)

Between VCE 2 and VCE 3 on platform 5, four columns mark the corners of a rectangle around a freight elevator, and only the east wall was drawn. You asked me to find the other three walls and move them down. They are not in the file at any level, so there was nothing to move. I added them instead, at platform level (`#787878`):

- 3009, west wall: x = 166.5, y -3.4 to 3.9.
- 3010, north wall: y = 4.3, x 167.0 to 185.3.
- 3011, south wall: y = -3.8, x 167.0 to 185.3.

Their `source` fields say "added Oct 2026, not digitized in PCIP Phase 1". Effect: 255 px of platform 5 floor in the simulator is newly blocked.

## 7. Oct 29: Platform 6, first batch (35 features: 33 edited, 2 added)

- `level: concourse`:
  - The series of walls between exits 4 and 7: 2529 (x 349 to 478), 2544 (x 478 to 570), 2545 and 2546 (all meet at x 478, y 50.6).
  - The two extra walls by exits 8 and 9: 2583 (x about 713) and 2589 (x 756 to 760). Both trace the edge of the concourse polygon.
- `status: planned`:
  - Exit 7 itself, 80 (unnamed stair, x 614 to 626), and the elevator beside it, 641 (x 592 to 600).
  - The 24 walls around them: 1957, 1958, 1961 to 1971, 1975 to 1984, 1988.
- T-shaped stair at exit 1, split the way platform 5's was (entry 4): 74 becomes `P6-S4 west` (`"mouth": "west"`), 3012 is added as `P6-S4 east` (`"mouth": "east"`), and 3013 is added as `P6-S4 stem` (`level: concourse`).
- Effect: platform 6 now builds 9 stairs and escalators (P6-S4 west and east, then P6-S5 to P6-S11). Exits are renumbered: 1 is the west flight, 2 the east flight, 3 is P6-S5, and so on. The chain of walls had been fencing off 15 doors: platform 6 goes from 55 to 70 usable doors and one more car fits (9+10 to 10+10).
- Left alone at the time: four tiny stubs at x 349 to 361 (2527, 2528, 2540, 2541). Entry 10 moves them.

## 8. Oct 30: Platform 6, freight-elevator walls (4 added)

You asked for the freight elevator walls just west of VCE 2. I took that as platform 6 (VCE 2 in the numbering before the T split, which is P6-S5). The rectangle at x 166 to 188 has four corner objects and no walls at any level, so I added all four at platform level (`#787878`):

- 3014, west wall: x = 166.5, y 41.2 to 48.6.
- 3015, east wall: x = 186.4, y 41.1 to 48.6.
- 3016, north wall: y = 48.9, x 167.0 to 185.3.
- 3017, south wall: y = 40.9, x 167.0 to 185.3.

Effect: four doors (x about 168.9 and 183.8, on both trains) drop out because only 9 px of clear platform is left in front of them (`MIN_DOOR_DEPTH_PX` is 10). Platform 6 goes from 70 to 66 doors.

Not done: the same rectangle at x about 166 to 188 on platforms 3 and 4 also has corner objects only, with no walls. I flagged it and have not touched it.

## 9. Oct 30: Platform 6, the stair that had become exit 7 set to planned (5 features)

- `status: planned`: 79 (P6-S9, x 452 to 469) and its walls 1705, 1706, 1707, 1708.
- Platform 6 now has 8 stairs and escalators: 1 P6-S4 west, 2 P6-S4 east, 3 P6-S5, 4 P6-S6, 5 P6-S7, 6 P6-S8, 7 P6-S10, 8 P6-S11.
- Column 399 (x 459.2 to 461.3, y 43.4 to 45.4) overlaps where the stair was and is left as it is. 14 px of floor that used to be carved out for the stair are now blocked, which is harmless.

## 10. Oct 30: Platform 6, walls between the east elevator and VCE 5 (4 features)

- `level: concourse`: 2527, 2528 and 2540 (walls) and 2541 (a thin enclosure sliver), all `#545252`, at x about 349 to 361, between the east elevator (643, x 317 to 325) and VCE 5 (P6-S7, x 368 to 385). They belong to the same mezzanine-edge line set as the walls moved in entry 7.
- Effect: 113 px of wall mask freed, none blocked. Stairs and doors are unchanged on all 11 platforms.

## 11. Oct 31: Platform 6, the line above stairs 1 and 2, and VCE 3's west door (2 features)

- `level: concourse`: 2507, the line just above stairs 1 and 2 (y about 49.6, `#545252`).
- 75 (escalator P6-S5, VCE 3) gets `"mouth": "west"`. Its west end is the spring-loaded zigzag door and its east end is a real wall, so riders now go in at the west end and ascend west to east. Before, they were being routed through the wall. Platform 6 goes from 66 to 67 doors (a new door at x = -0.8 on train 1).
- Left alone, as you said: the two lines parallel to the stairwell wall (the signs).
- Side effect, not fixed in the geojson: with VCE 3 entered from the west, about 80 more riders head for VCE 4 and its mouth gridlocks under the default settings. `MOUTH_SPACING_PX = 2` in simulator.py cleared it in my tests (see the simulator changelog).

---

## Still open (flagged, not changed)

- Platform 6: 2496 (x -80 to -70, y 40 to 50, beside the west elevator) and 2516 and 2517 (x 290 to 293, y 39 to 46, between VCE 4 and the east elevator) are in the same `#545252` mezzanine-edge layer as the walls moved in entries 7, 10 and 11, and are still at platform level.
- Platforms 3 and 4: the freight-elevator rectangle at x about 166 to 188 has corner objects only, no walls.
- Platform 10: 1411 (thin L-shaped enclosure) and 2885 are still at platform level.
- Platform 6: column 399 overlaps the former P6-S9 footprint.

## How each edit was made and checked

Each round was a guarded one-line text edit (one feature per line, so line number = index + 2), with a check that the line was the feature I expected. After each round I confirmed that only the intended lines differed from the previous file, built all 11 platforms in the simulator and ran them for 60 s, and did a longer headless run and a render of the platform concerned. Final check, today: the 91 edited and 13 added features in this changelog are exactly the differences between your original file and the current one, and each one was checked against the data (which property changed, and that the geometry is untouched except for 65 and 74).

---

## Appendix: every touched feature

Line = line number in the file (index + 2). Entry = the numbered entry above.

| Feature | Line | Platform | Type | Name | Colour | Change | Entry |
|---|---|---|---|---|---|---|---|
| 65 | 67 | 5 | stair | P5-S4 west |  | now the west flight (polygon cut down), mouth west | 4 |
| 70 | 72 | 5 | stair | P5-S9 |  | status → planned | 1 |
| 71 | 73 | 5 | stair |  |  | status → planned | 1 |
| 74 | 76 | 6 | stair | P6-S4 west |  | now the west flight (polygon cut down), mouth west | 7 |
| 75 | 77 | 6 | escalator | P6-S5 |  | added "mouth": "west" | 11 |
| 79 | 81 | 6 | stair | P6-S9 |  | status → planned | 9 |
| 80 | 82 | 6 | stair |  |  | status → planned | 7 |
| 109 | 111 | 5 | stair | P5-S10 |  | level → concourse | 1 |
| 641 | 643 | 6 | elevator |  |  | status → planned | 7 |
| 644 | 646 | 5 | elevator |  |  | level → concourse | 1 |
| 1705 | 1707 | 6 | wall |  | #525252 | status → planned | 9 |
| 1706 | 1708 | 6 | wall |  | #525252 | status → planned | 9 |
| 1707 | 1709 | 6 | wall |  | #525252 | status → planned | 9 |
| 1708 | 1710 | 6 | wall |  | #525252 | status → planned | 9 |
| 1718 | 1720 | 5 | wall |  | #525252 | status → planned | 2 |
| 1719 | 1721 | 5 | wall |  | #525252 | status → planned | 2 |
| 1720 | 1722 | 5 | wall |  | #525252 | status → planned | 2 |
| 1722 | 1724 | 5 | wall |  | #525252 | status → planned | 2 |
| 1730 | 1732 | 5 | wall |  | #525252 | status → planned | 2 |
| 1732 | 1734 | 5 | wall |  | #525252 | status → planned | 2 |
| 1811 | 1813 | 5 | wall |  | #525252 | status → planned | 2 |
| 1819 | 1821 | 5 | wall |  | #525252 | status → planned | 2 |
| 1820 | 1822 | 5 | wall |  | #525252 | status → planned | 2 |
| 1821 | 1823 | 5 | wall |  | #525252 | status → planned | 2 |
| 1832 | 1834 | 5 | wall |  | #525252 | status → planned | 2 |
| 1843 | 1845 | 5 | wall |  | #525252 | level → concourse | 3 |
| 1844 | 1846 | 5 | wall |  | #525252 | level → concourse | 3 |
| 1939 | 1941 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1940 | 1942 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1941 | 1943 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1942 | 1944 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1943 | 1945 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1944 | 1946 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1945 | 1947 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1948 | 1950 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1949 | 1951 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1950 | 1952 | 5 | wall |  | #525252 | level → concourse | 2 |
| 1952 | 1954 | 5 | wall |  | #525252 | status → planned | 2 |
| 1953 | 1955 | 5 | wall |  | #525252 | status → planned | 2 |
| 1954 | 1956 | 5 | wall |  | #525252 | status → planned | 2 |
| 1955 | 1957 | 5 | wall |  | #525252 | status → planned | 2 |
| 1957 | 1959 | 6 | wall |  | #525252 | status → planned | 7 |
| 1958 | 1960 | 6 | wall |  | #525252 | status → planned | 7 |
| 1961 | 1963 | 6 | wall |  | #525252 | status → planned | 7 |
| 1962 | 1964 | 6 | wall |  | #525252 | status → planned | 7 |
| 1963 | 1965 | 6 | wall |  | #525252 | status → planned | 7 |
| 1964 | 1966 | 6 | wall |  | #525252 | status → planned | 7 |
| 1965 | 1967 | 6 | wall |  | #525252 | status → planned | 7 |
| 1966 | 1968 | 6 | wall |  | #525252 | status → planned | 7 |
| 1967 | 1969 | 6 | wall |  | #525252 | status → planned | 7 |
| 1968 | 1970 | 6 | wall |  | #525252 | status → planned | 7 |
| 1969 | 1971 | 6 | wall |  | #525252 | status → planned | 7 |
| 1970 | 1972 | 6 | wall |  | #525252 | status → planned | 7 |
| 1971 | 1973 | 6 | wall |  | #525252 | status → planned | 7 |
| 1975 | 1977 | 6 | wall |  | #525252 | status → planned | 7 |
| 1976 | 1978 | 6 | wall |  | #525252 | status → planned | 7 |
| 1977 | 1979 | 6 | wall |  | #525252 | status → planned | 7 |
| 1978 | 1980 | 6 | wall |  | #525252 | status → planned | 7 |
| 1979 | 1981 | 6 | wall |  | #525252 | status → planned | 7 |
| 1980 | 1982 | 6 | wall |  | #525252 | status → planned | 7 |
| 1981 | 1983 | 6 | wall |  | #525252 | status → planned | 7 |
| 1982 | 1984 | 6 | wall |  | #525252 | status → planned | 7 |
| 1983 | 1985 | 6 | wall |  | #525252 | status → planned | 7 |
| 1984 | 1986 | 6 | wall |  | #525252 | status → planned | 7 |
| 1988 | 1990 | 6 | wall |  | #525252 | status → planned | 7 |
| 2485 | 2487 | 10 | enclosure |  | #525252 | level → concourse | 5 |
| 2486 | 2488 | 10 | enclosure |  | #525252 | level → concourse | 5 |
| 2487 | 2489 | 10 | enclosure |  | #525252 | level → concourse | 5 |
| 2504 | 2506 | 10 | wall |  | #545252 | level → concourse | 5 |
| 2507 | 2509 | 6 | wall |  | #545252 | level → concourse | 11 |
| 2509 | 2511 | 10 | wall |  | #545252 | level → concourse | 5 |
| 2510 | 2512 | 10 | wall |  | #545252 | level → concourse | 5 |
| 2527 | 2529 | 6 | wall |  | #545252 | level → concourse | 10 |
| 2528 | 2530 | 6 | wall |  | #545252 | level → concourse | 10 |
| 2529 | 2531 | 6 | wall |  | #545252 | level → concourse | 7 |
| 2534 | 2536 | 10 | wall |  | #545252 | level → concourse | 5 |
| 2535 | 2537 | 10 | wall |  | #545252 | level → concourse | 5 |
| 2540 | 2542 | 6 | wall |  | #545252 | level → concourse | 10 |
| 2541 | 2543 | 6 | enclosure |  | #545252 | level → concourse | 10 |
| 2544 | 2546 | 6 | wall |  | #545252 | level → concourse | 7 |
| 2545 | 2547 | 6 | wall |  | #545252 | level → concourse | 7 |
| 2546 | 2548 | 6 | wall |  | #545252 | level → concourse | 7 |
| 2557 | 2559 | 5 | wall |  | #545252 | status → planned | 2 |
| 2572 | 2574 | 5 | wall |  | #545252 | level → concourse | 1 |
| 2577 | 2579 | 10 | wall |  | #545252 | level → concourse | 5 |
| 2581 | 2583 | 5 | wall |  | #545252 | level → concourse | 1 |
| 2583 | 2585 | 6 | wall |  | #545252 | level → concourse | 7 |
| 2589 | 2591 | 6 | wall |  | #545252 | level → concourse | 7 |
| 2590 | 2592 | 10 | wall |  | #545252 | level → concourse | 5 |
| 2986 | 2988 | 5 | enclosure |  | #787878 | level → concourse | 1 |
| 2987 | 2989 | 5 | enclosure |  | #787878 | level → concourse | 1 |
| 3005 | 3007 | 5 | wall |  | #525252 | NEW (level platform) | 3 |
| 3006 | 3008 | 5 | wall |  | #525252 | NEW (level platform) | 3 |
| 3007 | 3009 | 5 | stair | P5-S4 east |  | NEW (level platform) | 4 |
| 3008 | 3010 | 5 | stair | P5-S4 stem |  | NEW (level concourse) | 4 |
| 3009 | 3011 | 5 | wall |  | #787878 | NEW (level platform) | 6 |
| 3010 | 3012 | 5 | wall |  | #787878 | NEW (level platform) | 6 |
| 3011 | 3013 | 5 | wall |  | #787878 | NEW (level platform) | 6 |
| 3012 | 3014 | 6 | stair | P6-S4 east |  | NEW (level platform) | 7 |
| 3013 | 3015 | 6 | stair | P6-S4 stem |  | NEW (level concourse) | 7 |
| 3014 | 3016 | 6 | wall |  | #787878 | NEW (level platform) | 8 |
| 3015 | 3017 | 6 | wall |  | #787878 | NEW (level platform) | 8 |
| 3016 | 3018 | 6 | wall |  | #787878 | NEW (level platform) | 8 |
| 3017 | 3019 | 6 | wall |  | #787878 | NEW (level platform) | 8 |
