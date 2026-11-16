"""
Penn Station platform crowd simulator: agent-based model of detraining and boarding passengers.

GEOMETRY
    The whole station comes from the PCIP GeoJSON (shapes_pcip_phase_1.geojson, in feet); it is downloaded next to this
    script the first time if it is missing. Choose a platform (1-11) with the slider or `--platform N`; it is rasterised
    at PX_PER_FT. Stairs and escalators are the VCEs. Where the drawn walls completely close a VCE mouth, an opening is cut
    through them (OPEN_BLOCKED_VCE_MOUTHS). VCEs that are still unreachable (e.g. the sealed east end of platform 7) are
    drawn gray and left closed. Platforms 1 and 2 are one U-shaped polygon in the file and are split into its two strips.
    Features whose "level" is not "platform" (concourse-level stairs, elevators, walls; "annotation" = CAD symbols kept for
    reference) and features marked "status": "planned" (on the plans but not built) are ignored (PLATFORM_LEVEL_ONLY,
    SKIP_PLANNED); start-up prints how many.
    A stair/escalator polygon may carry "mouth": "west" | "east" | "north" | "south", the end where it meets the open platform
    (riders step on and off the platform there). Without it the end is worked out from the surrounding walls. The other end is
    where riders leave the platform: alighting riders vanish there and boarding riders appear. The two flights of platform 5's
    T-shaped stair are drawn as two VCEs for this reason; the stem of the T is overhead (level "concourse") and is ignored.

TRAINS
    NJ Transit MultiLevel coaches, 85 ft x 10 ft (published). Door positions and width are ESTIMATES (DOOR_POSITIONS_FT,
    DOOR_WIDTH_FT). One train per side of the platform, berthed at the east end of the straight platform edge (ASSUMPTION;
    the berth slider moves it west). A door is only used where there is open platform in front of it (MIN_DOOR_DEPTH_PX).

PASSENGERS
    Alighting (green): each rider picks one of the doors of their own car - walking distance to the stairs/escalators, plus
    the queue already at that door, plus noise - and walks to the nearest stair/escalator ('eastern preference' bias applies).
    Departing (blue): appear where the alighting riders vanish (the exit line at the far end of a stair/escalator), walk to
    its mouth, step off onto the platform, pick a door of their train that is no longer letting people off, board
    (DEPARTING_START_AT_VCE_EXIT). On a stair/escalator the two directions each get their own lane, so riders going
    up and down never block each other.

ESCALATORS
    The GeoJSON says which VCEs are escalators ("type": "escalator"; the others are stairs). Each escalator can be set to
        both    a lane each way, like a stair (the default)
        up      platform -> concourse: alighting riders use it, nobody comes down it
        down    concourse -> platform: boarding riders arrive by it, alighting riders never enter it
    Stairs always carry both. Set the directions
        * in the dashboard: click an escalator on the map or its card (both -> up -> down -> both); arrows show the setting,
        * on the command line: --escalators "3=up,P5-S8=down"  (a VCE number as the dashboard shows it, or a vce_name;
          "all=down", or just "down", sets every escalator),
        * in this file: ESCALATOR_DIRECTIONS = {'P5-S8': 'down'} (by vce_name) and DEFAULT_ESCALATOR_DIRECTION.
    The eastern preference goes to the two easternmost VCEs that alighting riders can use, so an eastern escalator set to
    "down" hands it to the next VCE west. Riders already on an escalator when it is switched finish their ride.

CROWD-MOVEMENT ADDITIONS to the original movement rule (each can be switched off with the constant named):
    PATIENCE_TICKS                   riders who stop making progress stop avoiding crowds (kills standoff rings)
    SWAP_OPPOSING_RIDERS             riders blocking each other head-on, who would both get closer, trade places
    DEADLOCK_SWAP_TICKS              a rider stuck for ~50 s trades places with an opposing rider whatever the rules above say
    DEADLOCK_SQUEEZE_TICKS           a boarding rider stuck that long also accepts less personal space (empties jammed pockets)
    EDGE_STRIP_PX / EDGE_STRIP_PENALTY   riders don't idle on the 1.5 ft strip along the platform edge: a step onto or along it that
                                     doesn't bring them closer to where they're going costs extra, so waiting riders drift off it,
                                     while riders who are walking use it freely
    KEEP_CLEAR_PX / DEPARTING_MAX_CROWD   boarding riders keep clear of doors still letting people off, and only step off
                                     the stairs into uncrowded cells
    Optional, off by default: SQUEEZE_TICKS, MOUTH_SPACING_PX, STAIR_ENTRY_NEEDS_PLATFORM_ROOM = False.
    BOARDING_DELAY (120 s) opens boarding after most alighting riders have left; lower it to study counter-flow.

RUN
    python simulator.py                       # dashboard
    python simulator.py --headless 600        # no GUI; prints a timeline (add --platform 7 --seed 1)
Requires numpy, scipy, matplotlib and opencv-python.
"""
import random
import numpy as np
import matplotlib.pyplot as plt

from config import *
from station import load_station
from routing import parse_directions, resolve_directions, alight_field, describe_directions
from trains import place_trains
from agents import PedestrianModel
from world import build_platform, build_door_fields, default_params
from gui import SimulationGUI


def run_headless(platform=PLATFORM, seconds=900.0, cars=CARS_PER_TRAIN, berth_ft=0.0, seed=None, report=30.0,
                 escalators=None, **overrides):
    """Runs the model without the GUI and prints a short timeline - handy for batch experiments.
    escalators: escalator directions, as for --escalators: a dict such as {3: 'up', 'P5-S8': 'down'} or the string
    "3=up,P5-S8=down" ('all=down', or just 'down', sets every escalator). Without it every escalator carries both ways."""
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    station = load_station()
    scene, geo, routing = build_platform(station, str(platform))
    modes = resolve_directions(scene, escalators)
    layout = place_trains(scene, cars, berth_ft)
    params = {**default_params(), **overrides}
    fields = build_door_fields(routing, layout) if params['dep_per_car'] > 0 else {}
    field, _ = alight_field(routing, geo, modes, RIGHT_VCE_PREFERENCE_BIAS)
    m = PedestrianModel(scene, geo, routing, layout, fields, field, params, modes)
    print(f"Platform {platform}: {len(m.trains[1]['cars'])}+{len(m.trains[2]['cars'])} cars, {len(m.doors)} doors, "
          f"{m.total_pax} alighting / {m.total_dep} departing passengers")
    directions = describe_directions(scene, modes)
    if directions:
        print(f"  escalator directions: {directions}")
        if np.isinf(field).all():
            print("  warning: no VCE is left for alighting riders to leave the platform by - nobody will alight")
    next_report = 0.0
    while m.sim_time < seconds:
        m.step()
        if m.sim_time >= next_report:
            next_report += report
            print(f"  t={m.sim_time:5.0f}s  on platform {len(m.agents):4d}  alighted {m.alighted:4d}/{m.total_pax}"
                  f"  exited {sum(m.vce_counts.values()):4d}  boarded {m.boarded:4d}/{m.total_dep}")
        if m.alighted >= m.total_pax and not m.agents and m.boarded >= m.total_dep:
            print(f"  everyone is done at t={m.sim_time:.0f}s")
            break
    if directions:                                               # per-VCE tally, to see what the directions did
        print("  per VCE: exited = alighting riders who left the platform by it, entered = boarding riders who came onto it")
        for v in range(1, scene['n_vces'] + 1):
            info = scene['vce_info'][v]
            label = info['kind'] + (f" {m.vce_mode[v]}" if info['kind'] == 'escalator' else '')
            print(f"    VCE {v:2d} {info['name'] or '(unnamed)':12s} {label:16s} exited {m.vce_counts[v]:4d}  entered {m.vce_boarded[v]:4d}")
    return m


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Agent-based simulation of detraining/boarding passengers at Penn Station.")
    ap.add_argument('--platform', type=int, default=PLATFORM, help="platform to simulate (1-11); can also be changed in the GUI")
    ap.add_argument('--headless', type=float, metavar='SECONDS', help="run without the GUI for this many simulated seconds")
    ap.add_argument('--seed', type=int, default=None, help="random seed (headless runs)")
    ap.add_argument('--escalators', default=None, metavar='SPEC',
                    help="escalator directions, e.g. \"3=up,P5-S8=down\": a VCE number as the dashboard shows it, or a vce_name, "
                         "set to up (platform -> concourse), down (concourse -> platform) or both (the default); "
                         "\"all=down\", or just \"down\", sets every escalator. In the dashboard, click an escalator to change it.")
    args = ap.parse_args()
    try:
        parse_directions(args.escalators)
    except ValueError as exc:
        ap.error(f"--escalators {exc}")
    if args.headless:
        run_headless(args.platform, args.headless, seed=args.seed, escalators=args.escalators)
    else:
        gui = SimulationGUI(args.platform, escalators=args.escalators)
        plt.show()
