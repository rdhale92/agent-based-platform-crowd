import itertools
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button, Slider
from matplotlib.collections import EllipseCollection
from matplotlib.patches import Rectangle
from scipy.ndimage import distance_transform_edt, label
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
import cv2

# ==========================================
# CONFIGURATION PARAMETERS (defaults for the GUI sliders)
# ==========================================
IMAGE_FILE = "platform5_polygons.png"
PX_PER_FT = 2.28                 # Image scale (pixels per foot)
AGENT_SIZE_FT = 2.0              # Each agent occupies an AGENT_SIZE_FT x AGENT_SIZE_FT square
WALL_DILATE_PX = 1               # Grow obstacles by this many px for movement (seals thin/anti-aliased boundary lines)
CROWDING_BUFFER_PX = 1           # Extra ring (pixels) beyond touching in which neighbors count as "crowding"
PAXPERDOOR = 30                  # Default passengers per door (sets the default train loads)
SPAWN_RATE_PER_SECOND = 0.8      # Maximum passengers spawned per second per door
MAX_SPAWN_RATE = 1.0             # Upper end of the spawn-rate slider
MAX_PAX_PER_DOOR = 45            # Upper end of the train-load sliders (per door)
TIME_STEP = 0.1                  # Simulation seconds per step (each agent still makes at most one 1-px move per step)
PLATFORM_SPEED = 9.0             # Movement ticks per second on the platform (1 tick = 1 px)
VCE_SPEED = 7.0                  # Movement ticks per second inside a VCE (1 tick = 1 px)
ANIMATION_INTERVAL = 15          # Refresh rate in milliseconds (lower = faster rendering)
RIGHT_VCE_PREFERENCE_BIAS = 300  # Distance bias (px) favoring the 2 rightmost VCEs
CROWDING_PENALTY = 40.0          # Penalty factor for local crowding
CONGESTED_THRESHOLD = 15         # A VCE card turns red when more than this many pax are inside it
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
IMG_VCE_SWATCH = '#ff7400'       # legend colors while showing the original PNG
IMG_OBS_SWATCH = '#404040'
VCE_COLOR = '#ff0000'
OBSTACLE_COLOR = '#333333'
PAX_RGBA = (34 / 255, 197 / 255, 94 / 255, 0.8)   # green
ACCENT = '#4a90e2'
CONGESTED_EDGE = '#e24b4a'
CONGESTED_BG = '#fcebeb'

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans']


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ==========================================
# 1. PARSING & ROUTING
# ==========================================
# Colors read from platform5_polygons.png. Every pixel is snapped to the NEAREST of these, so anti-aliased
# edge pixels resolve to a definite class and the masks come out sharp.
PALETTE = {
    'platform': [(255, 255, 0), (1, 1, 254)],   # yellow floor (+ the blue text labels drawn on it)
    'train':    [(64, 64, 64), (25, 25, 25)],   # train-car polygons and their dark outline
    'obstacle': [(116, 116, 139)],              # blocks on the platform (VCE housings, columns, ...)
    'outside':  [(255, 255, 255)],              # white background between cars / beyond the platform
    'vce':      [(255, 116, 0)],                # orange VCE bars
    'door':     [(220, 30, 30)],                # red door dots
}
DOOR_CLEARANCE_PX = 2   # the white ring / dark edge around each door dot is walkable this far out


def classify_pixels(img):
    names, colors = [], []
    for name, cs in PALETTE.items():
        for c in cs:
            names.append(name)
            colors.append(c)
    colors = np.array(colors, dtype=np.float32)
    H, W = img.shape[:2]
    flat = img.reshape(-1, 3).astype(np.float32)
    idx = np.empty(len(flat), dtype=np.int32)
    for i in range(0, len(flat), 200000):                      # chunked so big images don't blow up memory
        d = ((flat[i:i + 200000, None, :] - colors[None, :, :]) ** 2).sum(axis=2)
        idx[i:i + 200000] = d.argmin(axis=1)
    cls = np.array(names)[idx].reshape(H, W)
    # anti-aliased text pixels (blue over yellow) look grayish and would snap to 'obstacle':
    # real obstacles are bluish-gray (B noticeably above R), text blends are neutral.
    fake = (cls == 'obstacle') & ((img[..., 2].astype(int) - img[..., 0].astype(int)) < 10)
    cls[fake] = 'platform'
    return cls


def parse_and_label_environment(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not find {image_path}. Check the path.")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    cls = classify_pixels(img)

    door_mask = cls == 'door'
    vce_mask = cls == 'vce'
    # Opening removes 1-px-thick fringe lines (anti-aliased platform edge snaps to orange) but keeps the real bars
    vce_mask = cv2.morphologyEx(vce_mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    obstacle_mask = np.isin(cls, ('train', 'obstacle', 'outside'))

    # Doors sit on the car edge, ringed by white/dark pixels: open a small walkable clearance around them
    door_zone = cv2.dilate(door_mask.astype(np.uint8), np.ones((2 * DOOR_CLEARANCE_PX + 1,) * 2, np.uint8)) > 0
    obstacle_mask = obstacle_mask & ~door_zone & ~vce_mask

    labeled_doors, num_doors = label(door_mask)
    raw_labeled_vces, raw_num_vces = label(vce_mask)

    vce_sizes = np.bincount(raw_labeled_vces.ravel())
    valid_vce_ids = [i for i in range(1, raw_num_vces + 1) if vce_sizes[i] > 50]
    # number VCEs sequentially from west (1) to east (N) by their horizontal center
    valid_vce_ids.sort(key=lambda i: np.where(raw_labeled_vces == i)[1].mean())

    labeled_vces = np.zeros_like(raw_labeled_vces)
    for new_id, old_id in enumerate(valid_vce_ids, start=1):
        labeled_vces[raw_labeled_vces == old_id] = new_id

    num_vces = len(valid_vce_ids)

    # Wall mask used for MOVEMENT: obstacles grown by WALL_DILATE_PX so no 1-px leaks, but never eating
    # into VCE pixels or the door clearance.
    if WALL_DILATE_PX > 0:
        k = 2 * WALL_DILATE_PX + 1
        grown = cv2.dilate(obstacle_mask.astype(np.uint8), np.ones((k, k), np.uint8)) > 0
        wall_mask = grown & ~(labeled_vces > 0) & ~door_zone
    else:
        wall_mask = obstacle_mask.copy()

    return img, obstacle_mask, wall_mask, labeled_doors, num_doors, labeled_vces, num_vces


def build_walk_graph(wall_mask, labeled_vces, entry_pixels):
    """8-connected graph over walkable platform pixels, using the SAME movement rules as the agents
    (no walking through walls, no cutting a wall's corner). VCE interiors are excluded - an agent that
    steps into a VCE is committed to it - except the entry column of each VCE. Stepping ONTO another
    VCE's entry column is penalised so routes never cut through a different VCE's doorway."""
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
        w_ab = w + 1000.0 * entry_flag[y0 + dy:y1 + dy, x0 + dx:x1 + dx]   # moving a -> b onto an entry column
        w_ba = w + 1000.0 * entry_flag[y0:y1, x0:x1]                        # moving b -> a onto an entry column
        # csgraph needs one direction per edge for a directed graph; add both directions explicitly
        rows.append(a[ok]); cols.append(b[ok]); wts.append(w_ab[ok])
        rows.append(b[ok]); cols.append(a[ok]); wts.append(w_ba[ok])
    n = int(node.sum())
    graph = coo_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))),
                       shape=(n, n)).tocsr()
    return graph, idx, node


def open_end_of(vce_pixels, obstacle_mask, min_x, max_x):
    """Returns 'left' or 'right' = the end that faces open platform (agents ENTER there).
    Looks 1-3 px beyond each end across the VCE's full height and compares how walled-in each end is
    (a single-pixel check misses housings separated from the bar by an anti-aliased fringe)."""
    H, W = obstacle_mask.shape
    ys = np.where(vce_pixels.any(axis=1))[0]
    y0, y1 = max(0, ys.min() - 1), min(H, ys.max() + 2)
    frac = {}
    for side, x_end, step in (('left', min_x, -1), ('right', max_x, 1)):
        vals = [obstacle_mask[y0:y1, x_end + step * k] for k in (1, 2, 3) if 0 <= x_end + step * k < W]
        frac[side] = float(np.mean(np.concatenate(vals))) if vals else 0.0
    if abs(frac['left'] - frac['right']) < 0.2:
        return 'left'
    return 'left' if frac['left'] < frac['right'] else 'right'


def build_routing_fields(obstacle_mask, wall_mask, labeled_vces, num_vces):
    """Builds the (bias-free) per-VCE entry fields and the internal exit fields.
    The east-preference bias is applied later by combine_platform_field() so the
    slider can change it without recomputing any distance transforms."""
    vce_centers = {}
    for vce_id in range(1, num_vces + 1):
        y_coords, x_coords = np.where(labeled_vces == vce_id)
        vce_centers[vce_id] = np.mean(x_coords)

    sorted_vces = sorted(vce_centers.keys(), key=lambda k: vce_centers[k], reverse=True)
    right_vce_ids = sorted_vces[:2] if len(sorted_vces) >= 2 else sorted_vces

    entry_fields = {}
    vce_internal_fields = {}
    entry_pixels = {}
    print("VCE entry ends:")

    for vce_id in range(1, num_vces + 1):
        vce_pixels = (labeled_vces == vce_id)
        y_coords, x_coords = np.where(vce_pixels)

        min_x = np.min(x_coords)
        max_x = np.max(x_coords)

        if open_end_of(vce_pixels, obstacle_mask, min_x, max_x) == 'left':
            entry_x, exit_x = min_x, max_x
        else:
            entry_x, exit_x = max_x, min_x
        print(f"  VCE {vce_id}: enter at {'left' if entry_x == min_x else 'right'} end, exit at the other")

        entry_mask = np.zeros_like(vce_pixels)
        exit_mask = np.zeros_like(vce_pixels)

        entry_mask[y_coords[x_coords == entry_x], entry_x] = True
        exit_mask[y_coords[x_coords == exit_x], exit_x] = True

        entry_pixels[vce_id] = (y_coords[x_coords == entry_x], np.full(np.sum(x_coords == entry_x), entry_x))

        dist_to_exit = distance_transform_edt(~exit_mask)
        dist_to_exit[~vce_pixels] = np.inf
        vce_internal_fields[vce_id] = dist_to_exit.astype(np.float32)

    # Walking-distance (geodesic) field to each VCE's entry column: agents route AROUND walls / blocks
    graph, idx, node = build_walk_graph(wall_mask, labeled_vces, entry_pixels)
    # reverse graph is identical in structure; distances are measured FROM the entry (weights on the way
    # into an entry column are penalised only for paths that pass through other VCEs' doorways)
    graph_t = graph.T.tocsr()
    for vce_id, (ys, xs) in entry_pixels.items():
        src = idx[ys, xs]
        dist = dijkstra(graph_t, directed=True, indices=src, min_only=True)
        field = np.full(obstacle_mask.shape, np.inf, dtype=np.float32)
        field[node] = dist.astype(np.float32)
        entry_fields[vce_id] = field

    return entry_fields, vce_internal_fields, right_vce_ids


def combine_platform_field(entry_fields, right_vce_ids, right_bias):
    """Non-preferred VCEs are made to look `right_bias` pixels farther away."""
    field = None
    for vce_id, d in entry_fields.items():
        d = d if vce_id in right_vce_ids else d + np.float32(right_bias)
        field = d.copy() if field is None else np.minimum(field, d, out=field)
    return field


def group_doors(labeled_doors, num_doors):
    """Splits doors into Train 1 (north / smaller y) and Train 2 (south / larger y)."""
    door_pixels = {}
    for d in range(1, num_doors + 1):
        px = np.argwhere(labeled_doors == d)
        if len(px) > 0:
            door_pixels[d] = px

    trains = {1: [], 2: []}
    if door_pixels:
        cy = {d: p[:, 0].mean() for d, p in door_pixels.items()}
        lo, hi = min(cy.values()), max(cy.values())
        split = (hi - lo) > 20
        mid = (lo + hi) / 2
        for d in sorted(cy):
            trains[1 if (not split or cy[d] <= mid) else 2].append(d)
    return door_pixels, trains


# ==========================================
# 2. AGENT SYSTEM
# ==========================================
class Agent:
    def __init__(self, pos):
        self.pos = pos
        self.state = 'platform'
        self.current_vce = None
        self.move_timer = 0.0


class PedestrianModel:
    def __init__(self, obstacle_mask, wall_mask, labeled_vces, platform_field, vce_fields,
                 door_pixels, trains, params):
        self.grid_shape = obstacle_mask.shape
        self.obstacle_mask = obstacle_mask
        self.wall_mask = wall_mask
        self.labeled_vces = labeled_vces
        self.platform_field = platform_field
        self.vce_fields = vce_fields

        self.agents = []
        self.vce_counts = {i: 0 for i in range(1, len(vce_fields) + 1)}

        # Footprint bookkeeping: boolean grid of agent CENTER pixels (padded so window slices stay in bounds)
        self.S = params['agent_px']
        self.pad = self.S + CROWDING_BUFFER_PX + 1
        # Two layers: agents on the platform and agents inside a VCE never see each other. The VCE walls are only
        # a few pixels thick, so a shared grid let platform agents standing just outside a wall block the
        # cells inside it (this is what froze the front of the easternmost VCE).
        shape = (self.grid_shape[0] + 2 * self.pad, self.grid_shape[1] + 2 * self.pad)
        self.centers = {'platform': np.zeros(shape, dtype=bool), 'vce': np.zeros(shape, dtype=bool)}

        self.dt = TIME_STEP
        self.sim_time = 0.0
        self.spawn_rate = params['spawn_rate']
        self.crowding_penalty = params['crowding']
        self.arrival = {1: params['arrival1'], 2: params['arrival2']}
        self.alighted = 0

        loads = {1: int(params['load1']), 2: int(params['load2'])}
        self.trains = {}
        self.doors = {}
        for t, door_ids in trains.items():
            n = len(door_ids)
            self.trains[t] = {'doors': door_ids, 'total': loads[t] if n else 0}
            if n == 0:
                continue
            base, extra = divmod(loads[t], n)
            for i, d in enumerate(door_ids):
                self.doors[d] = {'train': t, 'quota': base + (1 if i < extra else 0),
                                 'spawn_accumulator': 0.0, 'pixels': door_pixels[d]}
        self.total_pax = sum(t['total'] for t in self.trains.values())

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

    # ---- stats for the GUI ----
    def train_remaining(self, t):
        return sum(self.doors[d]['quota'] for d in self.trains[t]['doors'])

    def in_vce_counts(self):
        counts = {i: 0 for i in self.vce_counts}
        for a in self.agents:
            if a.state == 'vce':
                counts[a.current_vce] += 1
        return counts

    def step(self):
        self.sim_time += self.dt

        # Spawning (each train only starts once its arrival time has passed)
        for door_id, d_data in self.doors.items():
            if d_data['quota'] > 0 and self.sim_time >= self.arrival[d_data['train']]:
                d_data['spawn_accumulator'] += self.dt * self.spawn_rate
                while d_data['spawn_accumulator'] >= 1.0 and d_data['quota'] > 0:
                    spawn_pos = tuple(d_data['pixels'][np.random.choice(len(d_data['pixels']))])
                    if self._is_free('platform', *spawn_pos):
                        self.agents.append(Agent(list(spawn_pos)))
                        self._set_center('platform', *spawn_pos, True)
                        d_data['quota'] -= 1
                        self.alighted += 1
                    d_data['spawn_accumulator'] -= 1.0

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

            vce_id_here = self.labeled_vces[y, x]
            if agent.state == 'platform' and vce_id_here > 0:
                agent.state = 'vce'
                agent.current_vce = vce_id_here
                self._set_center('platform', y, x, False)      # hand over to the VCE layer
                self._set_center('vce', y, x, True)

            if agent.state == 'vce':
                if self.vce_fields[agent.current_vce][y, x] == 0:
                    self._set_center('vce', y, x, False)
                    self.vce_counts[agent.current_vce] += 1
                    continue

            neighbors = [
                (y-1, x), (y+1, x), (y, x-1), (y, x+1),
                (y-1, x-1), (y-1, x+1), (y+1, x-1), (y+1, x+1)
            ]

            best_pos = agent.pos
            if agent.state == 'platform':
                target_field = self.platform_field
            else:
                target_field = self.vce_fields[agent.current_vce]

            best_score = float('inf')

            # Lift this agent off its grid so it doesn't block or crowd itself
            layer = agent.state
            self._set_center(layer, y, x, False)

            for ny, nx in neighbors:
                if 0 <= ny < self.grid_shape[0] and 0 <= nx < self.grid_shape[1]:
                    if self.wall_mask[ny, nx]:
                        continue
                    # no cutting diagonally through the corner of a wall
                    if ny != y and nx != x and (self.wall_mask[ny, x] or self.wall_mask[y, nx]):
                        continue
                    if self._is_free(layer, ny, nx):
                        # stepping onto a VCE pixel = entering it: needs room in the VCE layer too
                        if layer == 'platform' and self.labeled_vces[ny, nx] > 0 and not self._is_free('vce', ny, nx):
                            continue
                        score = target_field[ny, nx] + self._crowding(layer, ny, nx) * self.crowding_penalty
                        if score < best_score:
                            best_score = score
                            best_pos = [ny, nx]

            # Despawn the instant the agent steps onto the exit line (no extra wait for the next tick)
            if agent.state == 'vce' and self.vce_fields[agent.current_vce][best_pos[0], best_pos[1]] == 0:
                self.vce_counts[agent.current_vce] += 1
                continue

            new_vce = self.labeled_vces[best_pos[0], best_pos[1]]
            if layer == 'platform' and new_vce > 0:            # commit to the VCE the moment it steps in
                agent.state = 'vce'
                agent.current_vce = new_vce
                layer = 'vce'
            self._set_center(layer, best_pos[0], best_pos[1], True)
            agent.pos = best_pos
            surviving_agents.append(agent)

        self.agents = surviving_agents


# ==========================================
# 3. DASHBOARD GUI
# ==========================================
class SimulationGUI:
    SLIDER_ROWS = [0.455, 0.385, 0.315]      # y (figure fraction) of the three slider rows
    VCE_PER_ROW = 6

    def __init__(self, image_path):
        print("Parsing image and building routing fields... this may take a moment.")
        (self.img, self.obs_mask, self.wall_mask, self.labeled_doors, n_doors,
         self.labeled_vces, self.n_vces) = parse_and_label_environment(image_path)
        self.entry_fields, self.vce_fields, self.right_ids = build_routing_fields(
            self.obs_mask, self.wall_mask, self.labeled_vces, self.n_vces)
        self.door_pixels, self.trains = group_doors(self.labeled_doors, n_doors)
        print(f"Detected {self.n_vces} active VCEs and {len(self.door_pixels)} doors "
              f"({len(self.trains[1])} north / {len(self.trains[2])} south).")

        self.applied_bias = None
        self.platform_field = None
        self.model = None
        self.running = False
        self.paused = False

        self._build_figure()
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
        self.fig.text(x, y + 0.022, title, fontsize=9, color=MUTED, va='bottom')
        ax = self.fig.add_axes([x, y, 0.235, 0.012])
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
    def _build_figure(self):
        H, W = self.obs_mask.shape
        self.fig = plt.figure(figsize=(15, 10.5), facecolor=BG)
        try:
            self.fig.canvas.manager.set_window_title("PSNY Platform 5 Pedestrian Flow Simulation")
        except Exception:
            pass

        self.fig.text(0.03, 0.975, "PSNY Platform 5 Pedestrian Flow Simulation",
                      fontsize=16, fontweight='bold', color='#222222', va='top')

        # --- simulation canvas (rendered from the parsed masks, like the HTML canvas) ---
        canvas_rect = [0.03, 0.795, 0.94, 0.145]
        self.ax = self.fig.add_axes(canvas_rect)
        self.ax.set_facecolor(CANVAS_BG)
        for s in self.ax.spines.values():
            s.set_edgecolor(BORDER)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        # Two backgrounds: the original PNG (crisp boundary + VCE walls) and what the parser actually detected
        mask_view = np.empty((H, W, 3), dtype=np.uint8)
        mask_view[:] = hex_to_rgb(CANVAS_BG)
        mask_view[self.obs_mask] = hex_to_rgb(OBSTACLE_COLOR)
        mask_view[self.wall_mask & ~self.obs_mask] = hex_to_rgb('#8a8a8a')   # the extra dilated wall px
        mask_view[self.labeled_vces > 0] = hex_to_rgb(VCE_COLOR)
        self.bg_views = {'image': self.img, 'masks': mask_view}
        self.view_mode = 'image'
        self.bg_im = self.ax.imshow(self.img, interpolation='antialiased', aspect='auto')

        # View window: zoom + horizontal scroll (the image is very wide and only ~100 px tall)
        feat = (self.labeled_vces > 0) | (self.labeled_doors > 0)
        rows = np.where(feat.any(axis=1))[0]
        self.view_yc = (rows.min() + rows.max()) / 2 if len(rows) else H / 2
        self.view_W = W
        self.box_aspect = canvas_rect[3] * 10.5 / (canvas_rect[2] * 15)   # axes height / width in inches
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)

        # VCE labels (white, bold, centered - as in the HTML)
        for vce_id in range(1, self.n_vces + 1):
            ys, xs = np.where(self.labeled_vces == vce_id)
            self.ax.text(xs.mean(), ys.min() - 2, str(vce_id), color='#111111', fontsize=8,
                         fontweight='bold', ha='center', va='bottom', zorder=6,
                         bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85))

        # Door dots (bigger while passengers remain, small once a door is empty)
        self.door_ids = sorted(self.door_pixels)
        dxy = np.array([[self.door_pixels[d][:, 1].mean(), self.door_pixels[d][:, 0].mean()]
                        for d in self.door_ids]) if self.door_ids else np.empty((0, 2))
        self.door_scatter = self.ax.scatter(dxy[:, 0], dxy[:, 1], s=22, c=DOOR_COLOR,
                                            linewidths=0, zorder=4)

        # Passengers, drawn at their true 2 ft footprint
        self.pax = EllipseCollection(widths=[1], heights=[1], angles=[0], units='xy',
                                     offsets=np.zeros((1, 2)), offset_transform=self.ax.transData,
                                     facecolors=[PAX_RGBA], edgecolors='#0f5132', linewidths=0.3, zorder=5)
        self.pax.set_offsets(np.empty((0, 2)))
        self.ax.add_collection(self.pax)

        # --- legend ---
        lax = self.fig.add_axes([0.03, 0.705, 0.94, 0.03])
        lax.axis('off')
        self.legend_dots = {}
        for i, (key, c, name) in enumerate([('door', DOOR_COLOR, 'Train doors'), ('vce', IMG_VCE_SWATCH, 'VCEs'),
                                            ('pax', PAX_RGBA[:3], 'Passengers'),
                                            ('obs', IMG_OBS_SWATCH, 'Obstacles / boundary')]):
            x = 0.002 + i * 0.105
            self.legend_dots[key], = lax.plot([x], [0.5], 'o', ms=7, color=c, transform=lax.transAxes, clip_on=False)
            lax.text(x + 0.008, 0.5, name, transform=lax.transAxes, fontsize=9, color=TEXT, va='center')
        vax = self.fig.add_axes([0.83, 0.708, 0.14, 0.026])
        self.btn_view = Button(vax, "View: Image", color='white', hovercolor='#f0f0f0')
        self.btn_view.label.set_fontsize(9)
        self.btn_view.label.set_color(TEXT)
        for sp in vax.spines.values():
            sp.set_edgecolor('#cccccc')
        self.btn_view.on_clicked(self.on_toggle_view)

        # --- stat cards ---
        self.stat_texts = []
        labels = ["On platform", "Total alighted", "Exited", "Time"]
        gap = 0.012
        cw = (0.94 - (len(labels) - 1) * gap) / len(labels)
        for i, name in enumerate(labels):
            ax = self._card_axes([0.03 + i * (cw + gap), 0.625, cw, 0.065])
            ax.text(0.06, 0.70, name, fontsize=8, color=FAINT, transform=ax.transAxes, va='center')
            self.stat_texts.append(ax.text(0.06, 0.28, "0", fontsize=16, fontweight='bold',
                                           color=TEXT, transform=ax.transAxes, va='center'))

        # --- train boxes ---
        self.train_texts = {}
        bw = (0.94 - 0.012) / 2
        for i, (t, title) in enumerate([(1, "Train 1 (North)"), (2, "Train 2 (South)")]):
            ax = self._card_axes([0.03 + i * (bw + 0.012), 0.555, bw, 0.055])
            ax.add_patch(Rectangle((0, 0), 0.006, 1, transform=ax.transAxes, color=ACCENT, clip_on=False))
            ax.text(0.02, 0.70, title, fontsize=10, fontweight='bold', color=TEXT,
                    transform=ax.transAxes, va='center')
            self.train_texts[t] = ax.text(0.02, 0.28, "", fontsize=9, color=TEXT,
                                          transform=ax.transAxes, va='center')

        # --- zoom / scroll for the canvas ---
        pax_ = self.fig.add_axes([0.03, 0.772, 0.94, 0.010])
        self.s_pan = Slider(pax_, '', 0.0, 1.0, valinit=0.0, color=ACCENT, track_color='#e5e7eb',
                            initcolor='none', handle_style=dict(facecolor='white', edgecolor=ACCENT, size=9))
        self.s_pan.valtext.set_visible(False)
        for sp in pax_.spines.values():
            sp.set_visible(False)

        # --- sliders (3-column grid, like the HTML controls) ---
        n1, n2 = max(len(self.trains[1]), 1), max(len(self.trains[2]), 1)
        self.s_east = self._slider(0, 0, "Eastern preference (bias, px)", 0, 600, 25,
                                   RIGHT_VCE_PREFERENCE_BIAS, '%d px')
        self.s_size = self._slider(1, 0, "Agent size (ft)  - applies on Reset", 0.5, 4.0, 0.25,
                                   AGENT_SIZE_FT, '%.2f')
        self.s_crowd = self._slider(2, 0, "Crowding penalty", 0, 100, 5, CROWDING_PENALTY, '%d')
        self.s_spawn = self._slider(0, 1, "Spawn rate (pax/sec/door)", 0.1, MAX_SPAWN_RATE, 0.1,
                                    SPAWN_RATE_PER_SECOND, '%.1f')
        self.s_load1 = self._slider(1, 1, "Train 1 passengers  - applies on Reset", 0, MAX_PAX_PER_DOOR * n1, n1,
                                    PAXPERDOOR * n1, '%d')
        self.s_load2 = self._slider(2, 1, "Train 2 passengers  - applies on Reset", 0, MAX_PAX_PER_DOOR * n2, n2,
                                    PAXPERDOOR * n2, '%d')
        self.s_arr1 = self._slider(0, 2, "Train 1 arrival (sec)", 0, 300, 1, 0, '%d s')
        self.s_arr2 = self._slider(1, 2, "Train 2 arrival (sec)", 0, 300, 1, 0, '%d s')
        self.s_zoom = self._slider(2, 2, "View zoom (x)", 1.0, 6.0, 0.5, 2.0, '%.1f x')
        self.s_zoom.on_changed(lambda _v: self.set_view())
        self.s_pan.on_changed(lambda _v: self.set_view())
        self.set_view()

        # --- buttons ---
        bw3 = (0.94 - 2 * 0.012) / 3
        self.btn_start = self._button([0.03, 0.235, bw3, 0.04], "Start", self.on_start)
        self.btn_pause = self._button([0.03 + bw3 + 0.012, 0.235, bw3, 0.04], "Pause", self.on_pause)
        self.btn_reset = self._button([0.03 + 2 * (bw3 + 0.012), 0.235, bw3, 0.04], "Reset", self.reset)

        # --- VCE cards ---
        self.fig.text(0.03, 0.212, "Vertical Circulation Elements", fontsize=11,
                      fontweight='bold', color=TEXT, va='center')
        rows = max(1, -(-self.n_vces // self.VCE_PER_ROW))
        ch = min(0.07, (0.18 - (rows - 1) * 0.01) / rows)
        cw = (0.94 - (self.VCE_PER_ROW - 1) * 0.01) / self.VCE_PER_ROW
        self.vce_cards = {}
        for i in range(self.n_vces):
            r, c = divmod(i, self.VCE_PER_ROW)
            ax = self._card_axes([0.03 + c * (cw + 0.01), 0.192 - ch - r * (ch + 0.01), cw, ch])
            edge = Rectangle((0, 0), 0.012, 1, transform=ax.transAxes, color=BORDER, clip_on=False)
            ax.add_patch(edge)
            tag = "  (east pref.)" if (i + 1) in self.right_ids else ""
            ax.text(0.06, 0.70, f"VCE {i + 1}{tag}", fontsize=9, fontweight='bold', color=TEXT,
                    transform=ax.transAxes, va='center')
            detail = ax.text(0.06, 0.28, "", fontsize=8, color=MUTED, transform=ax.transAxes, va='center')
            self.vce_cards[i + 1] = (ax, edge, detail)

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

    def on_toggle_view(self, _=None):
        """Swap between the original PNG and the parsed masks (diagnostic: shows exactly what agents treat as wall)."""
        self.view_mode = 'masks' if self.view_mode == 'image' else 'image'
        self.bg_im.set_data(self.bg_views[self.view_mode])
        self.bg_im.set_interpolation('nearest' if self.view_mode == 'masks' else 'antialiased')
        self.btn_view.label.set_text("View: Masks" if self.view_mode == 'masks' else "View: Image")
        self.legend_dots['vce'].set_color(VCE_COLOR if self.view_mode == 'masks' else IMG_VCE_SWATCH)
        self.legend_dots['obs'].set_color(OBSTACLE_COLOR if self.view_mode == 'masks' else IMG_OBS_SWATCH)
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
        self.platform_field = combine_platform_field(self.entry_fields, self.right_ids, bias)
        self.applied_bias = bias
        if self.model is not None:
            self.model.platform_field = self.platform_field

    def reset(self, _=None):
        if self.s_east.val != self.applied_bias:
            self.set_bias(self.s_east.val)
        params = dict(
            spawn_rate=self.s_spawn.val, crowding=self.s_crowd.val,
            agent_px=max(1, int(round(self.s_size.val * PX_PER_FT))),
            load1=self.s_load1.val, load2=self.s_load2.val,
            arrival1=self.s_arr1.val, arrival2=self.s_arr2.val)
        self.model = PedestrianModel(self.obs_mask, self.wall_mask, self.labeled_vces, self.platform_field,
                                     self.vce_fields, self.door_pixels, self.trains, params)
        self.pax.set_widths([self.model.S])
        self.pax.set_heights([self.model.S])
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

        if self.running and not self.paused:
            m.step()
        self.refresh()
        return []

    def refresh(self):
        m = self.model

        if m.agents:
            pos = np.array([a.pos for a in m.agents])
            self.pax.set_offsets(pos[:, [1, 0]])
        else:
            self.pax.set_offsets(np.empty((0, 2)))

        # door dots shrink once a door has no passengers left
        if self.door_ids:
            self.door_scatter.set_sizes([22 if m.doors[d]['quota'] > 0 else 6 for d in self.door_ids])

        in_vce = m.in_vce_counts()
        exited = sum(m.vce_counts.values())
        mins, secs = int(m.sim_time // 60), int(m.sim_time % 60)

        vals = [str(len(m.agents)), f"{m.alighted} / {m.total_pax}", str(exited),
                f"{mins}:{secs:02d}"]
        for txt, v in zip(self.stat_texts, vals):
            txt.set_text(v)

        for t in (1, 2):
            self.train_texts[t].set_text(f"Remaining: {m.train_remaining(t)}/{m.trains[t]['total']}")

        for vce_id, (ax, edge, detail) in self.vce_cards.items():
            q = in_vce.get(vce_id, 0)
            congested = q > CONGESTED_THRESHOLD
            ax.set_facecolor(CONGESTED_BG if congested else 'white')
            edge.set_color(CONGESTED_EDGE if congested else BORDER)
            detail.set_text(f"In VCE: {q} | Exited: {m.vce_counts[vce_id]}")


if __name__ == "__main__":
    gui = SimulationGUI(IMAGE_FILE)
    plt.show()
