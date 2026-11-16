"""STATION GEOMETRY: the whole station's GeoJSON (feet) -> raster masks for one platform's simulation grid."""
from collections import defaultdict
import json
import os
import urllib.request
import numpy as np
import cv2
from config import *


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


# The station GeoJSON is in longitude and latitude, as GeoJSON requires. The simulator works in the plans' frame in feet
# (x east along the platforms, y north, both along Manhattan's street grid), the frame of the Effective Transit Alliance's
# platform-crowd-model, whose shapes_pcip_phase_1.latlon.geojson registers it to OpenStreetMap's platform outlines with a
# rotation and an offset (the plans are to scale). This is that same mapping, fitted to their file pair (to within 0.1 ft):
#   [lon, lat] = [x_ft, y_ft, 1] @ FT_TO_LONLAT
FT_TO_LONLAT = np.array([[3.1540175424007365e-06, -1.3371342460322917e-06],
                         [1.7650573136407388e-06, 2.3893405476371754e-06],
                         [-73.99481602786665, 40.75091826897086]])
FT_DECIMALS = 3                  # feet coordinates are rounded to this after converting back (they were drawn to 0.01 ft)


def lonlat_to_ft(coords):
    """Nested GeoJSON coordinates in longitude/latitude -> the same nesting in the feet frame."""
    if isinstance(coords[0], (int, float)):
        x, y = np.linalg.solve(FT_TO_LONLAT[:2].T, np.asarray(coords[:2], dtype=float) - FT_TO_LONLAT[2])
        return [round(float(x), FT_DECIMALS), round(float(y), FT_DECIMALS)]
    return [lonlat_to_ft(c) for c in coords]


def ft_to_lonlat(coords, decimals=10):
    """Nested coordinates in the feet frame -> longitude/latitude (for writing the GeoJSON)."""
    if isinstance(coords[0], (int, float)):
        lon, lat = np.array([coords[0], coords[1], 1.0]) @ FT_TO_LONLAT
        return [round(float(lon), decimals), round(float(lat), decimals)]
    return [ft_to_lonlat(c, decimals) for c in coords]


def load_station(path=GEOJSON_FILE):
    path = ensure_geojson(path)
    with open(path) as fh:
        data = json.load(fh)
    # A file with a "frame" member is already in feet (e.g. the Effective Transit Alliance download); otherwise it is
    # longitude/latitude and is converted to feet here.
    if 'frame' not in data:
        for f in data['features']:
            if f.get('geometry'):
                f['geometry']['coordinates'] = lonlat_to_ft(f['geometry']['coordinates'])
    station = {'frame': data.get('frame', ''), 'polys': defaultdict(list), 'walls': []}
    skipped = 0
    for f in data['features']:
        props, g = f.get('properties') or {}, f.get('geometry')
        if not g:
            continue
        if ((PLATFORM_LEVEL_ONLY and props.get('level', 'platform') != 'platform')
                or (SKIP_PLANNED and props.get('status') == 'planned')):
            skipped += 1                                   # not on the platform (concourse level) or not built yet
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
    print(f"Station geometry: {os.path.abspath(path)} - {skipped} of {len(data['features'])} features skipped "
          f"(not platform level, or planned)")
    return station


# "mouth" property of a stair/escalator polygon -> direction (x right = east, y down = south) its platform-side end faces
MOUTH_DIRECTIONS = {'west': (-1.0, 0.0), 'east': (1.0, 0.0), 'north': (0.0, -1.0), 'south': (0.0, 1.0)}


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
            mouth = str(p['props'].get('mouth') or '').strip().lower()      # optional: which end meets the open platform
            vce_src.append({'kind': kind, 'name': name, 'ring': p['rings'][0], 'cx': cx,
                            'mouth': mouth if mouth in MOUTH_DIRECTIONS else ''})
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
        vce_info[new_id] = {'name': v['name'], 'kind': v['kind'], 'ring_px': ring_px, 'mouth': v['mouth'],
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


