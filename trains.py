"""TRAINS AND DOORS: NJ Transit MultiLevel cars laid along the straight platform edge."""
import numpy as np
from scipy.ndimage import label
from config import *
from station import _longest_run


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


def edge_strip_mask(scene, width_px):
    """Walkable platform pixels within width_px rows of the track-side platform edge (the first walkable row is row 0).
    The edge is found the same way place_trains finds it: the first floor pixel seen from the north and from the south."""
    floor, wall, lv = scene['floor'], scene['wall_mask'], scene['labeled_vces']
    H, W = floor.shape
    walk = floor & ~wall & ~(lv > 0)
    prof = edge_profiles(floor)
    strip = np.zeros((H, W), bool)
    for key, sgn in (('N', 1), ('S', -1)):
        cols = np.where(~np.isnan(prof[key]))[0]
        e = prof[key][cols].astype(int)
        first = np.full(len(cols), -1)
        for o in range(0, 7):                                          # the first walkable row lies just inside the edge
            rr = np.clip(e + sgn * o, 0, H - 1)
            ok = (first < 0) & walk[rr, cols]
            first[ok] = rr[ok]
        alive = first >= 0
        for k in range(width_px):
            rr = first + sgn * k
            alive &= (rr >= 0) & (rr < H)
            alive &= walk[np.clip(rr, 0, H - 1), cols]                 # a wall right at the edge ends the strip there
            strip[rr[alive], cols[alive]] = True
    return strip


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


