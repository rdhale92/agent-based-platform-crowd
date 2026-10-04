"""
Penn Station platform crowd simulator: agent-based model of detraining and boarding passengers.

GEOMETRY
    The whole station comes from the PCIP GeoJSON (shapes_pcip_phase_1.geojson, in feet); it is downloaded next to this
    script the first time if it is missing. Choose a platform (1-11) with the slider or `--platform N`; it is rasterised
    at PX_PER_FT. Stairs and escalators are the VCEs. Where the drawn walls completely close a VCE mouth, an opening is cut
    through them (OPEN_BLOCKED_VCE_MOUTHS). VCEs that are still unreachable (e.g. the sealed east end of platform 7) are
    drawn gray and left closed. Platforms 1 and 2 are one U-shaped polygon in the file and are split into its two strips.

TRAINS
    NJ Transit MultiLevel coaches, 85 ft x 10 ft (published). Door positions and width are ESTIMATES (DOOR_POSITIONS_FT,
    DOOR_WIDTH_FT). One train per side of the platform, berthed at the east end of the straight platform edge (ASSUMPTION;
    the berth slider moves it west). A door is only used where there is open platform in front of it (MIN_DOOR_DEPTH_PX).

PASSENGERS
    Alighting (green): each rider picks one of the doors of their own car - walking distance to the stairs/escalators, plus
    the queue already at that door, plus noise - and walks to the nearest stair/escalator ('eastern preference' bias applies).
    Departing (blue): step off the stairs/escalators, pick a door of their train that is no longer letting people off, board.

CROWD-MOVEMENT ADDITIONS to the original movement rule (each can be switched off with the constant named):
    PATIENCE_TICKS                   riders who stop making progress stop avoiding crowds (kills standoff rings)
    SWAP_OPPOSING_RIDERS             riders blocking each other head-on, who would both get closer, trade places
    KEEP_CLEAR_PX / DEPARTING_MAX_CROWD   boarding riders keep clear of doors still letting people off, and only step off
                                     the stairs into uncrowded cells
    Optional, off by default: SQUEEZE_TICKS, MOUTH_SPACING_PX, STAIR_ENTRY_NEEDS_PLATFORM_ROOM = False.
    BOARDING_DELAY (120 s) opens boarding after most alighting riders have left; lower it to study counter-flow.

RUN
    python simulator.py                       # dashboard
    python simulator.py --headless 600        # no GUI; prints a timeline (add --platform 7 --seed 1)
Requires numpy, scipy, matplotlib and opencv-python.
"""
import itertools
import json
import os
import random
import urllib.request
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button, Slider
from matplotlib.collections import EllipseCollection, PolyCollection, LineCollection
from matplotlib.patches import Rectangle
from scipy.ndimage import distance_transform_edt, label
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
import cv2

# ==========================================
# CONFIGURATION PARAMETERS (defaults for the GUI sliders)
# ==========================================
# ---- station geometry (replaces the old platform5_polygons.png) ----
GEOJSON_FILE = "shapes_pcip_phase_1.geojson"   # whole-station geometry in feet (downloaded automatically if missing)
GEOJSON_URL = ("https://github.com/effective-transit-alliance/platform-crowd-model/raw/refs/heads/"
               "kkysen/per-vce/data/shapes_pcip_phase_1.geojson")
PLATFORM = 5                     # platform simulated at start-up (1-11); changeable in the GUI (applies on Reset)
PX_PER_FT = 2.28                 # Raster scale (pixels per foot), same scale the PNG used
INCLUDE_UNNAMED_VCES = True      # stairs/escalators with no vce_name in the GeoJSON are still modelled as VCEs
INCLUDE_ELEVATORS = False        # elevators are drawn as solid blocks; True models them as VCEs too
OPEN_BLOCKED_VCE_MOUTHS = True   # if the drawn walls close a stair/escalator mouth, cut an opening through them
TRACK_MARGIN_FT = 14.0           # raster margin on each track side of the platform (room to draw the cars)
END_MARGIN_FT = 6.0              # raster margin / clearance at the platform ends

# ---- NJ Transit MultiLevel coach (Bombardier / Alstom) ----
CAR_LENGTH_FT = 85.0             # length over couplers = car pitch (published: 85 ft)
CAR_WIDTH_FT = 10.0              # body width (published: 10 ft 0 in)
CAR_COUPLER_GAP_FT = 1.5         # visual gap drawn between neighbouring car bodies (approximate)
CAR_PLATFORM_GAP_FT = 0.5        # gap between the car side and the platform edge (approximate)
DOOR_WIDTH_FT = 3.0              # single-width side door (approximate; ADA minimum clear opening is 32 in)
DOOR_POSITIONS_FT = (10.0, 75.0) # door centres measured from the car's west end (approximate: one per end)
DOORS_PER_CAR = len(DOOR_POSITIONS_FT)
MIN_DOOR_DEPTH_PX = 10           # A door is only used if at least this much open platform (px, ~4.4 ft) lies in front of it;
                                 # trains berthed beside a wall or a narrow sliver of platform don't open onto it
CARS_PER_TRAIN = 10              # default train length (cars)
MAX_CARS = 12                    # upper end of the cars-per-train slider

# ---- passengers / flows ----
AGENT_SIZE_FT = 2.0              # Each agent occupies an AGENT_SIZE_FT x AGENT_SIZE_FT square
WALL_DILATE_PX = 1               # Grow obstacles by this many px for movement (seals thin boundary lines)
CROWDING_BUFFER_PX = 1           # Extra ring (pixels) beyond touching in which neighbors count as "crowding"
PAXPERDOOR = 30                  # Default alighting passengers per door (sliders are per car = DOORS_PER_CAR doors)
DEPARTING_PER_DOOR = 10          # Default departing (boarding) passengers per door
MAX_PAX_PER_DOOR = 45            # Upper end of the alighting slider (per door)
MAX_DEPARTING_PER_DOOR = 30      # Upper end of the departing slider (per door)
SPAWN_RATE_PER_SECOND = 0.8      # Maximum passengers released per second per door
MAX_SPAWN_RATE = 1.0             # Upper end of the spawn-rate slider
DEPART_RATE = 4.0                # Departing passengers stepping off the stairs/escalators per second (per train)
BOARDING_DELAY = 120             # Seconds after a train's arrival before its departing passengers start to appear
DEPARTING_MAX_CROWD = 2          # A departing passenger only steps off the stairs into a cell with at most this many
                                 # neighbours (otherwise they wait on the stairs) - keeps stair mouths from locking up
# Alighting riders choose which door of their own car to leave by: a random-utility choice made when the train arrives.
#   cost(door) = DOOR_PREF_WEIGHT * walking distance to the stairs/escalators (ft)
#              + queue-length cost (riders already heading for that door) + logistic noise
DOOR_CHOICE_RANGE_CARS = 0       # 0 = only the doors of the rider's own car; 1 = the neighbouring cars' doors too, ...
DOOR_PREF_WEIGHT = 1.0           # weight on the walking distance (ft) from a door to the stairs/escalators
DOOR_QUEUE_AWARENESS = 0.6       # share of a door queue's real waiting-time cost that riders take into account (0 = ignore)
DOOR_NOISE_FT = 12.0             # randomness in door choice (logistic scale, in ft of walking)
# Departing riders choose which door of their train to board
CAR_CROWD_WEIGHT_FT = 4.0        # cost (ft) added per passenger already crowding a door
CAR_NOISE_FT = 25.0              # randomness in door choice (logistic scale, in ft of walking)
TIME_STEP = 0.1                  # Simulation seconds per step (each agent still makes at most one 1-px move per step)
PLATFORM_SPEED = 9.0             # Movement ticks per second on the platform (1 tick = 1 px)
VCE_SPEED = 7.0                  # Movement ticks per second inside a VCE (1 tick = 1 px)
ANIMATION_INTERVAL = 15          # Refresh rate in milliseconds (lower = faster rendering)
RIGHT_VCE_PREFERENCE_BIAS = 300  # Distance bias (px) favoring the 2 easternmost VCEs
CROWDING_PENALTY = 40.0          # Penalty factor for local crowding
SWAP_OPPOSING_RIDERS = True      # alighting and departing riders who block each other head-on swap places
PATIENCE_TICKS = 90              # A rider who makes no progress for this many moves (~10 s) stops avoiding crowds: the
                                 # crowding penalty fades linearly to zero. Prevents standoff rings around crowded stairs
                                 # and doors. 0 = off (the original behaviour: crowding is always avoided).
# --- optional extras, OFF by default (they helped some platforms and hurt others in testing) ---
SQUEEZE_TICKS = 0                # >0: a rider still stuck after PATIENCE_TICKS accepts 1 px less personal space per further
                                 # SQUEEZE_TICKS without progress (e.g. 30). 0 = off.
MOUTH_SPACING_PX = None          # e.g. 2: riders next to a stair/escalator mouth (within MOUTH_ZONE_PX) only need this much
                                 # personal space (radius, px), so they funnel in shoulder to shoulder. None = off.
MOUTH_ZONE_PX = 8                # size of that zone around a mouth (px)
STAIR_ENTRY_NEEDS_PLATFORM_ROOM = True   # True = the original rule: stepping onto a stair also needs the platform cell under the
                                 # first step to be free of other riders' footprints. False = only the stair itself must have room.
KEEP_CLEAR_PX = 4                # Boarding riders stay this many px clear of a door that is still letting people off
CONGESTED_THRESHOLD = 15         # A VCE card turns red when more than this many pax are inside it
# ---- window ----
FIG_W, FIG_H = 15.0, 11.5        # figure size (inches)
DEFAULT_ZOOM = 1.5               # initial zoom (1 = whole platform length visible)
MAX_VCE_CARDS = 18               # cards reserved for the VCE read-outs
# ==========================================

# ---- Theme (mirrors the HTML preview) ----
BG = '#f5f5f5'
CANVAS_BG = '#fafafa'
BORDER = '#dddddd'
CARD_BORDER = '#eeeeee'
TEXT = '#333333'
MUTED = '#666666'
FAINT = '#999999'
DOOR_COLOR = '#dc1e1e'
IMG_VCE_SWATCH = '#ff7400'       # legend colors while showing the drawn geometry
IMG_OBS_SWATCH = '#404040'
VCE_COLOR = '#ff0000'
OBSTACLE_COLOR = '#333333'
FLOOR_COLOR = '#fff3b0'          # platform floor (yellow, as in the PNG)
FLOOR_EDGE = '#b59b00'
STAIR_COLOR = '#ff7400'
ESCALATOR_COLOR = '#f2530d'
ELEVATOR_COLOR = '#74a7ee'
CAR_COLOR = '#dde2ea'
CAR_EDGE = '#6b7280'
PAX_RGBA = (34 / 255, 197 / 255, 94 / 255, 0.8)    # green  = alighting
DEP_RGBA = (37 / 255, 99 / 255, 235 / 255, 0.85)   # blue   = departing
ACCENT = '#4a90e2'
CONGESTED_EDGE = '#e24b4a'
CONGESTED_BG = '#fcebeb'

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans']


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ==========================================
# 1. STATION GEOMETRY  (GeoJSON in feet -> raster masks on the simulation grid)
# ==========================================
# The GeoJSON frame: x = feet east of the Master Plan's west edge, y = feet north of platform 5's centerline.
# Feature types used: platform (floor), wall (lines), column / enclosure (solid blocks),
# stair / escalator (the VCEs), elevator (solid block unless INCLUDE_ELEVATORS).
def ensure_geojson(path=GEOJSON_FILE):
    """Find the station GeoJSON next to this script (or in the working dir); download it if it is missing."""
    here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    for p in (path, os.path.join(here, os.path.basename(path))):
        if os.path.exists(p):
            return p
    print(f"{path} not found - downloading the station geometry from GitHub ...")
    target = os.path.join(here, os.path.basename(path))
    try:
        urllib.request.urlretrieve(GEOJSON_URL, target)
    except Exception as exc:
        raise FileNotFoundError(
            f"Could not find or download {path}.\n  Download it from\n  {GEOJSON_URL}\n"
            f"  and save it next to simulator.py. ({exc})")
    return target


def load_station(path=GEOJSON_FILE):
    with open(ensure_geojson(path)) as fh:
        data = json.load(fh)
    station = {'frame': data.get('frame', ''), 'polys': defaultdict(list), 'walls': []}
    for f in data['features']:
        props, g = f.get('properties') or {}, f.get('geometry')
        if not g:
            continue
        if g['type'] == 'Polygon':
            rings = [np.asarray(r, dtype=float) for r in g['coordinates']]
            if len(rings[0]) >= 3:
                b = (rings[0][:, 0].min(), rings[0][:, 1].min(), rings[0][:, 0].max(), rings[0][:, 1].max())
                station['polys'][props.get('type')].append({'props': props, 'rings': rings, 'bbox': b})
        elif g['type'] == 'LineString':
            pts = np.asarray(g['coordinates'], dtype=float)
            if len(pts) >= 2:
                b = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
                station['walls'].append({'props': props, 'pts': pts, 'bbox': b})
    return station


def _to_px(pts_ft, ox, oy):
    """feet (x east, y north) -> pixel coordinates (x right, y down); pixel i is centred on coordinate i."""
    return np.column_stack(((pts_ft[:, 0] - ox) * PX_PER_FT - 0.5, (oy - pts_ft[:, 1]) * PX_PER_FT - 0.5))


def _fill(img, pts_px, value=1):
    cv2.fillPoly(img, [np.round(pts_px * 16).astype(np.int32)], value, lineType=cv2.LINE_8, shift=4)


def _line(img, pts_px, thickness=1, value=1):
    cv2.polylines(img, [np.round(pts_px * 16).astype(np.int32)], False, value, thickness=thickness,
                  lineType=cv2.LINE_8, shift=4)


def _overlaps(b, win):
    return not (b[2] < win[0] or b[0] > win[2] or b[3] < win[1] or b[1] > win[3])


def _split_u_platform(station):
    """Platforms 1 and 2 are drawn as ONE U-shaped polygon ('1/2'). Returns (polygon, {'1': (ylo, yhi), '2': (ylo, yhi)})."""
    poly = next(p for p in station['polys']['platform'] if p['props'].get('platform') == '1/2')
    x0, y0, x1, y1 = poly['bbox']
    h, w = int(np.ceil(y1 - y0)) + 2, int(np.ceil(x1 - x0)) + 2
    m = np.zeros((h, w), np.uint8)
    _fill(m, np.column_stack((poly['rings'][0][:, 0] - x0, y1 - poly['rings'][0][:, 1])))
    prof = m.sum(axis=1)
    inrun = prof > 0.3 * prof.max()
    runs, start = [], None
    for r, v in enumerate(inrun):
        if v and start is None:
            start = r
        if (not v) and start is not None:
            runs.append((start, r - 1)); start = None
    if start is not None:
        runs.append((start, h - 1))
    runs = sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:2]     # the two long strips
    runs.sort()                                                           # north strip (small row) first
    (n0, n1), (s0, s1) = runs
    return poly, {'2': (y1 - n1 - 0.5, y1 - n0 + 0.5), '1': (y1 - s1 - 0.5, y1 - s0 + 0.5)}


def platform_ids(station):
    return [str(i) for i in range(1, 12)]


def _floor_polygon(station, pid):
    """(rings, (ylo, yhi) clip or None) for one platform."""
    if pid in ('1', '2'):
        poly, ranges = _split_u_platform(station)
        return poly['rings'], ranges[pid]
    for p in station['polys']['platform']:
        if p['props'].get('platform') == pid:
            return p['rings'], None
    raise KeyError(f"Platform {pid} not found in the GeoJSON")


def _longest_run(prof, tol=1.5, max_gap=6):
    """Longest stretch of columns where an edge profile (row per column) stays within `tol` px of its most common value."""
    valid = ~np.isnan(prof)
    if valid.sum() < 10:
        return None
    vals = np.round(prof[valid]).astype(int)
    mode = np.bincount(vals - vals.min()).argmax() + vals.min()
    ok = valid & (np.abs(np.nan_to_num(prof, nan=1e9) - mode) <= tol)
    idx = np.where(ok)[0]
    if len(idx) == 0:
        return None
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > max_gap + 1:
            runs.append((start, prev)); start = i
        prev = i
    runs.append((start, prev))
    return max(runs, key=lambda r: r[1] - r[0])


def build_scene(station, pid):
    """Rasterises one platform (plus a strip of track either side) into the masks the simulator uses."""
    pid = str(pid)
    rings, clip = _floor_polygon(station, pid)
    fx0, fy0, fx1, fy1 = (rings[0][:, 0].min(), rings[0][:, 1].min(), rings[0][:, 0].max(), rings[0][:, 1].max())
    if clip is not None:
        fy0, fy1 = max(fy0, clip[0]), min(fy1, clip[1])
    ox, oy = fx0 - END_MARGIN_FT, fy1 + TRACK_MARGIN_FT
    W = int(np.ceil((fx1 + END_MARGIN_FT - ox) * PX_PER_FT))
    H = int(np.ceil((oy - (fy0 - TRACK_MARGIN_FT)) * PX_PER_FT))
    win = (ox, fy0 - TRACK_MARGIN_FT, ox + W / PX_PER_FT, oy)

    floor = np.zeros((H, W), np.uint8)
    _fill(floor, _to_px(rings[0], ox, oy))
    for hole in rings[1:]:
        _fill(floor, _to_px(hole, ox, oy), 0)
    if clip is not None:                                   # keep just this platform's strip of the U
        rows = np.arange(H)
        y_of_row = oy - (rows + 0.5) / PX_PER_FT
        floor[(y_of_row < clip[0]) | (y_of_row > clip[1])] = 0
    floor = floor.astype(bool)

    geom = {'columns': [], 'enclosures': [], 'elevators': [], 'walls': [], 'vces': []}
    solid = np.zeros((H, W), np.uint8)
    for kind, key in (('column', 'columns'), ('enclosure', 'enclosures')):
        for p in station['polys'][kind]:
            if _overlaps(p['bbox'], win):
                pts = _to_px(p['rings'][0], ox, oy)
                _fill(solid, pts)
                geom[key].append(pts)
    for w in station['walls']:
        if _overlaps(w['bbox'], win):
            pts = _to_px(w['pts'], ox, oy)
            _line(solid, pts, thickness=1)
            geom['walls'].append(pts)

    # --- VCEs: stairs + escalators whose centre lies on this platform's strip ---
    vce_src = []
    kinds = ['stair', 'escalator'] + (['elevator'] if INCLUDE_ELEVATORS else [])
    for kind in kinds:
        for p in station['polys'][kind]:
            b = p['bbox']
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if not (win[0] <= cx <= win[2] and fy0 - 1.0 <= cy <= fy1 + 1.0):
                continue
            name = p['props'].get('vce_name', '') or ''
            if not name and not INCLUDE_UNNAMED_VCES and kind != 'elevator':
                continue
            vce_src.append({'kind': kind, 'name': name, 'ring': p['rings'][0], 'cx': cx})
    vce_src.sort(key=lambda v: v['cx'])                    # number west (1) -> east (N)
    labeled = np.zeros((H, W), np.int16)
    for i, v in enumerate(vce_src, start=1):
        _fill(labeled, _to_px(v['ring'], ox, oy), i)
    sizes = np.bincount(labeled.ravel(), minlength=len(vce_src) + 1)
    keep = [i for i in range(1, len(vce_src) + 1) if sizes[i] > 50]          # drop slivers (< ~10 sq ft)
    labeled_vces = np.zeros((H, W), np.int16)
    vce_info = {}
    for new_id, old_id in enumerate(keep, start=1):
        labeled_vces[labeled == old_id] = new_id
        v = vce_src[old_id - 1]
        ring_px = _to_px(v['ring'], ox, oy)
        (_, _), (rw, rh), _ = cv2.minAreaRect(ring_px.astype(np.float32))
        vce_info[new_id] = {'name': v['name'], 'kind': v['kind'], 'ring_px': ring_px,
                            'width_ft': min(rw, rh) / PX_PER_FT, 'length_ft': max(rw, rh) / PX_PER_FT}
        geom['vces'].append((new_id, v['kind'], ring_px))
    vce_mask = labeled_vces > 0

    for p in station['polys']['elevator']:
        if _overlaps(p['bbox'], win):
            pts = _to_px(p['rings'][0], ox, oy)
            geom['elevators'].append(pts)
            if not INCLUDE_ELEVATORS:
                _fill(solid, pts)

    # --- masks (same meaning as before) ---
    obstacle_mask = (~floor | (solid > 0)) & ~vce_mask
    if WALL_DILATE_PX > 0:
        k = 2 * WALL_DILATE_PX + 1
        grown = cv2.dilate(obstacle_mask.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
        wall_mask = grown & ~vce_mask
    else:
        wall_mask = obstacle_mask.copy()

    geom['floor'] = [_to_px(r, ox, oy) for r in rings[:1]]
    return {'pid': pid, 'H': H, 'W': W, 'ox': ox, 'oy': oy, 'floor': floor,
            'obstacle_mask': obstacle_mask, 'wall_mask': wall_mask,
            'labeled_vces': labeled_vces, 'n_vces': len(keep), 'vce_info': vce_info,
            'geom': geom}



# ==========================================
# 2. ROUTING
# ==========================================
def build_walk_graph(wall_mask, labeled_vces, entry_pixels):
    """8-connected graph over walkable platform pixels, using the SAME movement rules as the agents
    (no walking through walls, no cutting a wall's corner). VCE interiors are excluded - an agent that
    steps into a VCE is committed to it - except the entry pixels of each VCE. Stepping ONTO an entry
    pixel is penalised so that routes never cut through a VCE's doorway."""
    H, W = wall_mask.shape
    free = ~wall_mask
    node = free & ~(labeled_vces > 0)
    for ys, xs in entry_pixels.values():
        node[ys, xs] = True
    idx = -np.ones((H, W), dtype=np.int64)
    idx[node] = np.arange(node.sum())
    entry_flag = np.zeros((H, W), dtype=bool)
    for ys, xs in entry_pixels.values():
        entry_flag[ys, xs] = True

    rows, cols, wts = [], [], []
    for dy, dx in [(0, 1), (1, 0), (1, 1), (1, -1)]:
        y0, y1 = 0, H - dy
        x0, x1 = max(0, -dx), W - max(0, dx)
        a = idx[y0:y1, x0:x1]
        b = idx[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        ok = (a >= 0) & (b >= 0)
        if dy and dx:                                  # diagonal: both orthogonal neighbours must be non-wall
            ok &= free[y0:y1, x0 + dx:x1 + dx] & free[y0 + dy:y1 + dy, x0:x1]
        w = np.full(a.shape, np.hypot(dy, dx), dtype=np.float64)
        w_ab = w + 1000.0 * entry_flag[y0 + dy:y1 + dy, x0 + dx:x1 + dx]   # moving a -> b onto an entry pixel
        w_ba = w + 1000.0 * entry_flag[y0:y1, x0:x1]                        # moving b -> a onto an entry pixel
        rows.append(a[ok]); cols.append(b[ok]); wts.append(w_ab[ok])
        rows.append(b[ok]); cols.append(a[ok]); wts.append(w_ba[ok])
    n = int(node.sum())
    graph = coo_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))),
                       shape=(n, n)).tocsr()
    return graph, idx, node


def analyze_vces(scene):
    """For every VCE decide where its platform-side mouth is, and make sure that mouth is actually reachable.

    * Candidate mouths are the two ends along the stair/escalator's long axis (plus the two short-axis ends for
      near-square stairs). The 'landing' end - the one whose side walls run on past the polygon - is preferred.
    * The CAD linework frequently closes a mouth completely (a wall across the end, a boxed-in landing). With
      OPEN_BLOCKED_VCE_MOUTHS, a corridor as wide as the mouth is cleared from the mouth out to the open platform, using the
      candidate that needs the fewest wall pixels removed. These openings are recorded in scene['openings'].
    * Returns, per VCE: entry pixels (alighting riders step in here), exit mask (far end, where riders leave the
      platform) and src pixels (where departing riders step out of the mouth)."""
    lv, floor = scene['labeled_vces'], scene['floor']
    wall, obs = scene['wall_mask'], scene['obstacle_mask']
    H, W = lv.shape
    comp, _ = label(floor & ~wall & ~(lv > 0), structure=np.ones((3, 3)))
    sizes = np.bincount(comp.ravel()); sizes[0] = 0
    main = comp == sizes.argmax()                                   # the open platform
    scene['openings'] = []
    geo = {}
    for v in range(1, scene['n_vces'] + 1):
        ys, xs = np.nonzero(lv == v)
        c = np.array([xs.mean(), ys.mean()])
        evals, evecs = np.linalg.eigh(np.cov(np.vstack((xs - c[0], ys - c[1]))))
        u = evecs[:, 1]
        ang = np.degrees(np.arctan2(u[1], u[0])) % 180
        if min(ang, 180 - ang) < 8 or evals[1] < 1.6 * evals[0]:    # near-axis-aligned or near-square: use the raster axes
            u = np.array([1.0, 0.0])
        elif abs(ang - 90) < 8:
            u = np.array([0.0, 1.0])
        nrm = np.array([-u[1], u[0]])
        y0, y1 = max(0, ys.min() - 60), min(H, ys.max() + 61)
        x0, x1 = max(0, xs.min() - 60), min(W, xs.max() + 61)
        sl = (slice(y0, y1), slice(x0, x1))
        Y, X = np.mgrid[y0:y1, x0:x1]
        own = lv[sl] == v
        other_vce = (lv[sl] > 0) & ~own
        ob = obs[sl] & ~own
        squarish = evals[1] < 1.6 * evals[0]
        cands = []
        for ai, ax in enumerate([u, nrm] if squarish else [u]):
            pr = np.array([-ax[1], ax[0]])
            P = (X - c[0]) * ax[0] + (Y - c[1]) * ax[1]
            L = (X - c[0]) * pr[0] + (Y - c[1]) * pr[1]
            pmin, pmax = P[own].min(), P[own].max()
            halfw = np.abs(L[own]).max()
            score = {}
            for s, end in ((-1, pmin), (1, pmax)):
                d = s * (P - end)
                near = (d > 0.5) & (d <= 3.5) & (np.abs(L) <= halfw)
                frac = float(ob[near].mean()) if near.any() else 0.0
                land = int(ob[(d > 0.5) & (d <= 30) & (np.abs(L) > halfw - 0.5) & (np.abs(L) <= halfw + 4.5)].sum())
                score[s] = (frac, land)
            if abs(score[-1][0] - score[1][0]) >= 0.2:
                pref = -1 if score[-1][0] < score[1][0] else 1
            elif score[-1][1] != score[1][1]:
                pref = -1 if score[-1][1] > score[1][1] else 1
            else:
                pref = -1
            for rank, s in enumerate((pref, -pref)):
                end = pmax if s == 1 else pmin
                d = s * (P - end)
                corridor = (d > 0.5) & (np.abs(L) <= halfw)
                reach = None
                for k in range(1, 45):
                    slab = corridor & (d > k - 0.5) & (d <= k + 0.5)
                    if slab.any() and main[sl][slab].any():
                        reach = k
                        break
                if reach is None:
                    continue
                cells = corridor & (d <= reach + 0.5) & floor[sl] & ~other_vce   # never carve off the platform or into another VCE
                if any((corridor & (d > k - 0.5) & (d <= k + 0.5) & cells).sum() < 3 for k in range(1, reach + 1)):
                    continue                                          # the passage would be cut by another VCE / the platform edge
                cost = int((wall[sl] & cells).sum())
                if cost > 0 and not OPEN_BLOCKED_VCE_MOUTHS:
                    continue
                cands.append((cost, ai, rank, s, ax, pr, pmin, pmax, halfw, cells, reach))
        if not cands:
            print(f"  warning: VCE {v} ({scene['vce_info'][v]['name'] or 'unnamed'}) cannot be reached from the platform - it is left closed")
            geo[v] = {'entry': (ys[:1], xs[:1]), 'exit_mask': np.zeros((H, W), bool), 'src': (ys[:0], xs[:0], xs[:0].astype(float)),
                      'axis': u, 'side': -1, 'cx': float(c[0]), 'cy': float(c[1]), 'opened': False, 'blocked': True}
            continue
        cost, ai, rank, s, ax, pr, pmin, pmax, halfw, cells, reach = min(cands, key=lambda t: t[:3])
        if cost > 0:                                                   # clear the corridor through the walls
            wall[sl][cells] = False
            obs[sl][cells] = False
            end = pmax if s == 1 else pmin
            e0, e1 = end, end + s * (reach + 0.5)
            scene['openings'].append(np.array([c + p * ax + l * pr for p, l in
                                               ((e0, -halfw - 0.5), (e1, -halfw - 0.5), (e1, halfw + 0.5), (e0, halfw + 0.5))]))
        P = (X - c[0]) * ax[0] + (Y - c[1]) * ax[1]
        L = (X - c[0]) * pr[0] + (Y - c[1]) * pr[1]
        end, far = (pmin, pmax) if s == -1 else (pmax, pmin)
        d = s * (P - end)
        walkable = ~wall[sl] & ~(lv[sl] > 0)
        entry = own & (d >= -1.5)
        exit_local = own & (np.abs(P - far) <= 1.5)
        src = walkable & floor[sl] & (d > 0.5) & (d <= 16) & (np.abs(L) <= halfw)   # model keeps the band that clears the mouth
        exit_mask = np.zeros((H, W), dtype=bool)
        exit_mask[sl] = exit_local
        geo[v] = {'entry': (Y[entry], X[entry]), 'exit_mask': exit_mask, 'src': (Y[src], X[src], d[src]),
                  'axis': ax, 'side': s, 'cx': float(c[0]), 'cy': float(c[1]), 'opened': cost > 0, 'blocked': False}
    return geo


def build_routing_fields(scene, geo):
    lv, wall, n = scene['labeled_vces'], scene['wall_mask'], scene['n_vces']
    entry_pixels = {v: geo[v]['entry'] for v in geo}
    graph, idx, node = build_walk_graph(wall, lv, entry_pixels)
    graph_t = graph.T.tocsr()
    entry_fields, internal = {}, {}
    for v in range(1, n + 1):
        ys, xs = entry_pixels[v]
        dist = dijkstra(graph_t, directed=True, indices=idx[ys, xs], min_only=True)
        f = np.full(lv.shape, np.inf, dtype=np.float32)
        f[node] = dist
        entry_fields[v] = f
        d = distance_transform_edt(~geo[v]['exit_mask']).astype(np.float32)
        d[lv != v] = np.inf
        internal[v] = d
    comp, _ = label(node & scene['floor'], structure=np.ones((3, 3)))
    sizes = np.bincount(comp.ravel()); sizes[0] = 0
    for v in range(1, n + 1):                         # a mouth that cannot reach the open platform = closed VCE
        reach = int((np.isfinite(entry_fields[v]) & scene['floor']).sum())
        if not geo[v].get('blocked') and reach < 0.5 * sizes.max():
            geo[v]['blocked'] = True
            print(f"  warning: VCE {v} ({scene['vce_info'][v]['name'] or 'unnamed'}) is sealed off from the platform - it is left closed")
        if geo[v].get('blocked'):
            entry_fields[v][:] = np.inf
    order = sorted((v for v in geo if not geo[v].get('blocked')), key=lambda v: geo[v]['cx'])
    right_ids = set(order[-2:])                       # the two easternmost usable VCEs get the 'eastern preference'
    return {'entry_fields': entry_fields, 'internal': internal, 'right_ids': right_ids,
            'graph_t': graph_t, 'idx': idx, 'node': node}


def combine_platform_field(entry_fields, right_ids, bias):
    best = None
    for v, f in entry_fields.items():
        g = f + (0.0 if v in right_ids else float(bias))
        best = g if best is None else np.minimum(best, g)
    return best


def door_field(routing, pixels_yx):
    """Walking distance (px) from every platform pixel to the nearest of the given door pixels."""
    ys, xs = pixels_yx
    dist = dijkstra(routing['graph_t'], directed=True, indices=routing['idx'][ys, xs], min_only=True)
    f = np.full(routing['node'].shape, np.inf, dtype=np.float32)
    f[routing['node']] = dist
    return f



# ==========================================
# 3. TRAINS AND DOORS  (NJ Transit MultiLevel cars along the platform edge)
# ==========================================
EDGE_TOL_PX = 8          # how far (px) the platform edge may wander and still count as 'straight' track side
TRAIN_END_CLEAR_FT = 4.0 # clearance between the train's east end and the end of the straight edge
BOARD_DEPTH_PX = 5       # depth of the boarding area in front of a door (departing riders board on entering it)


def edge_profiles(floor):
    """Row of the first floor pixel seen from the north edge (top) and from the south edge (bottom), per column."""
    H, W = floor.shape
    cols = np.where(floor.any(axis=0))[0]
    top = np.full(W, np.nan)
    bot = np.full(W, np.nan)
    top[cols] = floor[:, cols].argmax(axis=0)
    bot[cols] = H - 1 - floor[::-1, cols].argmax(axis=0)
    return {'N': top, 'S': bot}


def place_trains(scene, n_cars, berth_ft):
    """Lay out one train on the north track and one on the south track of the platform.
    Cars are CAR_LENGTH_FT apart (couplers touching), the east end of each train sits berth_ft west of the end of the
    straight stretch of platform edge. Every car gets a door at each DOOR_POSITIONS_FT; doors that have no
    platform in front of them are dropped."""
    floor = scene['floor']
    walk_ok = floor & ~scene['wall_mask'] & ~(scene['labeled_vces'] > 0)
    H, W = floor.shape
    prof = edge_profiles(floor)
    comp, _ = label(walk_ok, structure=np.ones((3, 3)))
    sizes = np.bincount(comp.ravel()); sizes[0] = 0
    main = comp == sizes.argmax()                                      # the open platform
    pitch = CAR_LENGTH_FT * PX_PER_FT
    gap = CAR_COUPLER_GAP_FT * PX_PER_FT
    depth = 2
    layout = {'trains': {}, 'cars': [], 'doors': []}
    for t, key in ((1, 'N'), (2, 'S')):
        out = -1 if key == 'N' else 1
        layout['trains'][t] = {'side': key, 'cars': [], 'requested': n_cars}
        run = _longest_run(prof[key], tol=EDGE_TOL_PX)
        if run is None:
            continue
        a, b = run
        east = (b + 1) - TRAIN_END_CLEAR_FT * PX_PER_FT - berth_ft * PX_PER_FT
        for k in range(n_cars):
            x_e = east - k * pitch
            x_w = x_e - pitch
            if x_w < a - 0.5:
                break                                                  # no room for another car on the straight edge
            span = prof[key][int(np.ceil(x_w)):int(np.floor(x_e)) + 1]
            span = span[~np.isnan(span)]
            if len(span) == 0:
                continue
            edge_row = span.min() if out < 0 else span.max()           # most protruding edge under this car
            edge = edge_row + 0.5 * out
            inner = edge + out * CAR_PLATFORM_GAP_FT * PX_PER_FT       # car face nearest the platform
            outer = inner + out * CAR_WIDTH_FT * PX_PER_FT
            xa, xb = x_w + gap / 2, x_e - gap / 2
            car = {'id': len(layout['cars']), 'train': t, 'index': k, 'x_w': x_w, 'x_e': x_e,
                   'rect': np.array([[xa, inner], [xb, inner], [xb, outer], [xa, outer]]), 'doors': []}
            for p_ft in DOOR_POSITIONS_FT:
                xd = x_w + p_ft * PX_PER_FT
                half = DOOR_WIDTH_FT * PX_PER_FT / 2
                pix, board = [], []
                bhalf = half * 1.5                                     # the boarding area is a little wider than the door
                for c in range(int(np.ceil(xd - bhalf)), int(np.floor(xd + bhalf)) + 1):
                    if not (0 <= c < W) or np.isnan(prof[key][c]):
                        continue
                    for j in range(1, BOARD_DEPTH_PX + 1):
                        r = int(prof[key][c]) - out * j                # inward from the edge
                        if 0 <= r < H and walk_ok[r, c]:
                            board.append((r, c))
                            if j <= depth and abs(c - xd) <= half:
                                pix.append((r, c))
                if not pix:
                    continue
                pix, board = np.array(pix), np.array(board)
                # only keep doors that open onto real platform: enough walkable depth in front of them, connected to the rest
                clear_depth = []
                for c in sorted(set(pix[:, 1].tolist())):
                    n = 0
                    while n < 40 and 0 <= int(prof[key][c]) - out * (n + 1) < H and walk_ok[int(prof[key][c]) - out * (n + 1), c]:
                        n += 1
                    clear_depth.append(n)
                if np.median(clear_depth) < MIN_DOOR_DEPTH_PX or main[pix[:, 0], pix[:, 1]].mean() < 0.5:
                    continue
                door = {'id': len(layout['doors']), 'car': car['id'], 'train': t, 'pixels': pix, 'board': board,
                        'center': (int(round(pix[:, 0].mean())), int(round(pix[:, 1].mean()))),
                        'rect': np.array([[xd - half, inner], [xd + half, inner],
                                          [xd + half, inner + out * 2.5], [xd - half, inner + out * 2.5]])}
                layout['doors'].append(door)
                car['doors'].append(door['id'])
            layout['cars'].append(car)
            layout['trains'][t]['cars'].append(car['id'])
    return layout



# ==========================================
# 4. AGENT SYSTEM
# ==========================================
NEIGHBOR_STEPS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


class Agent:
    def __init__(self, pos, kind='alight', target=None):
        self.pos = pos
        self.state = 'platform'
        self.current_vce = None
        self.move_timer = 0.0
        self.kind = kind          # 'alight' = train door -> stairs/escalator ; 'depart' = stairs/escalator mouth -> train door
        self.target = target      # departing riders: the id of the door they are walking to
        self.best_field = float('inf')   # closest to their goal they have been so far (for the patience rule)
        self.stall = 0                   # moves since they last got closer


class PedestrianModel:
    def __init__(self, scene, geo, routing, layout, door_fields, platform_field, params):
        self.grid_shape = scene['obstacle_mask'].shape
        self.obstacle_mask = scene['obstacle_mask']
        self.wall_mask = scene['wall_mask']
        self.labeled_vces = scene['labeled_vces']
        self.platform_field = platform_field
        self.vce_fields = routing['internal']
        self.door_fields = door_fields

        # Zone around every usable stair/escalator mouth where riders funnel in closer together (see MOUTH_SPACING_PX)
        mouth = np.zeros(self.grid_shape, dtype=np.uint8)
        for v, g in geo.items():
            if not g.get('blocked'):
                mouth[g['entry'][0], g['entry'][1]] = 1
        k = 2 * MOUTH_ZONE_PX + 1
        self.mouth_zone = cv2.dilate(mouth, np.ones((k, k), np.uint8)) > 0

        self.agents = []
        self.vce_counts = {i: 0 for i in range(1, scene['n_vces'] + 1)}

        # Footprint bookkeeping: boolean grid of agent CENTER pixels (padded so window slices stay in bounds)
        self.S = params['agent_px']
        self.pad = self.S + CROWDING_BUFFER_PX + 1
        # Two layers: agents on the platform and agents inside a VCE never see each other. The VCE walls are only
        # a few pixels thick, so a shared grid let platform agents standing just outside a wall block the
        # cells inside it (this is what froze the front of the easternmost VCE).
        shape = (self.grid_shape[0] + 2 * self.pad, self.grid_shape[1] + 2 * self.pad)
        self.centers = {'platform': np.zeros(shape, dtype=bool), 'vce': np.zeros(shape, dtype=bool)}
        self.occ = {}                       # (y, x) -> agent, for the platform layer (used to let opposing riders swap)

        self.dt = TIME_STEP
        self.sim_time = 0.0
        self.spawn_rate = params['spawn_rate']
        self.crowding_penalty = params['crowding']
        self.arrival = {1: params['arrival1'], 2: params['arrival2']}
        self.boarding_delay = params['boarding_delay']
        self.alighted = 0
        self.boarded = 0

        # ---- doors, cars, trains ----
        self.doors = {}
        for d in layout['doors']:
            self.doors[d['id']] = {'train': d['train'], 'car': d['car'], 'pixels': d['pixels'], 'center': d['center'],
                                   'queue': 0, 'acc': 0.0, 'zone': None}
        self.cars = {c['id']: c for c in layout['cars']}
        # Boarding riders keep clear of a door that is still letting people off: a small zone in front of it is off limits
        # to them until its alighting queue is empty (otherwise they block the exit they are waiting for).
        self.keep_clear = np.zeros(self.grid_shape, dtype=bool)
        Hh, Ww = self.grid_shape
        for did, d in self.doors.items():
            ys, xs = d['pixels'][:, 0], d['pixels'][:, 1]
            d['zone'] = (slice(max(0, ys.min() - KEEP_CLEAR_PX), min(Hh, ys.max() + KEEP_CLEAR_PX + 1)),
                         slice(max(0, xs.min() - KEEP_CLEAR_PX), min(Ww, xs.max() + KEEP_CLEAR_PX + 1)))
        per_car = {1: int(params['load1']), 2: int(params['load2'])}
        dep_per_car = int(params['dep_per_car'])
        self.trains = {}
        for t in (1, 2):
            usable = [c for c in layout['trains'][t]['cars'] if self.cars[c]['doors']]
            door_ids = [d for c in usable for d in self.cars[c]['doors']]
            self.trains[t] = {'cars': usable, 'doors': door_ids, 'requested': layout['trains'][t]['requested'],
                              'per_car': per_car[t], 'alight_total': per_car[t] * len(usable), 'alighted': 0,
                              'assigned': False, 'dep_total': dep_per_car * len(usable),
                              'dep_left': dep_per_car * len(usable), 'dep_acc': 0.0, 'boarded': 0}
        self.total_pax = sum(t['alight_total'] for t in self.trains.values())
        self.total_dep = sum(t['dep_total'] for t in self.trains.values())

        # where departing riders step out of the stairs/escalators (weighted by the width of the mouth)
        # (a band starting just beyond the footprint of anyone entering the mouth, so they don't block the entry)
        self.dep_sources = []
        for v, g in geo.items():
            if g.get('blocked') or len(g['src'][0]) == 0:
                continue
            ys, xs, ds = g['src']
            sel = (ds >= self.S + 1) & (ds <= self.S + 4)
            if not sel.any():
                sel = ds >= self.S + 1
            if sel.any():
                self.dep_sources.append((v, ys[sel], xs[sel]))
        w = np.array([len(s[1]) for s in self.dep_sources], dtype=float)
        self.dep_weights = w / w.sum() if len(w) else w

    # ---- footprint helpers ----
    def _window(self, layer, y, x, r):
        p = self.pad
        return self.centers[layer][y + p - r: y + p + r + 1, x + p - r: x + p + r + 1]

    def _set_center(self, layer, y, x, val):
        self.centers[layer][y + self.pad, x + self.pad] = val

    def _is_free(self, layer, y, x):
        # Two S x S squares overlap iff centers are within S-1 pixels on both axes
        return not self._window(layer, y, x, self.S - 1).any()

    def _crowding(self, layer, y, x):
        return int(self._window(layer, y, x, self.S + CROWDING_BUFFER_PX).sum())

    def _lift(self, layer, y, x):
        self._set_center(layer, y, x, False)
        if layer == 'platform':
            self.occ.pop((y, x), None)

    def _place(self, agent, layer, y, x):
        self._set_center(layer, y, x, True)
        if layer == 'platform':
            self.occ[(y, x)] = agent

    def _swap_partner(self, agent, target_field, y, x, here):
        """Two riders who block each other head-on and would BOTH get closer to where they are going by trading
        places do so (people step round one another). Exchanging two equal footprints keeps every other rider's
        spacing intact. Only done when exactly one rider is in the way and both gain, so it never makes a queue
        jump the line: riders walking the same way never both gain."""
        H, W = self.grid_shape
        r = self.S - 1
        best = None
        for dy, dx in NEIGHBOR_STEPS:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < H and 0 <= nx < W) or self.wall_mask[ny, nx] or self.labeled_vces[ny, nx] > 0:
                continue
            if dy and dx and (self.wall_mask[ny, x] or self.wall_mask[y, nx]):
                continue
            win = self._window('platform', ny, nx, r)
            if win.sum() != 1:
                continue
            wy, wx = np.nonzero(win)
            by, bx = ny - r + int(wy[0]), nx - r + int(wx[0])
            other = self.occ.get((by, bx))
            if other is None or other.state != 'platform':
                continue
            if agent.kind == 'depart' and self.keep_clear[by, bx] and not self.keep_clear[y, x]:
                continue
            if other.kind == 'depart' and self.keep_clear[y, x] and not self.keep_clear[by, bx]:
                continue
            pf = self.door_fields[other.target] if other.kind == 'depart' else self.platform_field
            mover_gain = here - target_field[by, bx]
            partner_gain = pf[by, bx] - pf[y, x]
            if mover_gain >= 1.0 and partner_gain >= 1.0 and (best is None or mover_gain > best[0]):
                best = (mover_gain, other, by, bx)
        return best

    # ---- stats for the GUI ----
    def train_remaining(self, t):
        return self.trains[t]['alight_total'] - self.trains[t]['alighted']

    def in_vce_counts(self):
        counts = {i: 0 for i in self.vce_counts}
        for a in self.agents:
            if a.state == 'vce':
                counts[a.current_vce] += 1
        return counts

    # ---- alighting riders: free choice of door within their car ----
    def _choice_doors(self, car_id):
        t = self.cars[car_id]['train']
        k = self.cars[car_id]['index']
        doors = []
        for c in self.trains[t]['cars']:
            if abs(self.cars[c]['index'] - k) <= DOOR_CHOICE_RANGE_CARS:
                doors += self.cars[c]['doors']
        return doors

    def _assign_alighting(self, t):
        """Every rider of every car picks a door when the train arrives: walking distance from the door to the
        nearest (preferred) stairs/escalator, plus a penalty for the riders already queueing at that door, plus noise.
        Riders are processed one by one, so queues build up as the car fills its doors - the door nearer the stairs
        gets more riders, but not all of them."""
        tr = self.trains[t]
        rate = max(self.spawn_rate, 0.05)
        queue_cost_ft = DOOR_QUEUE_AWARENESS * (PLATFORM_SPEED / PX_PER_FT) / rate   # ft of walking ~ 1 queued rider's wait
        for cid in tr['cars']:
            doors = [d for d in self._choice_doors(cid)
                     if np.isfinite(self.platform_field[self.doors[d]['pixels'][:, 0], self.doors[d]['pixels'][:, 1]].min())]
            if not doors:
                tr['alight_total'] -= tr['per_car']                    # no door of this car can reach a stair/escalator
                continue
            walk_ft = np.array([self.platform_field[self.doors[d]['pixels'][:, 0], self.doors[d]['pixels'][:, 1]].min()
                                for d in doors]) / PX_PER_FT
            for _ in range(tr['per_car']):
                queue = np.array([self.doors[d]['queue'] for d in doors], dtype=float)
                cost = (DOOR_PREF_WEIGHT * walk_ft + queue_cost_ft * queue
                        + np.random.logistic(0.0, DOOR_NOISE_FT, size=len(doors)))
                self.doors[doors[int(np.argmin(cost))]]['queue'] += 1
        self.total_pax = sum(x['alight_total'] for x in self.trains.values())
        for d in tr['doors']:
            if self.doors[d]['queue'] > 0:
                self.keep_clear[self.doors[d]['zone']] = True

    # ---- departing riders: step out of a stairs/escalator mouth and pick a door to board ----
    def _spawn_departing(self, t):
        tr = self.trains[t]
        if not self.dep_sources or not tr['doors']:
            return False
        k = np.random.choice(len(self.dep_sources), p=self.dep_weights)
        _, ys, xs = self.dep_sources[k]
        for _ in range(3):
            j = np.random.randint(len(ys))
            y, x = int(ys[j]), int(xs[j])
            if self._is_free('platform', y, x) and self._crowding('platform', y, x) <= DEPARTING_MAX_CROWD:
                break
        else:
            return False
        best, best_cost = None, np.inf
        r = min(7, self.pad)
        for d in tr['doors']:
            if self.doors[d]['queue'] > 0:
                continue                                             # let people off first: this door is still in use
            f = self.door_fields[d][y, x]
            if not np.isfinite(f):
                continue
            cy, cx = self.doors[d]['center']
            cost = (f / PX_PER_FT + CAR_CROWD_WEIGHT_FT * int(self._window('platform', cy, cx, r).sum())
                    + np.random.logistic(0.0, CAR_NOISE_FT))
            if cost < best_cost:
                best, best_cost = d, cost
        if best is None:
            return False
        a = Agent([y, x], kind='depart', target=best)
        self.agents.append(a)
        self._place(a, 'platform', y, x)
        return True

    def _board(self, agent):
        self.boarded += 1
        self.trains[self.doors[agent.target]['train']]['boarded'] += 1

    def step(self):
        self.sim_time += self.dt

        # Trains arrive: riders choose their doors
        for t, tr in self.trains.items():
            if not tr['assigned'] and self.sim_time >= self.arrival[t]:
                self._assign_alighting(t)
                tr['assigned'] = True

        # Alighting riders leave the train through their doors (rate-limited per door)
        for door_id, d in self.doors.items():
            if d['queue'] > 0:
                d['acc'] += self.dt * self.spawn_rate
                while d['acc'] >= 1.0 and d['queue'] > 0:
                    spawn_pos = tuple(int(v) for v in d['pixels'][np.random.randint(len(d['pixels']))])
                    if self._is_free('platform', *spawn_pos):
                        a = Agent(list(spawn_pos))
                        self.agents.append(a)
                        self._place(a, 'platform', *spawn_pos)
                        d['queue'] -= 1
                        self.alighted += 1
                        self.trains[d['train']]['alighted'] += 1
                        if d['queue'] == 0:                                 # door is clear: boarding riders may use it
                            self.keep_clear[d['zone']] = False
                    d['acc'] -= 1.0
            else:
                d['acc'] = 0.0

        # Departing riders come off the stairs/escalators once boarding opens
        for t, tr in self.trains.items():
            if tr['assigned'] and tr['dep_left'] > 0 and self.sim_time >= self.arrival[t] + self.boarding_delay:
                tr['dep_acc'] += self.dt * DEPART_RATE
                while tr['dep_acc'] >= 1.0 and tr['dep_left'] > 0:
                    if self._spawn_departing(t):
                        tr['dep_left'] -= 1
                    tr['dep_acc'] -= 1.0

        # Movement
        np.random.shuffle(self.agents)
        surviving_agents = []

        for agent in self.agents:
            y, x = agent.pos
            speed_limit = PLATFORM_SPEED if agent.state == 'platform' else VCE_SPEED
            agent.move_timer += self.dt * speed_limit

            if agent.move_timer < 1.0:
                surviving_agents.append(agent)
                continue

            agent.move_timer -= 1.0
            departing = agent.kind == 'depart'

            if departing:
                target_field = self.door_fields[agent.target]
                if target_field[y, x] == 0:                                # standing at the door: board
                    self._lift('platform', y, x)
                    self._board(agent)
                    continue
            else:
                vce_id_here = self.labeled_vces[y, x]
                if agent.state == 'platform' and vce_id_here > 0:
                    agent.state = 'vce'
                    agent.current_vce = vce_id_here
                    self._lift('platform', y, x)                           # hand over to the VCE layer
                    self._place(agent, 'vce', y, x)

                if agent.state == 'vce':
                    if self.vce_fields[agent.current_vce][y, x] == 0:
                        self._lift('vce', y, x)
                        self.vce_counts[agent.current_vce] += 1
                        continue

                target_field = self.platform_field if agent.state == 'platform' else self.vce_fields[agent.current_vce]

            best_pos = agent.pos
            best_score = float('inf')
            best_free_field = float('inf')

            # Patience: a rider who is not getting closer gradually stops avoiding crowded cells and pushes forward
            here = target_field[y, x]
            if here < agent.best_field - 0.5:
                agent.best_field = here
                agent.stall = 0
            else:
                agent.stall += 1
            crowd_w = self.crowding_penalty * (max(0.0, 1.0 - agent.stall / PATIENCE_TICKS) if PATIENCE_TICKS > 0 else 1.0)

            # ...and one who stays stuck accepts less personal space (crowds compress under pressure): the required
            # separation shrinks by 1 px for every further SQUEEZE_TICKS without progress
            r_eff = self.S - 1
            if PATIENCE_TICKS > 0 and SQUEEZE_TICKS > 0:
                r_eff = max(1, r_eff - max(0, agent.stall - PATIENCE_TICKS) // SQUEEZE_TICKS)

            # Lift this agent off its grid so it doesn't block or crowd itself
            layer = agent.state
            self._lift(layer, y, x)

            steps = NEIGHBOR_STEPS[:]
            random.shuffle(steps)                                          # random tie-breaking
            for dy, dx in steps:
                ny, nx = y + dy, x + dx
                if 0 <= ny < self.grid_shape[0] and 0 <= nx < self.grid_shape[1]:
                    if self.wall_mask[ny, nx]:
                        continue
                    # no cutting diagonally through the corner of a wall
                    if dy and dx and (self.wall_mask[ny, x] or self.wall_mask[y, nx]):
                        continue
                    if departing and (self.labeled_vces[ny, nx] > 0 or (self.keep_clear[ny, nx] and not self.keep_clear[y, x])):
                        continue                                           # boarders never enter a VCE or a door still in use
                    entering = layer == 'platform' and not departing and self.labeled_vces[ny, nx] > 0
                    # Stepping ONTO a stair/escalator only needs room on the stair itself: people waiting on the platform
                    # beside the mouth don't stand on the first step (same layering idea as the platform/VCE split above).
                    # Next to a mouth riders also funnel in closer together than they would on open platform.
                    r_cell = min(r_eff, MOUTH_SPACING_PX) if (MOUTH_SPACING_PX is not None and layer == 'platform' and self.mouth_zone[ny, nx]) else r_eff
                    if entering and not STAIR_ENTRY_NEEDS_PLATFORM_ROOM:
                        cell_ok = self._is_free('vce', ny, nx)
                    elif entering:
                        cell_ok = not self._window(layer, ny, nx, r_cell).any() and self._is_free('vce', ny, nx)
                    else:
                        cell_ok = not self._window(layer, ny, nx, r_cell).any()
                    if cell_ok:
                        tf = target_field[ny, nx]
                        best_free_field = min(best_free_field, tf)
                        score = tf + self._crowding(layer, ny, nx) * crowd_w
                        if score < best_score:
                            best_score = score
                            best_pos = [ny, nx]

            # Boxed in by someone walking the other way? Swap places with them.
            if SWAP_OPPOSING_RIDERS and layer == 'platform' and agent.stall >= 5 and best_free_field >= here - 0.5:
                sw = self._swap_partner(agent, target_field, y, x, here)
                if sw is not None:
                    _, other, by, bx = sw
                    other.pos = [y, x]
                    agent.pos = [by, bx]
                    self.occ[(y, x)] = other
                    self.occ[(by, bx)] = agent
                    self._set_center('platform', y, x, True)               # both cells stay occupied
                    agent.stall = 0
                    surviving_agents.append(agent)
                    continue

            if departing:
                if target_field[best_pos[0], best_pos[1]] == 0:            # board the instant the door is reached
                    self._board(agent)
                    continue
            elif agent.state == 'vce' and self.vce_fields[agent.current_vce][best_pos[0], best_pos[1]] == 0:
                # Despawn the instant the agent steps onto the exit line (no extra wait for the next tick)
                self.vce_counts[agent.current_vce] += 1
                continue

            if not departing:
                new_vce = self.labeled_vces[best_pos[0], best_pos[1]]
                if layer == 'platform' and new_vce > 0:                    # commit to the VCE the moment it steps in
                    agent.state = 'vce'
                    agent.current_vce = new_vce
                    layer = 'vce'
            self._place(agent, layer, best_pos[0], best_pos[1])
            agent.pos = best_pos
            surviving_agents.append(agent)

        self.agents = surviving_agents


# ==========================================
# 5. WORLD BUILDING
# ==========================================
def build_platform(station, pid):
    """Everything that depends only on the platform: raster masks, VCE mouths, walking-distance fields."""
    scene = build_scene(station, pid)
    geo = analyze_vces(scene)
    routing = build_routing_fields(scene, geo)
    return scene, geo, routing


def build_door_fields(routing, layout):
    """Walking distance to each door's boarding area (used by departing riders)."""
    return {d['id']: door_field(routing, (d['board'][:, 0], d['board'][:, 1])) for d in layout['doors']}


def default_params():
    return dict(spawn_rate=SPAWN_RATE_PER_SECOND, crowding=CROWDING_PENALTY,
                agent_px=max(1, int(round(AGENT_SIZE_FT * PX_PER_FT))),
                load1=PAXPERDOOR * DOORS_PER_CAR, load2=PAXPERDOOR * DOORS_PER_CAR,
                arrival1=0, arrival2=0, dep_per_car=DEPARTING_PER_DOOR * DOORS_PER_CAR,
                boarding_delay=BOARDING_DELAY)


def run_headless(platform=PLATFORM, seconds=900.0, cars=CARS_PER_TRAIN, berth_ft=0.0, seed=None, report=30.0, **overrides):
    """Runs the model without the GUI and prints a short timeline - handy for batch experiments."""
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    station = load_station()
    scene, geo, routing = build_platform(station, str(platform))
    layout = place_trains(scene, cars, berth_ft)
    params = {**default_params(), **overrides}
    fields = build_door_fields(routing, layout) if params['dep_per_car'] > 0 else {}
    field = combine_platform_field(routing['entry_fields'], routing['right_ids'], RIGHT_VCE_PREFERENCE_BIAS)
    m = PedestrianModel(scene, geo, routing, layout, fields, field, params)
    print(f"Platform {platform}: {len(m.trains[1]['cars'])}+{len(m.trains[2]['cars'])} cars, {len(m.doors)} doors, "
          f"{m.total_pax} alighting / {m.total_dep} departing passengers")
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
    return m


# ==========================================
# 6. DASHBOARD GUI
# ==========================================
class SimulationGUI:
    SLIDER_ROWS = [0.535, 0.488, 0.441, 0.394, 0.347]      # y (figure fraction) of the five slider rows
    VCE_PER_ROW = 6

    def __init__(self, platform=PLATFORM):
        print("Loading station geometry...")
        self.station = load_station()
        self.pid = None
        self.scene = self.geo = self.routing = self.layout = None
        self.door_fields = {}
        self.scene_cache = {}
        self.layout_cache = {}
        self.applied_bias = None
        self.platform_field = None
        self.model = None
        self.running = False
        self.paused = False
        self.scene_artists, self.layout_artists = [], []
        self.view_mode = 'image'
        self.mask_im = None
        self.door_scatter = None
        self.view_W, self.view_yc = 1000, 50

        self._build_figure(platform)
        self.reset()
        self.ani = animation.FuncAnimation(
            self.fig, self.update, frames=itertools.count(),
            interval=ANIMATION_INTERVAL, blit=False, cache_frame_data=False)

    # ---------- layout helpers ----------
    def _card_axes(self, rect):
        ax = self.fig.add_axes(rect)
        ax.set_facecolor('white')
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor(CARD_BORDER)
        return ax

    def _slider(self, col, row, title, vmin, vmax, step, init, fmt):
        x = 0.03 + col * 0.32
        y = self.SLIDER_ROWS[row]
        self.fig.text(x, y + 0.019, title, fontsize=9, color=MUTED, va='bottom')
        ax = self.fig.add_axes([x, y, 0.235, 0.011])
        s = Slider(ax, '', vmin, vmax, valinit=init, valstep=step, valfmt=fmt, color=ACCENT,
                   track_color='#e5e7eb', initcolor='none',
                   handle_style=dict(facecolor='white', edgecolor=ACCENT, size=9))
        s.valtext.set_fontsize(9)
        s.valtext.set_color(FAINT)
        for sp in ax.spines.values():
            sp.set_visible(False)
        return s

    def _button(self, rect, text, callback):
        ax = self.fig.add_axes(rect)
        b = Button(ax, text, color='white', hovercolor='#f0f0f0')
        b.label.set_fontsize(10)
        b.label.set_color(TEXT)
        for s in ax.spines.values():
            s.set_edgecolor('#cccccc')
        b.on_clicked(callback)
        return b

    # ---------- figure ----------
    def _build_figure(self, platform):
        self.fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=BG)
        self.title = self.fig.text(0.03, 0.978, "", fontsize=16, fontweight='bold', color='#222222', va='top')

        # --- simulation canvas ---
        canvas_rect = [0.03, 0.80, 0.94, 0.14]
        self.ax = self.fig.add_axes(canvas_rect)
        self.ax.set_facecolor(CANVAS_BG)
        for s in self.ax.spines.values():
            s.set_edgecolor(BORDER)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.box_aspect = canvas_rect[3] * FIG_H / (canvas_rect[2] * FIG_W)   # axes height / width in inches

        # Passengers, drawn at their true footprint: alighting (green) and departing (blue)
        self.pax = EllipseCollection(widths=[1], heights=[1], angles=[0], units='xy',
                                     offsets=np.zeros((1, 2)), offset_transform=self.ax.transData,
                                     facecolors=[PAX_RGBA], edgecolors='#0f5132', linewidths=0.3, zorder=5)
        self.dep = EllipseCollection(widths=[1], heights=[1], angles=[0], units='xy',
                                     offsets=np.zeros((1, 2)), offset_transform=self.ax.transData,
                                     facecolors=[DEP_RGBA], edgecolors='#1e3a8a', linewidths=0.3, zorder=5.1)
        for c in (self.pax, self.dep):
            c.set_offsets(np.empty((0, 2)))
            self.ax.add_collection(c)

        # --- legend ---
        lax = self.fig.add_axes([0.03, 0.735, 0.94, 0.03])
        lax.axis('off')
        self.legend_dots = {}
        for i, (key, c, name) in enumerate([('door', DOOR_COLOR, 'Train doors'), ('car', CAR_EDGE, 'MultiLevel cars'),
                                            ('vce', IMG_VCE_SWATCH, 'VCEs'), ('pax', PAX_RGBA[:3], 'Alighting'),
                                            ('dep', DEP_RGBA[:3], 'Departing'),
                                            ('obs', IMG_OBS_SWATCH, 'Obstacles / boundary')]):
            x = 0.002 + i * 0.125
            self.legend_dots[key], = lax.plot([x], [0.5], 'o', ms=7, color=c, transform=lax.transAxes, clip_on=False)
            lax.text(x + 0.008, 0.5, name, transform=lax.transAxes, fontsize=9, color=TEXT, va='center')
        vax = self.fig.add_axes([0.83, 0.738, 0.14, 0.024])
        self.btn_view = Button(vax, "View: Image", color='white', hovercolor='#f0f0f0')
        self.btn_view.label.set_fontsize(9)
        self.btn_view.label.set_color(TEXT)
        for sp in vax.spines.values():
            sp.set_edgecolor('#cccccc')
        self.btn_view.on_clicked(self.on_toggle_view)

        # --- stat cards ---
        self.stat_texts = []
        labels = ["On platform", "Alighted", "Exited via VCEs", "Boarded", "Time"]
        gap = 0.012
        cw = (0.94 - (len(labels) - 1) * gap) / len(labels)
        for i, name in enumerate(labels):
            ax = self._card_axes([0.03 + i * (cw + gap), 0.665, cw, 0.055])
            ax.text(0.06, 0.70, name, fontsize=8, color=FAINT, transform=ax.transAxes, va='center')
            self.stat_texts.append(ax.text(0.06, 0.28, "0", fontsize=16, fontweight='bold',
                                           color=TEXT, transform=ax.transAxes, va='center'))

        # --- train boxes ---
        self.train_texts = {}
        bw = (0.94 - 0.012) / 2
        for i, (t, title) in enumerate([(1, "Train 1 (North)"), (2, "Train 2 (South)")]):
            ax = self._card_axes([0.03 + i * (bw + 0.012), 0.600, bw, 0.052])
            ax.add_patch(Rectangle((0, 0), 0.006, 1, transform=ax.transAxes, color=ACCENT, clip_on=False))
            ax.text(0.02, 0.70, title, fontsize=10, fontweight='bold', color=TEXT, transform=ax.transAxes, va='center')
            self.train_texts[t] = ax.text(0.02, 0.28, "", fontsize=9, color=TEXT, transform=ax.transAxes, va='center')

        # --- scroll for the canvas ---
        pax_ = self.fig.add_axes([0.03, 0.779, 0.94, 0.009])
        self.s_pan = Slider(pax_, '', 0.0, 1.0, valinit=0.0, color=ACCENT, track_color='#e5e7eb',
                            initcolor='none', handle_style=dict(facecolor='white', edgecolor=ACCENT, size=9))
        self.s_pan.valtext.set_visible(False)
        for sp in pax_.spines.values():
            sp.set_visible(False)

        # --- sliders (3-column grid) ---
        pc = DOORS_PER_CAR
        self.s_plat = self._slider(0, 0, "Platform (1-11)  - applies on Reset", 1, 11, 1, int(platform), '%d')
        self.s_cars = self._slider(1, 0, "Cars per train  - applies on Reset", 1, MAX_CARS, 1, CARS_PER_TRAIN, '%d')
        self.s_berth = self._slider(2, 0, "Train berth: ft west of the east end  - applies on Reset", 0, 400, 10, 0, '%d ft')
        self.s_load1 = self._slider(0, 1, "Train 1 alighting (pax per car)  - applies on Reset", 0, MAX_PAX_PER_DOOR * pc, 5,
                                    PAXPERDOOR * pc, '%d')
        self.s_load2 = self._slider(1, 1, "Train 2 alighting (pax per car)  - applies on Reset", 0, MAX_PAX_PER_DOOR * pc, 5,
                                    PAXPERDOOR * pc, '%d')
        self.s_spawn = self._slider(2, 1, "Spawn rate (pax/sec/door)", 0.1, MAX_SPAWN_RATE, 0.1, SPAWN_RATE_PER_SECOND, '%.1f')
        self.s_arr1 = self._slider(0, 2, "Train 1 arrival (sec)", 0, 300, 1, 0, '%d s')
        self.s_arr2 = self._slider(1, 2, "Train 2 arrival (sec)", 0, 300, 1, 0, '%d s')
        self.s_dep = self._slider(2, 2, "Departing pax per car (both trains)  - applies on Reset", 0,
                                  MAX_DEPARTING_PER_DOOR * pc, 5, DEPARTING_PER_DOOR * pc, '%d')
        self.s_board = self._slider(0, 3, "Boarding opens (sec after the train arrives)", 0, 300, 5, BOARDING_DELAY, '%d s')
        self.s_east = self._slider(1, 3, "Eastern preference (bias, px)", 0, 600, 25, RIGHT_VCE_PREFERENCE_BIAS, '%d px')
        self.s_crowd = self._slider(2, 3, "Crowding penalty", 0, 100, 5, CROWDING_PENALTY, '%d')
        self.s_size = self._slider(0, 4, "Agent size (ft)  - applies on Reset", 0.5, 4.0, 0.25, AGENT_SIZE_FT, '%.2f')
        self.s_zoom = self._slider(1, 4, "View zoom (x)", 1.0, 6.0, 0.5, DEFAULT_ZOOM, '%.1f x')
        self.s_zoom.on_changed(lambda _v: self.set_view())
        self.s_pan.on_changed(lambda _v: self.set_view())

        # --- buttons ---
        bw3 = (0.94 - 2 * 0.012) / 3
        self.btn_start = self._button([0.03, 0.290, bw3, 0.036], "Start", self.on_start)
        self.btn_pause = self._button([0.03 + bw3 + 0.012, 0.290, bw3, 0.036], "Pause", self.on_pause)
        self.btn_reset = self._button([0.03 + 2 * (bw3 + 0.012), 0.290, bw3, 0.036], "Reset", self.reset)

        # --- VCE cards (laid out per platform) ---
        self.fig.text(0.03, 0.262, "Vertical Circulation Elements", fontsize=11, fontweight='bold', color=TEXT, va='center')
        self.fig.text(0.97, 0.262, "(E) = eastern-preference VCE", fontsize=8, color=FAINT, va='center', ha='right')
        self.vce_cards = {}
        for i in range(1, MAX_VCE_CARDS + 1):
            ax = self._card_axes([0.03, 0.1, 0.1, 0.05])
            edge = Rectangle((0, 0), 0.012, 1, transform=ax.transAxes, color=BORDER, clip_on=False)
            ax.add_patch(edge)
            name = ax.text(0.06, 0.70, "", fontsize=9, fontweight='bold', color=TEXT, transform=ax.transAxes, va='center')
            detail = ax.text(0.06, 0.28, "", fontsize=8, color=MUTED, transform=ax.transAxes, va='center')
            ax.set_visible(False)
            self.vce_cards[i] = (ax, edge, name, detail)

    # ---------- drawing the station ----------
    @staticmethod
    def _clear(artists):
        for a in artists:
            try:
                a.remove()
            except Exception:
                pass
        artists.clear()

    def _apply_view_mode(self):
        show_masks = self.view_mode == 'masks'
        for a in self.scene_artists + self.layout_artists:
            if a is not self.mask_im and a is not self.door_scatter:
                a.set_visible(not show_masks)
        if self.mask_im is not None:
            self.mask_im.set_visible(show_masks)

    def _draw_scene(self):
        self._clear(self.scene_artists)
        sc, ax = self.scene, self.ax
        geom = sc['geom']
        H, W = sc['floor'].shape
        art = []

        # raster masks (shown in 'Masks' view): exactly what the agents treat as walls
        mv = np.empty((H, W, 3), dtype=np.uint8)
        mv[:] = hex_to_rgb(CANVAS_BG)
        mv[sc['obstacle_mask']] = hex_to_rgb(OBSTACLE_COLOR)
        mv[sc['wall_mask'] & ~sc['obstacle_mask']] = hex_to_rgb('#8a8a8a')
        mv[sc['labeled_vces'] > 0] = hex_to_rgb(VCE_COLOR)
        self.mask_base = mv
        self.mask_im = ax.imshow(mv, interpolation='nearest', aspect='auto', zorder=0, visible=False)
        art.append(self.mask_im)

        # the drawing (vector): floor from the raster so the U-shaped platform 1/2 is split correctly
        contours, _ = cv2.findContours(sc['floor'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        floor_polys = [c[:, 0, :].astype(float) for c in contours if len(c) >= 3]
        art.append(PolyCollection(floor_polys, facecolors=FLOOR_COLOR, edgecolors=FLOOR_EDGE, linewidths=0.6, zorder=1))
        if geom['enclosures']:
            art.append(PolyCollection(geom['enclosures'], facecolors='#d4d4d4', edgecolors='#8a8a8a', linewidths=0.4, zorder=2))
        if geom['columns']:
            art.append(PolyCollection(geom['columns'], facecolors='#444444', edgecolors='#444444', linewidths=0.3, zorder=3))
        if geom['elevators']:
            art.append(PolyCollection(geom['elevators'], facecolors=ELEVATOR_COLOR, edgecolors='#2b5fa8', linewidths=0.4, zorder=3))
        if geom['walls']:
            art.append(LineCollection(geom['walls'], colors='#555555', linewidths=0.6, zorder=3))
        if sc['openings']:                                   # where a drawn wall was opened so a stair/escalator is usable
            art.append(PolyCollection(sc['openings'], facecolors=FLOOR_COLOR, edgecolors='none', zorder=3.5))
        for kind, color in (('stair', STAIR_COLOR), ('escalator', ESCALATOR_COLOR), ('elevator', ELEVATOR_COLOR)):
            polys = [r for (vid, k, r) in geom['vces'] if k == kind and not self.geo[vid].get('blocked')]
            if polys:
                art.append(PolyCollection(polys, facecolors=color, edgecolors='#8a3a00', linewidths=0.4, zorder=4))
        closed = [r for (vid, k, r) in geom['vces'] if self.geo[vid].get('blocked')]
        if closed:
            art.append(PolyCollection(closed, facecolors='#bdbdbd', edgecolors='#777777', linewidths=0.4, zorder=4))
        for vce_id, kind, ring in geom['vces']:                # VCE numbers
            cx, ytop = ring[:, 0].mean(), ring[:, 1].min()
            art.append(ax.text(cx, ytop - 2, str(vce_id), color='#111111', fontsize=8, fontweight='bold',
                               ha='center', va='bottom', zorder=6,
                               bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85)))
        for a in art:
            if a.axes is None:                                # collections still need attaching; the image and texts are
                ax.add_collection(a)
        self.scene_artists = art
        rows = np.where(sc['floor'].any(axis=1))[0]
        self.view_W, self.view_yc = W, (rows.min() + rows.max()) / 2
        self._apply_view_mode()

    def _draw_layout(self):
        self._clear(self.layout_artists)
        lay, ax = self.layout, self.ax
        art = []
        if lay['cars']:
            art.append(PolyCollection([c['rect'] for c in lay['cars']], facecolors=CAR_COLOR, edgecolors=CAR_EDGE,
                                      linewidths=0.8, zorder=2))
        if lay['doors']:
            art.append(PolyCollection([d['rect'] for d in lay['doors']], facecolors=DOOR_COLOR, edgecolors='none', zorder=2.6))
        for a in art:
            ax.add_collection(a)
        # door dots (bigger while riders are still waiting inside, small once a door is clear)
        self.door_ids = [d['id'] for d in lay['doors']]
        dxy = np.array([[d['center'][1], d['center'][0]] for d in lay['doors']]) if self.door_ids else np.empty((0, 2))
        self.door_scatter = ax.scatter(dxy[:, 0], dxy[:, 1], s=14, c=DOOR_COLOR, linewidths=0, zorder=4.2)
        art.append(self.door_scatter)
        self.layout_artists = art
        mv = self.mask_base.copy()
        for d in lay['doors']:
            mv[d['board'][:, 0], d['board'][:, 1]] = hex_to_rgb('#f5b5b5')
            mv[d['pixels'][:, 0], d['pixels'][:, 1]] = hex_to_rgb(DOOR_COLOR)
        self.mask_im.set_data(mv)
        self._apply_view_mode()

    def _update_vce_cards(self):
        n = self.scene['n_vces']
        rows = max(1, -(-n // self.VCE_PER_ROW))
        ch = min(0.065, (0.215 - (rows - 1) * 0.008) / rows)
        cw = (0.94 - (self.VCE_PER_ROW - 1) * 0.01) / self.VCE_PER_ROW
        for i, (ax, edge, name, detail) in self.vce_cards.items():
            if i > n:
                ax.set_visible(False)
                continue
            r, c = divmod(i - 1, self.VCE_PER_ROW)
            ax.set_position([0.03 + c * (cw + 0.01), 0.245 - ch - r * (ch + 0.008), cw, ch])
            info = self.scene['vce_info'][i]
            tag = " (E)" if i in self.routing['right_ids'] else ""
            name.set_text(f"VCE {i} \u00b7 {info['name'] or info['kind']}{tag}")
            ax.set_visible(True)

    # ---------- platform / layout loading ----------
    def _load_platform(self, pid):
        print(f"Building platform {pid} (geometry, stair/escalator mouths, walking-distance fields)...")
        if pid not in self.scene_cache:
            if len(self.scene_cache) >= 3:
                self.scene_cache.pop(next(iter(self.scene_cache)))
            self.scene_cache[pid] = build_platform(self.station, pid)
        self.scene, self.geo, self.routing = self.scene_cache[pid]
        self.pid = pid
        self.layout = None
        self.layout_cache = {}
        self.applied_bias = None
        self._draw_scene()
        self._update_vce_cards()
        title = f"PSNY Platform {pid} Pedestrian Flow Simulation"
        self.title.set_text(title)
        try:
            self.fig.canvas.manager.set_window_title(title)
        except Exception:
            pass
        self.set_view()

    # ---------- control callbacks ----------
    def set_view(self):
        """Zoom = how much of the platform's length is visible; Scroll = where the window sits."""
        W = self.view_W
        vis_w = W / self.s_zoom.val
        x0 = self.s_pan.val * (W - vis_w)
        y_range = vis_w * self.box_aspect
        self.ax.set_xlim(x0, x0 + vis_w)
        self.ax.set_ylim(self.view_yc + y_range / 2, self.view_yc - y_range / 2)
        self.fig.canvas.draw_idle()

    def center_on_trains(self):
        if not self.layout or not self.layout['cars']:
            return
        xs = [(c['x_w'] + c['x_e']) / 2 for c in self.layout['cars']]
        W, vis_w = self.view_W, self.view_W / self.s_zoom.val
        frac = 0.0 if W <= vis_w else float(np.clip((np.mean(xs) - vis_w / 2) / (W - vis_w), 0, 1))
        self.s_pan.set_val(frac)

    def on_toggle_view(self, _=None):
        """Swap between the drawing and the parsed masks (diagnostic: shows exactly what agents treat as wall)."""
        self.view_mode = 'masks' if self.view_mode == 'image' else 'image'
        self._apply_view_mode()
        masks = self.view_mode == 'masks'
        self.btn_view.label.set_text("View: Masks" if masks else "View: Image")
        self.legend_dots['vce'].set_color(VCE_COLOR if masks else IMG_VCE_SWATCH)
        self.legend_dots['obs'].set_color(OBSTACLE_COLOR if masks else IMG_OBS_SWATCH)
        self.fig.canvas.draw_idle()

    def on_start(self, _=None):
        self.running = True
        self.paused = False
        self.btn_pause.label.set_text("Pause")

    def on_pause(self, _=None):
        if not self.running:
            return
        self.paused = not self.paused
        self.btn_pause.label.set_text("Resume" if self.paused else "Pause")

    def set_bias(self, bias):
        self.platform_field = combine_platform_field(self.routing['entry_fields'], self.routing['right_ids'], bias)
        self.applied_bias = bias
        if self.model is not None:
            self.model.platform_field = self.platform_field

    def reset(self, _=None):
        pid = str(int(self.s_plat.val))
        n_cars, berth, dep_per_car = int(self.s_cars.val), float(self.s_berth.val), int(self.s_dep.val)
        if pid != self.pid:
            self._load_platform(pid)
        key = (pid, n_cars, berth)
        entry = self.layout_cache.get(key)
        if entry is None:
            entry = {'layout': place_trains(self.scene, n_cars, berth), 'fields': {}}
            self.layout_cache = {key: entry}
        if dep_per_car > 0 and not entry['fields'] and entry['layout']['doors']:
            print("Computing door routing for departing passengers...")
            entry['fields'] = build_door_fields(self.routing, entry['layout'])
        if self.layout is not entry['layout']:
            self.layout = entry['layout']
            self._draw_layout()
            self.center_on_trains()
        self.door_fields = entry['fields']
        if self.s_east.val != self.applied_bias or self.platform_field is None:
            self.set_bias(self.s_east.val)
        params = dict(
            spawn_rate=self.s_spawn.val, crowding=self.s_crowd.val,
            agent_px=max(1, int(round(self.s_size.val * PX_PER_FT))),
            load1=self.s_load1.val, load2=self.s_load2.val,
            arrival1=self.s_arr1.val, arrival2=self.s_arr2.val,
            dep_per_car=dep_per_car, boarding_delay=self.s_board.val)
        self.model = PedestrianModel(self.scene, self.geo, self.routing, self.layout, self.door_fields,
                                     self.platform_field, params)
        for c in (self.pax, self.dep):
            c.set_widths([self.model.S])
            c.set_heights([self.model.S])
        self.running = False
        self.paused = False
        self.btn_pause.label.set_text("Pause")
        self.refresh()

    # ---------- per-frame ----------
    def update(self, _frame):
        m = self.model
        # live parameters
        if self.s_east.val != self.applied_bias:
            self.set_bias(self.s_east.val)
        m.crowding_penalty = self.s_crowd.val
        m.spawn_rate = self.s_spawn.val
        m.arrival = {1: self.s_arr1.val, 2: self.s_arr2.val}
        m.boarding_delay = self.s_board.val

        if self.running and not self.paused:
            m.step()
        self.refresh()
        return []

    def refresh(self):
        m = self.model

        alight = [a.pos for a in m.agents if a.kind == 'alight']
        depart = [a.pos for a in m.agents if a.kind == 'depart']
        for coll, pts in ((self.pax, alight), (self.dep, depart)):
            if pts:
                coll.set_offsets(np.array(pts)[:, [1, 0]])
            else:
                coll.set_offsets(np.empty((0, 2)))

        # door dots shrink once a door has nobody left to let off
        if self.door_ids:
            self.door_scatter.set_sizes([16 if m.doors[d]['queue'] > 0 else 5 for d in self.door_ids])

        in_vce = m.in_vce_counts()
        exited = sum(m.vce_counts.values())
        mins, secs = int(m.sim_time // 60), int(m.sim_time % 60)
        vals = [str(len(m.agents)), f"{m.alighted} / {m.total_pax}", str(exited),
                f"{m.boarded} / {m.total_dep}", f"{mins}:{secs:02d}"]
        for txt, v in zip(self.stat_texts, vals):
            txt.set_text(v)

        for t in (1, 2):
            tr = m.trains[t]
            self.train_texts[t].set_text(
                f"{len(tr['cars'])}/{tr['requested']} cars fit  |  alighting left {m.train_remaining(t)}/{tr['alight_total']}"
                f"  |  boarded {tr['boarded']}/{tr['dep_total']}")

        for vce_id, (ax, edge, name, detail) in self.vce_cards.items():
            if vce_id > self.scene['n_vces']:
                continue
            if self.geo[vce_id].get('blocked'):
                ax.set_facecolor('#f3f3f3')
                edge.set_color('#cccccc')
                detail.set_text("closed (no way in from the platform)")
                continue
            q = in_vce.get(vce_id, 0)
            congested = q > CONGESTED_THRESHOLD
            ax.set_facecolor(CONGESTED_BG if congested else 'white')
            edge.set_color(CONGESTED_EDGE if congested else (ACCENT if vce_id in self.routing['right_ids'] else BORDER))
            detail.set_text(f"In VCE: {q} | Exited: {m.vce_counts[vce_id]}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Agent-based simulation of detraining/boarding passengers at Penn Station.")
    ap.add_argument('--platform', type=int, default=PLATFORM, help="platform to simulate (1-11); can also be changed in the GUI")
    ap.add_argument('--headless', type=float, metavar='SECONDS', help="run without the GUI for this many simulated seconds")
    ap.add_argument('--seed', type=int, default=None, help="random seed (headless runs)")
    args = ap.parse_args()
    if args.headless:
        run_headless(args.platform, args.headless, seed=args.seed)
    else:
        gui = SimulationGUI(args.platform)
        plt.show()
