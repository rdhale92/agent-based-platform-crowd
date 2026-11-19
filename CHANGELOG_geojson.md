# Changelog: `shapes_pcip_phase_1.geojson`

Everything I changed in the geojson, measured against the file as I first saw it: your commit `ff3ee37` ("Clean out old stuff.", Oct 6), 3,005 features. After entry 11 the file had 3,018 features. Entries run oldest first. Dates are 2026, US Eastern, taken from my working files and the git history.

Entries 1 to 11 (Oct 8 to 31) were logged as they were made. Entries 12 to 25 (Nov 15 to 16) were reconstructed from the git history on Nov 18, and entries 26 to 42 are Nov 18. The file now has 2,635 features.

## At a glance

Entries 1 to 11, against `ff3ee37`:

- 91 existing features edited, 13 features added, none deleted.
  - 39 changed from `"level": "platform"` to `"level": "concourse"`.
  - 49 given `"status": "planned"`.
  - 3 other edits: the two T-stair polygons (65 and 74) cut down to their west flight, and escalator 75 given `"mouth": "west"`.
- Platform 5: 37 edited + 7 added. Platform 6: 44 edited + 6 added. Platform 10: 10 edited. Nothing else in the file was touched.
- No existing feature was moved or reordered, and no coordinate of an existing feature changed except the two T-stair polygons. New features are appended at the end (indices 3005 to 3017), so every old index still points at the same feature.

Entries 12 to 42, Nov 15 to 18:

- 3,018 to 2,635 features: 310 feature edits, 141 added, 524 deleted (3,018 + 141 - 524 = 2,635), so the old indices from entries 1 to 11 no longer point at the same features.
- The big changes: the Moynihan Train Hall end of platforms 5 to 8 (entries 12 to 14), the file stored in longitude/latitude (15), the stray linework and gone stairs on platforms 7 and 8 (16, 18, 21, 22), the last T-stairs split and the freight-elevator landings (17), Penn platforms 1 and 2 split into separate polygons (26), and VCEs 4, 5 and 7 removed from platform 1 with an escalator added beside VCE 6 (28), the stairs at the planned concourse on platforms 1 and 2 (29), more planned features and mezzanine edges on platforms 1 to 4 (30, 31), P5-S12 narrowed (31), P4-S9 restored as built (32), every planned feature deleted (33), a missing stair and enclosure added on platform 7 (34), every VCE renamed west to east (35), P4-S9 removed and P2-S8 lengthened (36), the old P2-S8 linework removed (37), the walls by P2-S6 and P2-S7 removed (38), P4-S7's mouth widened (39), an enclosure on platform 4 moved to concourse level (40), the obstruction in front of P4-S8 removed (41), and a wall stub beside P4-S3 removed (42). VCE names in entries before 35 are the old names (kept in `old_vce_name`).
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
- Doorway trims: 20 wall lines in P5 and P6 doorways shortened so the opening is clear (966, 967, 1079, 1082, 1084, 1089 to 1091 at x about 266 on P6; 1548 to 1679 at x about 422 on P5 and P6). The trims were made on Nov 12.

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

## 27. Nov 18: source notes cleaned (31 edited, properties only)

- Shortened the `source` notes of 31 features (the doorway trims and CAD symbols of entry 12, and the platform 5 and 7 west fingers) so they only say what was done and when. No geometry changed.

## 28. Nov 18: Platform 1, VCEs 4, 5 and 7 removed, escalator beside VCE 6 added (1 added, 68 deleted)

Indices are those of the file before this entry (2,936 features); it now has 2,869.

- Deleted P1-S4 (14) and P1-S5 (15), then VCEs 4 and 5, with the boxes and walls around them between x 474 and 556: the four elevators 654, 655, 656 and 659, 52 `#525252` walls (1630 to 1835), the `#545252` mezzanine-edge walls 2388 and 2405, and wall 2635. The columns there (617, 621, 622) are kept.
- Deleted the unnamed stair 18, then VCE 7 (x 763.5 to 783.0), and the hallway walls running from it to P1-S8: 2211, 2212, 2277, 2278, 2279 and 2288.
- Added 2868, escalator `P1-S6 south` with `"mouth": "west"`: the escalator drawn with treads just south of P1-S6 (x 659.2 to 683.1, y -188.4 to -186.2), which never had a polygon.
- Check: platform 1 now has seven VCEs (P1-S1, S2, S3, S6 south, S6, S7, S8), all open, and keeps its 9+8 cars and 68 doors. A 300 s headless run cleared 1,977 of 2,040 alighting riders off the trains.

## 29. Nov 18: Platforms 1 and 2, stairs at the planned concourse (15 edited, 2 added, 1 deleted)

Placed from screenshots you marked up. They were lined up using the west wall of the planned concourse (x about 497), PCIP columns 596 and 600, and the platform edges, then moved east to where you said they belong. Both stairs open to the east (`"mouth": "east"`), and their edges run parallel or perpendicular to the tracks. The dark planned stairs in the same drawing were not added. Indices are those of the file after this entry.

- Added 2868, `P1-S9`: x 529.7 to 547.4, y -187.8 to -181.1.
- Platform 2: deleted PCIP's P2-S5 (38 before this entry, x 541.8 to 550.5) and added 2869, `P2-S10`, at x 545.9 to 564.0, y -141.8 to -134.6.
- The 15 wall lines of P2-S5's enclosure moved 22.1 ft east, by their own width (x 533.5 to 555.6 becomes 555.6 to 577.7), with a note in each `source`. Before this entry they were 1705, 1706, 1707, 1717, 1720, 1721, 1751, 1752, 1753, 1768, 1769, 1770, 1773, 1776 and 2341; each index is one lower now.
- Check: every VCE on platforms 1 and 2 is open. P1-S9 is VCE 4 of 8 on platform 1, and P2-S10 is VCE 6 of 10 on platform 2, both entered from the east.

## 30. Nov 18: Platforms 1 to 3, planned features, mezzanine edges, P2-S2 (53 edited, 1 deleted)

Indices are those of the file before this entry (2,870 features); every index above 34 is one lower now. The file has 2,869 features.

- `status: planned`, 46 features on platform 2:
  - the backwards-h cluster at x 477 to 507, beside the planned stairs on platform 3: P2-S4 (37), elevator 647 and 29 walls (1608, 1609, 1644, 1645, 1649, 1650, 1651, 1660, 1661, 1662, 1668, 1669, 1670, 1671, 1675, 1676, 1681, 1682, 1683, 1684, 1685, 1686, 1688, 1689, 1690, 2322, 2323, 2324, 2325);
  - the enclosure that entry 29 moved east, which partly overlaps P2-S10: its 15 walls (1704, 1705, 1706, 1716, 1719, 1720, 1750, 1751, 1752, 1767, 1768, 1769, 1772, 1775, 2340).
- `level: concourse`, six `#545252` mezzanine-edge walls:
  - platform 1, around the west VCEs: 2297 (x 289.5 to 352.1), 2299 (x 293.0) and 2318 (x 351.4 to 391.3);
  - platform 2: the L-shaped wall 2341 (x 533.5 to 542.0) and 2308 (x 340.0 to 349.4, by P2-S2);
  - platform 3: 2300 (x 339.5 to 344.6), across from it.
- P2-S2 (35) extended west to x 344.5, so it now runs x 344.5 to 366.5, the same as P3-S4 across the tracks. It takes in the unnamed stair 34 (x 344.5 to 349.4), which is part of the same stair and is deleted.
- Check: every VCE on platforms 1, 2 and 3 is open. Platform 2 has 8: P2-S1, S2, S3, S10, S6, S7, S8, S9.

## 31. Nov 18: Platform 4 cluster planned, P5-S12 narrowed (33 edited)

- `status: planned` on platform 4, in the cluster at x 477 to 507 around P4-S8 (already planned): elevator 641 and 31 walls (1609 to 1673, 2326, 2327), covering the stair outline with treads, the curved wall and the box around the elevator. The columns there (480, 481) are built and stay as they are.
- P5-S12 (66) narrowed from 5.4 ft to 3.4 ft, the width of P4-S10, centred between its side walls: y -5.3 to -1.9 (was -6.3 to -0.9). x is unchanged, 650.1 to 700.4.
- Check: every VCE on platforms 4 and 5 is open.

## 32. Nov 18: P4-S9 built again, its door swing arcs removed (1 edited, 8 deleted)

- P4-S9 (57) is built: its `"status": "planned"` from entry 16 is removed.
- Deleted the door leaves and swing arcs at its west entrance (1709, 1710, 1714, 1717, 1722, 1723) and the swing-arc remnant inside its east end (1769, 1775). The enclosure's outline walls stay.
- Check: P4-S9 is open, entered from the west, and every VCE on platform 4 is open (10 in all). The file has 2,861 features.

## 33. Nov 18: every planned feature deleted (174 deleted)

- Deleted all 174 features marked `"status": "planned"` (on the plans, not built). They had been flagged in entries 1, 2, 9, 12, 16, 30 and 31.
  - Platform 2: 44 walls, P2-S4 and an elevator.
  - Platform 3: 41 walls, an enclosure, an elevator, P3-S8, P3-S9 and an unnamed stair.
  - Platform 4: 31 walls, P4-S8 and an elevator.
  - Platform 5: 16 walls, P5-S9 and an unnamed stair.
  - Platform 6: 28 walls, P6-S9, an unnamed stair and an elevator.
- No feature in the file is marked planned any more. `SKIP_PLANNED` stays in the simulator in case one is added later.
- Check: all 11 platforms build, and no VCE is blocked on any of them. Simulator runs are unchanged, since planned features were already skipped. The file has 2,687 features.

## 34. Nov 18: Platform 7, missing stair and enclosure added (2 added)

- Added 2687, `P7-S10`, with `"mouth": "east"`: x 538.9 to 549.3, y 84.6 to 89.7 (10.4 x 5.1 ft). It sits 3 to 4 ft west of directly across from P8-S9, and its south-east corner is on column 357's north-east corner. It is the built stair drawn with light treads in your screenshots, which PCIP never digitized; its east end opens to the platform.
- Added 2688: a copy of the C-shaped `enclosure` 2091 on platform 8 (x 483.5 to 492.5, the box you called an elevator), put on platform 7 directly across from it. It is shifted 46.23 ft south so it sits in the same place across the platform: y 84.7 to 93.4, at the same x. Its type is kept as `enclosure`, the same as the original, so the simulator treats it as a solid block either way.
- Earlier attempts today put the stair at x 497.6 to 508.0 and then x 447.2 to 457.6, and briefly added a duplicate of elevator 621; all were corrected before this entry.
- Noted, not changed: in your close-up, the P7 escalator east of the Central Concourse sits at about x 360 to 371, while PCIP has P7-S8 at x 373.7 to 382.6.
- Check: every VCE on platform 7 is open (11 in all), and P7-S10 is entered from the east.

## 35. Nov 18: C-shaped walls at P8-S9 and P7-S10, VCEs renamed west to east (63 edited, 2 added, 8 deleted)

- The walls around P8-S9 joined into one C-shaped wall, closed on the west and open on the east where its mouth is. The 8 pieces (1620 and 1622 to 1628: a double-line outline and a diagonal break line) are replaced by one LineString: x 533.7 to 554.5, y 129.1 to 134.1.
- That C copied to platform 7 around P7-S10 (entry 34). It is stretched from P8-S9's 11.3 x 4.2 ft to P7-S10's 10.4 x 5.1 ft, so it wraps the stair the same way: x 531.5 to 550.6, y 84.0 to 90.1. Its south side runs across column 357.
- Every stair and escalator renamed `P{platform}-S{n}`, with n counting west to east by the centre of each polygon, the order the simulator numbers VCEs in. VCE n on platform p is now P{p}-S{n} on all 11 platforms. 63 of the 101 changed. Each changed feature keeps its previous name in a new `old_vce_name` property, so names used in earlier entries can still be found. The Train Hall escalators (TH-W/E) and the split flights ("west"/"east") lose those suffixes.

| Platform | Renamed (old → new) |
|---|---|
| 1 | P1-S9 → S4, P1-S6 south → S5 |
| 2 | P2-S10 → S4, P2-S6 → S5, P2-S7 → S6, P2-S8 → S7, P2-S9 → S8 |
| 3 | P3-TH-E → S1, P3-S3 west → S2, P3-S3 east → S3, P3-S10 → S8 |
| 4 | P4-TH-W → S1, P4-TH-E → S2, P4-S3 west → S3, P4-S3 east → S4, P4-S4 → S5, P4-S5 → S6, P4-S6 → S7, P4-S7 → S8 |
| 5 | P5-TH-W → S1, P5-TH-E → S2, P5-S4 west → S3, P5-S4 east → S4, P5-S12 → S9, P5-S13 → S10 |
| 6 | P6-TH-W → S1, P6-TH-E → S2, P6-S4 west → S3, P6-S4 east → S4, P6-S10 → S9, P6-S11 → S10 |
| 7 | P7-TH-W → S1, P7-TH-E → S2, P7-S5 west → S3, P7-S5 east → S4, P7-S6 → S5, P7-S7 → S6, P7-S8 → S7, P7-S9 → S8, P7-S10 → S9, P7-S11 → S10, P7-S12 → S11 |
| 8 | P8-TH-W → S1, P8-TH-E → S2, P8-S4 west → S3, P8-S4 east → S4 |
| 9 | P9-S5 → S4, P9-S6 → S5, P9-S7 → S6, P9-S9 → S7, P9-S10 → S8, P9-S11 → S9 |
| 10 | P10-S5 → S4, P10-S4 → S5, P10-S8 → S6, P10-S10 → S7, P10-S11 → S8, P10-S12 → S9 |
| 11 | P11-S4 → S3, P11-S6 → S4, P11-S7 → S5, P11-S8 → S6, P11-S9 → S7 |

- Check: all 11 platforms build, every VCE is open (101), and each VCE's number matches its name. The file has 2,683 features.

## 36. Nov 18: P4-S9 and its enclosure removed, P2-S8 lengthened (2 edited, 9 deleted)

Indices are those of the file before this entry (2,683 features). The file now has 2,674.

- Platform 4: deleted P4-S9 (52, x 541.8 to 553.9; `old_vce_name` P4-S9), the walls of its enclosure (1593, 1594, 1595, 1620, 1621 and the `#545252` wall 2148, x 533.2 to 555.6), and the short wall just west of it (1590, x 495.1 to 507.2, y -41.7). The last stair on platform 4 is now P4-S9 (it was P4-S10; `old_vce_name` P4-S10), keeping the west-to-east numbering.
- Platform 2: deleted the jogging wall 1998, which stepped from y -139.0 down to y -142.7 at x 816 and ran west to x 802.1.
- P2-S8 extended west to the length of P1-S8 (17.1 ft): x 817.6 to 834.7 (was 827.8 to 834.7), y -138.2 to -133.9.
- Check: every VCE on platforms 2 and 4 is open (8 and 9). P2-S8 is entered from the east.

## 37. Nov 18: Platform 2, old P2-S8 linework removed (2 edited, 18 deleted)

Indices are those of the file before this entry (2,674 features). The file now has 2,656.

- Deleted 18 wall lines that drew the old, shorter P2-S8. Per your note they are above platform level:
  - the stepped wall just west of it (2003, x 807.1 to 816.6);
  - the west end of its old outline (2006, 2007, 2008);
  - the tread lines now inside the lengthened stair (2011 to 2023, 2025; x 818.1 to 824.1).
  
  The six long side walls that run the full length to x 836.4 stay (2004, 2005, 2009, 2010, 2024, 2026).
- Opening the west end changed which end the simulator chose for two VCEs, so both are pinned to what they were: P2-S8 gets `"mouth": "east"` and P2-S7 (the escalator just west, x 760.8 to 805.5) gets `"mouth": "west"`.
- Check: every VCE on platform 2 is open (8), with the same mouths as before this entry.

## 38. Nov 18: Platforms 1 and 2, walls by P2-S6 and P2-S7 removed (17 deleted)

Indices are those of the file before this entry (2,656 features). The file now has 2,639.

- Platform 2: deleted the box drawn just south of P2-S7 (x 762.9 to 807.1, y -142.9 to -138.2): walls 1972 to 1975 and 1991 to 2000. P2-S7's own outline stays.
- Platform 2: deleted two short `#545252` segments on the south edge, 2129 (x 710.2 to 716.0, by P2-S6) and 2137 (x 749.4 to 757.8, by P2-S7).
- Platform 1: deleted the L-shaped `#545252` wall 2132 across from them (x 716.0 to 751.2, y -193.5 to -174.5).
- Check: every VCE on platforms 1 and 2 is open (8 each), with the same mouths as before.

## 39. Nov 18: P4-S7 mouth widened (2 edited, 2 added)

- The side walls of P4-S7's enclosure, 1256 (south) and 1269 (north), each ran 0.5 ft past the stair's east end, to x 375.2, and turned back in a small hook. After the simulator's 1-pixel wall growth, those ends narrowed the 12-pixel mouth to 8. Each is now split at the hook into its outer line (kept as 1256 and 1269) and its inner line (added as 2639 and 2640), and all four lines stop at the stair's east end (x 374.7).
- Check: P4-S7's mouth is open across the stair's full width, and every VCE on platform 4 is open with the same mouths as before. The file has 2,641 features.
- Not changed: riders still pass P4-S7 by for P4-S8, because P4-S8 became one of the two easternmost VCEs, which get `RIGHT_VCE_PREFERENCE_BIAS`, when entry 36 deleted the old P4-S9.

## 40. Nov 18: Platform 4, enclosure around column 477 to concourse level (1 edited)

- `level: concourse`: enclosure 2031 (x -22.3 to -19.1, y -54.4 to -49.2), drawn around column 477 just south-west of P4-S3. The column stays at platform level.
- Check: every VCE on platform 4 is open, with the same mouths as before.

## 41. Nov 18: Platform 4, obstruction in front of P4-S8 removed (5 deleted)

Indices are those of the file before this entry (2,641 features). The file now has 2,636.

- Deleted the obstruction at the east end of P4-S8's enclosure (x 430.5 to 432.4), about 6 ft in front of its mouth: column 473 (y -49.2 to -47.3, off the column grid, inside the enclosure) and the stub walls 1585 to 1588. Together they narrowed the way out to about half the stair's width. The grid columns at x 439 to 441 stay.
- Check: the way out of P4-S8 is open across 10 of the stair's 13 pixel rows all the way to the end of the enclosure; the rest are the enclosure's own side lines. Every VCE on platform 4 is open, with the same mouths as before.

## 42. Nov 18: Platform 4, wall stub beside P4-S3's mouth removed (1 deleted)

- Deleted wall 680 (x -22.3 to -19.2, y -43.5), a 3-ft stub that stuck out west of P4-S3's mouth along its north side. Column 477, on the south side of the mouth, stays.
- Check: every VCE on platform 4 is open, with the same mouths as before. The file has 2,635 features.

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
