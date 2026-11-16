"""ROUTING: walkability graph over the platform, VCE mouth analysis, walking-distance fields, escalator directions."""
import re
import numpy as np
from scipy.ndimage import distance_transform_edt, label
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from config import *
from station import MOUTH_DIRECTIONS


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
      near-square stairs). The 'landing' end - the one whose side walls run on past the polygon - is preferred. A polygon
      whose GeoJSON properties say "mouth": "west" (or east / north / south) only considers the end facing that way.
    * The CAD linework frequently closes a mouth completely (a wall across the end, a boxed-in landing). With
      OPEN_BLOCKED_VCE_MOUTHS, a corridor as wide as the mouth is cleared from the mouth out to the open platform, using the
      candidate that needs the fewest wall pixels removed. These openings are recorded in scene['openings'].
    * Returns, per VCE: entry pixels (alighting riders step in here, boarding riders step off), exit mask (far end, where
      alighting riders leave the platform and boarding riders appear) and src pixels (the platform in front of the mouth;
      boarding riders step off onto the band of it that starts just beyond the footprint of anyone entering the mouth)."""
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
        hint = MOUTH_DIRECTIONS.get(scene['vce_info'][v].get('mouth', ''))      # end the GeoJSON says is the mouth, if any
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
                faces_hint = hint is None or float(np.dot(s * ax, hint)) > 0.7
                cands.append((cost, ai, rank, s, ax, pr, pmin, pmax, halfw, cells, reach, faces_hint))
        if not cands:
            print(f"  warning: VCE {v} ({scene['vce_info'][v]['name'] or 'unnamed'}) cannot be reached from the platform - it is left closed")
            geo[v] = {'entry': (ys[:1], xs[:1]), 'exit_mask': np.zeros((H, W), bool), 'src': (ys[:0], xs[:0], xs[:0].astype(float)),
                      'axis': u, 'side': -1, 'cx': float(c[0]), 'cy': float(c[1]), 'opened': False, 'blocked': True}
            continue
        pool = [t for t in cands if t[-1]]
        if hint is not None and not pool:
            print(f"  warning: VCE {v} ({scene['vce_info'][v]['name'] or 'unnamed'}): its mouth is marked '{scene['vce_info'][v]['mouth']}' "
                  f"but that end cannot be reached from the platform - using the other end")
        cost, ai, rank, s, ax, pr, pmin, pmax, halfw, cells, reach, _ = min(pool or cands, key=lambda t: t[:3])
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
    entry_fields, internal, internal_up = {}, {}, {}
    for v in range(1, n + 1):
        ys, xs = entry_pixels[v]
        dist = dijkstra(graph_t, directed=True, indices=idx[ys, xs], min_only=True)
        f = np.full(lv.shape, np.inf, dtype=np.float32)
        f[node] = dist
        entry_fields[v] = f
        d = distance_transform_edt(~geo[v]['exit_mask']).astype(np.float32)
        d[lv != v] = np.inf
        internal[v] = d
        at_mouth = np.zeros(lv.shape, dtype=bool)                      # boarding riders: distance to the cells at the mouth
        at_mouth[ys, xs] = True
        up = distance_transform_edt(~at_mouth).astype(np.float32)
        up[lv != v] = np.inf
        internal_up[v] = up
    comp, _ = label(node & scene['floor'], structure=np.ones((3, 3)))
    sizes = np.bincount(comp.ravel()); sizes[0] = 0
    for v in range(1, n + 1):                         # a mouth that cannot reach the open platform = closed VCE
        reach = int((np.isfinite(entry_fields[v]) & scene['floor']).sum())
        if not geo[v].get('blocked') and reach < 0.5 * sizes.max():
            geo[v]['blocked'] = True
            print(f"  warning: VCE {v} ({scene['vce_info'][v]['name'] or 'unnamed'}) is sealed off from the platform - it is left closed")
        if geo[v].get('blocked'):
            entry_fields[v][:] = np.inf
    right_ids = eastern_vces(geo, geo)                # the two easternmost usable VCEs get the 'eastern preference'
    return {'entry_fields': entry_fields, 'internal': internal, 'internal_up': internal_up, 'right_ids': right_ids,
            'graph_t': graph_t, 'idx': idx, 'node': node}


def combine_platform_field(entry_fields, right_ids, bias):
    best = None
    for v, f in entry_fields.items():
        g = f + (0.0 if v in right_ids else float(bias))
        best = g if best is None else np.minimum(best, g)
    return best


def eastern_vces(geo, ids, n=2):
    """The n easternmost VCEs among `ids` that can be reached from the platform: the ones the eastern preference favours."""
    order = sorted((v for v in ids if not geo[v].get('blocked')), key=lambda v: geo[v]['cx'])
    return set(order[-n:])


# ---- escalator directions: 'both' = a lane each way, 'up' = platform -> concourse only, 'down' = concourse -> platform only ----
VCE_MODES = ('both', 'up', 'down')
NEXT_MODE = {'both': 'up', 'up': 'down', 'down': 'both'}          # the order a click in the dashboard cycles through


def parse_directions(text):
    """'3=up,P5-S8=down,all=down' -> {'3': 'up', 'P5-S8': 'down', 'all': 'down'}. A bare 'down' means 'all=down'."""
    out = {}
    for part in (text or '').replace(';', ',').split(','):
        part = part.strip()
        if not part:
            continue
        key, eq, mode = part.partition('=')
        if not eq:
            key, mode = 'all', key
        key, mode = key.strip(), mode.strip().lower()
        if mode not in VCE_MODES:
            raise ValueError(f"'{part}': the direction must be one of {', '.join(VCE_MODES)}")
        out[key] = mode
    return out


def _name_key(s):
    return ' '.join(str(s).split()).casefold()


def resolve_directions(scene, directions=None):
    """The direction of every VCE of this platform, {VCE number: 'both' | 'up' | 'down'}.
    Precedence: DEFAULT_ESCALATOR_DIRECTION, then ESCALATOR_DIRECTIONS (by vce_name), then `directions` (a dict or the
    --escalators string): 'all' first, then the individual keys, each a VCE number as the dashboard shows it (3 or '3') or a
    vce_name ('P5-S8'). Only escalators have a direction: a stair named here is reported and ignored."""
    if isinstance(directions, str):
        directions = parse_directions(directions)
    directions = {str(k).strip(): str(m).strip().lower() for k, m in (directions or {}).items()}
    checks = [('DEFAULT_ESCALATOR_DIRECTION', DEFAULT_ESCALATOR_DIRECTION)]
    checks += [(f'ESCALATOR_DIRECTIONS[{k!r}]', m) for k, m in ESCALATOR_DIRECTIONS.items()]
    checks += [(f'escalators[{k!r}]', m) for k, m in directions.items()]
    for label, mode in checks:
        if mode not in VCE_MODES:
            raise ValueError(f"{label} = {mode!r}: the direction must be one of {', '.join(VCE_MODES)}")
    info = scene['vce_info']
    by_name = {_name_key(i['name']): v for v, i in info.items() if i['name']}
    modes = {v: (DEFAULT_ESCALATOR_DIRECTION if i['kind'] == 'escalator' else 'both') for v, i in info.items()}

    def put(v, mode):
        if info[v]['kind'] != 'escalator':
            print(f"  note: VCE {v} ({info[v]['name'] or 'unnamed'}) is a {info[v]['kind']}, which always carries both "
                  f"directions - '{mode}' ignored")
        else:
            modes[v] = mode

    for name, mode in ESCALATOR_DIRECTIONS.items():
        if _name_key(name) in by_name:                                 # names of other platforms' VCEs are simply not here
            put(by_name[_name_key(name)], mode)
    for key, mode in directions.items():                               # 'all' first, so individual keys can refine it
        if key.casefold() == 'all':
            for v, i in info.items():
                if i['kind'] == 'escalator':
                    modes[v] = mode
    for key, mode in directions.items():
        if key.casefold() == 'all':
            continue
        if key.isdigit():
            v = int(key)
            if v in info:
                put(v, mode)
            else:
                print(f"  warning: platform {scene['pid']} has VCEs 1-{scene['n_vces']}, not {v} - '{key}={mode}' ignored")
        elif _name_key(key) in by_name:
            put(by_name[_name_key(key)], mode)
        elif not re.match(r'p\d+-', key.casefold()) or key.casefold().startswith(f"p{scene['pid']}-"):
            print(f"  warning: platform {scene['pid']} has no VCE named '{key}' - '{key}={mode}' ignored")
    return modes


def describe_directions(scene, modes):
    """'3 P5-S5 up, 4 P5-S6 down' for the escalators that are not 'both' ('' if there are none)."""
    return ', '.join(f"{v} {scene['vce_info'][v]['name'] or 'escalator'} {m}" for v, m in sorted(modes.items()) if m != 'both')


def alight_field(routing, geo, modes, bias):
    """(walking-distance field the alighting riders follow, the VCEs the eastern preference favours).
    An escalator set to 'down' only brings people onto the platform, so it is no place to leave it: it is left out of the
    field, and the eastern preference goes to the two easternmost of the VCEs that remain. With no escalator set to 'down'
    this is exactly combine_platform_field(entry_fields, right_ids, bias). If no VCE is left the field is infinite everywhere
    (no door can reach one, so nobody alights)."""
    ids = [v for v in routing['entry_fields'] if modes.get(v, 'both') != 'down' and not geo[v].get('blocked')]
    right = eastern_vces(geo, ids)
    if not ids:
        return np.full(next(iter(routing['entry_fields'].values())).shape, np.inf, dtype=np.float32), right
    return combine_platform_field({v: routing['entry_fields'][v] for v in ids}, right, bias), right


def door_field(routing, pixels_yx):
    """Walking distance (px) from every platform pixel to the nearest of the given door pixels."""
    ys, xs = pixels_yx
    dist = dijkstra(routing['graph_t'], directed=True, indices=routing['idx'][ys, xs], min_only=True)
    f = np.full(routing['node'].shape, np.inf, dtype=np.float32)
    f[routing['node']] = dist
    return f


