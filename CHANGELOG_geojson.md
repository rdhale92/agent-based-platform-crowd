# Changelog: `shapes_pcip_phase_1.geojson`

Everything I changed in the geojson, measured against the file as I first saw it: your commit `ff3ee37` ("Clean out old stuff.", Oct 6), 3,005 features. After entry 11 the file had 3,018 features. Entries run oldest first. Dates are 2026, US Eastern, taken from my working files and the git history.

Entries 1 to 11 (Oct 8 to 31) were logged as they were made. Entries 12 to 25 (Nov 15 to 16) were reconstructed from the git history on Nov 18, and entry 26 is Nov 18. The file now has 2,936 features.

## At a glance

Entries 1 to 11, against `ff3ee37`:

- 91 existing features edited, 13 features added, none deleted.
  - 39 changed from `"level": "platform"` to `"level": "concourse"`.
  - 49 given `"status": "planned"`.
  - 3 other edits: the two T-stair polygons (65 and 74) cut down to their west flight, and escalator 75 given `"mouth": "west"`.
- Platform 5: 37 edited + 7 added. Platform 6: 44 edited + 6 added. Platform 10: 10 edited. Nothing else in the file was touched.
- No existing feature was moved or reordered, and no coordinate of an existing feature changed except the two T-stair polygons. New features are appended at the end (indices 3005 to 3017), so every old index still points at the same feature.

Entries 12 to 26, Nov 15 to 18:

- 3,018 to 2,936 features: 138 feature edits, 132 added, 214 deleted (3,018 + 132 - 214 = 2,936), so the old indices from entries 1 to 11 no longer point at the same features.
- The big changes: the Moynihan Train Hall end of platforms 5 to 8 (entries 12 to 14), the file stored in longitude/latitude (15), the stray linework and gone stairs on platforms 7 and 8 (16, 18, 21, 22), the last T-stairs split and the freight-elevator landings (17), and Penn platforms 1 and 2 split into separate polygons (26).
- Feature numbers in those entries are the indices right after each change, so they are listed in each entry; the appendix table below covers entries 1 to 11 and 26.

## How the simulator treats these properties

- `"level": "concourse"`: the simulator ignores the feature (`PLATFORM_LEVEL_ONLY`).
- `"status": "planned"`: ignored too (`SKIP_PLANNED`).
- `"level": "annotation"` (from entry 12): CAD symbols kept for reference; ignored like concourse.
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

## Nov 15-16 commits (entries 12 to 25)

Reconstructed on Nov 18 from the git history: each commit's file was compared feature by feature with the one before it (coordinates in feet, rounded to 0.1 ft), and the reasons come from the commit messages. Feature numbers are the indices in the file right after that commit, so they shift from entry to entry as features are deleted; "a -> b" means the feature was index a before the commit and b after. Line = index + 2, as before.

## 12. Nov 15, `68b9234`: Moynihan Train Hall, platform 3, doorway trims (86 edited, 83 added)

- Platforms 5, 6 and 7 (4, 5, 6) extended west from x = -401.4 to the Train Hall: the west fingers traced from the Moynihan Station General Project Plan (June 2010, PDF page 22), to x = -645.7 on P5 and P7 and -622.9 on P6.
- Train Hall equipment added (3020 to 3048): the egress-corridor outline (3020), two sets of enclosures at x -415 to -379 and -340 to -325 on P4 to P8 (3021 to 3030), six passenger elevators at x -260 to -251 on P3 to P8 (3031 to 3036), and twelve escalators P{3-8}-TH-N/S at x -233 to -200 (3037 to 3048). Entry 13 replaced the elevators and escalators.
- 52 columns added (3049 to 3100), from the same plan: the columns on the west fingers of P5, P6 and P7, and the round columns by the Train Hall escalators on P4, P5, P7 and P8 that the PCIP plan does not show. 3049 and 3050 are small enclosures at the tips of the P5 and P7 fingers.
- Platform 3, T-shaped stair P3-S3 split like P5/P6 (entries 4 and 7): 46 becomes `P3-S3 west` (mouth west); added 3018 `P3-S3 east` (mouth east) and 3019 `P3-S3 stem` (concourse level).
- Platform 3, planned (not built): stairs 51 (P3-S8), 52, 53 (P3-S9), elevator 652, and 41 walls and one enclosure around them (1715 to 1935).
- Platform 3, other: 54 (P3-S10) redrawn to x 658.2 to 691.8 with mouth west; 55 (unnamed stair) and wall 692 to concourse level; four `#545252` mezzanine-edge walls (2500, 2553, 2556, 2568) to concourse level.
- New level `"annotation"` (ignored by the simulator, like concourse): nine CAD door symbols in P6 stair and escalator doorways (964, 965, 968, 969, 978, 979, 1080, 1081, 1083).
- Doorway trims: 20 wall lines in P5 and P6 doorways shortened so the opening is clear (966, 967, 1079, 1082, 1084, 1089 to 1091 at x about 266 on P6; 1548 to 1679 at x about 422 on P5 and P6). Their `source` cites entries 6 and 7 of a `CHANGELOG_geojson_2026-11.md` (Nov 12), which is not in the repository.

## 13. Nov 15, `bddc608`: Train Hall escalators redrawn (21 added, 29 deleted)

- Deleted the egress-corridor outline (3020), the six passenger elevators west of the escalators (3031 to 3036) and the twelve TH-N/S escalators (3037 to 3048).
- The ten Train Hall enclosures are unchanged; they move up one place (3021 to 3030 become 3020 to 3029).
- Added eleven escalators with their mouths at the east end (`"mouth": "east"`): P3-TH-E (3030) and P{4-8}-TH-W/E (3031 to 3040), TH-W at x -199.6 to -149.0 and TH-E at x -147.0 to -95.9.
- File: 3,093 features.

## 14. Nov 15, `08950f3`: Train Hall escalators trimmed to their treads (11 edited)

- 3030 to 3040 cut to 28 ft, the part drawn as treads at platform level on the Level A lower concourse plan; the rest of each unit rises overhead. TH-W now x -177.0 to -149.0, TH-E x -123.9 to -95.9, east mouths unchanged.
- Why: at full length there were about 2 ft between VCE 1's mouth and the back of VCE 2, so boarders could not come off VCE 1 on P4, P6 and P8. Now about 25 ft of platform lies in front of VCE 1.

## 15. Nov 16, `d9932d1`: file stored in longitude/latitude (no feature changed)

- Every coordinate converted from the plans' feet frame to WGS 84 longitude/latitude, registered as the Effective Transit Alliance's platform-crowd-model registers the same frame to OpenStreetMap (rotation and offset, no scale; within 0.1 ft of their file pair).
- Written to 10 decimals, so every feature converts back to its previous feet coordinates; the comparison found no feature changed. station.py converts back on load (`FT_TO_LONLAT`).

## 16. Nov 16, `e1f9d53`: platforms 4 and 7 (1 edited, 3 added, 100 deleted)

- Platform 4: the unnamed stair 60 (x 407.4) and P4-S7 (61) are one escalator: replaced by 60, escalator `P4-S7`, x 407.4 to 424.9, mouth east. P4-S8 (61) and P4-S9 (62) are planned. The L-shaped wall 2499 -> 2409, which traces the West End Concourse outline, to concourse level.
- Platform 7: deleted the unnamed diagonal stair (110) and P7-S10 (89), which are not VCEs, and 94 wall and enclosure features of stray linework: around P7-S8/P7-S9 (x 349 to 436), from the former VCE 9 to P7-S12 (x 515 to 692) and the wall ring at x 484 to 492 (enclosure 2492). P7 is one connected platform again and every VCE is reachable.

## 17. Nov 16, `8867783`: T-stairs split, enclosure doors opened, freight landings (9 edited, 16 added, 17 deleted)

- T-shaped stairs P4-S3 (56), P7-S5 (83) and P8-S4 (91) split like P3/P5/P6: each becomes the west flight (mouth west); added the east flights (2981, 2983, 2985, mouth east) and the overhead stems at concourse level (2982, 2984, 2986).
- P7-S6's door leaves (948 to 953), which swung out and pinched its entrance, replaced by two leaves flat against the enclosure sides (948, 949). P4-S4's half-swung leaves (967 -> 963 and 972 -> 967 kept and straightened; 969, 974, 977, 978 deleted); P4-S4 (57) gets mouth west, facing its entrance.
- Platform 7: walls 2407 -> 2399, 2435 -> 2427 and 2451 -> 2443 (the C-shaped wall at the West End Concourse alcove, x -79.9 to -70.5, and two walls just west of P7-S8) to concourse level.
- Freight-elevator landings (Level A plan, Feb 2010): a 19.9 x 8.1 ft enclosure between the corner columns at x 166.5 to 186.4 on platforms 2 to 9 (2987 to 2994). They replace the Oct wall outlines on P5 (2912 to 2914) and P6 (2917 to 2920), which are deleted. The non-public hallway is not drawn.

## 18. Nov 16, `07a10e4`: P7/P8 VCEs (10 edited, 1 added, 18 deleted)

- P7-S4 (82) and P8-S3 (90) no longer exist: deleted, with the 16 wall and enclosure features that drew them (666 to 721).
- P7-S9 (87 -> 86) gets mouth east.
- Added 2977, P8-S8: a stair drawn with treads at x 405.3 to 422.3 that never had a polygon. It climbs westward, so its mouth is east.
- To concourse level: P8's C-shaped mezzanine-edge wall by the west end (2397 -> 2379), and the `#545252` walls around P8-S7, P8-S9 and P8-S11 (2438 to 2474 -> 2420 to 2456).

## 19. Nov 16, `940af7a`: P8 mezzanine-edge walls (5 edited)

- To concourse level: the `#545252` walls between P8-S6 and P8-S7 (2398, 2399, x 291 to 292) and at the east end of platform 8 (2462 to 2464, x 734 to 758).

## 20. Nov 16, `f0f3ea9`: P8-S5 mouth (1 edited)

- 90 (P8-S5) gets mouth west, the door end; its east end stays a closed wall.

## 21. Nov 16, `acb06d2`: P5 VCE 6-7, P7 VCE 5, 6 and 9 (6 edited, 1 added, 8 deleted)

- P5-S7 (67) widened to cover the whole flight (x 372.8 to 389.9).
- Platform 5: mezzanine-edge walls by P5-S6/S7 (2404, 2414, 2415 -> 2397, 2407, 2408) to concourse level. The door at P5-S6's east end and the door between P5-S7 and the elevator closed: leaves 1381, 1382, 1387 deleted, a straight wall added (1376), and wall 1144 -> 1139 extended to y 0.6.
- Platform 7: stray flaps inside the P7-S6 enclosure (983, 984, 987) and the angled P7-S7 door leaves (1002, 1005) deleted; P7-S11 (87) ends snapped to the CAD outline.

## 22. Nov 16, `480f43e`: P7 VCE 5, 6 and 9 linework (5 edited, 1 added, 25 deleted)

- Deleted a stray wall under the freight-elevator landing (2651), the flaps past VCE 6's east end and the door leaves further east (1079 to 1105 and 1206 to 1209, 24 features); an end wall closes that enclosure (1092, x 292.5).
- VCE 5's mouth leaves straightened (956, 960); P7-S7 (84) keeps its mouth at the west end (`"mouth": "west"`).
- One more mezzanine-edge wall to concourse level (2395 -> 2372).
- P7-S11 (87) widened to the enclosure's inner walls.

## 23. Nov 16, `1fa08bb`: P7-S11 reshaped (1 edited)

- 87 (P7-S11) redrawn to the drawn escalator outline (x 631.8 to 653.9), mouth west.

## 24. Nov 16, `49859e1`: P7-S6 widened, P7-S8 mouth (2 edited)

- 83 (P7-S6) widened to its enclosure walls (x 219.5 to 232.7).
- 85 (P7-S8) gets mouth east.

## 25. Nov 16, `831c294`: P6-S10 and P6-S11 mouths opened (5 added, 17 deleted)

- P6-S10's enclosure at x 672 to 691: ten door-leaf and double-line wall features (2073 to 2082) replaced by four straight single walls (2073 to 2076).
- P6-S11's enclosure at x 769 to 794: seven features (2227 to 2232, 2234) replaced by one wall (2221).
- Both mouths are now open to the platform. File: 2,935 features.

## 26. Nov 18: Platforms 1 and 2, U-shaped polygon split in two (1 edited, 1 added)

- The PCIP drawing has platforms 1 and 2 as one U-shaped polygon (`"platform": "1/2"`), joined at the east end by a short non-public link. That link (the bridge of the U) is cut out: x 884.4 to 911.1 ft, between y -148.5 and -173.8.
- 9 stays where it is and becomes platform 2, the north strip (`"platform": "2"`). Its west end and both long edges are the original vertices; the east end is closed with a straight edge at x = 911.1 from y -128.1 to -148.5.
- Added 2935: platform 1, the south strip (`"platform": "1"`). Same treatment, closed at x = 911.1 from y -173.8 to -196.2.
- Both `source` fields say they were split from the U polygon and where the cut is.
- Why: the simulator had to cut the U into two strips at load time (`_split_u_platform` in station.py), which only worked for this one polygon. With two ordinary platform polygons that code is gone, and every platform loads the same way.
- Check: 60 s headless runs, same seed, against the code before the split. Platform 2 is identical (453 riders left the platform). Platform 1 is within 2 riders (436 vs 434), because its floor is now the polygon itself rather than a horizontal band of the U. Both keep 9+8 cars and 68 doors.

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

Line = line number in the file (index + 2). Entry = the numbered entry above. Entries 12 to 25 list their features in the entries themselves; rows for entries 1 to 11 use the indices of the file after entry 11.

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
| 9 | 11 | 2 | platform |  |  | U polygon "1/2" cut down to the north strip, now platform 2 | 26 |
| 2935 | 2937 | 1 | platform |  |  | NEW (level platform): the south strip of the U | 26 |
