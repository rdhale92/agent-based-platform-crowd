"""DASHBOARD GUI: the matplotlib dashboard (SimulationGUI)."""
import itertools
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button, Slider
import matplotlib.patheffects as patheffects
from matplotlib.collections import EllipseCollection, PolyCollection, LineCollection
from matplotlib.patches import FancyArrowPatch, Rectangle
import cv2
from config import *
from station import load_station
from routing import parse_directions, resolve_directions, NEXT_MODE, VCE_MODES, alight_field
from trains import place_trains
from agents import PedestrianModel
from world import build_platform, build_door_fields


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ==========================================
# 6. DASHBOARD GUI
# ==========================================
class SimulationGUI:
    SLIDER_ROWS = [0.535, 0.488, 0.441, 0.394, 0.347]      # y (figure fraction) of the five slider rows
    VCE_PER_ROW = 6
    CLICK_TOLERANCE_PX = 8                                  # screen pixels around an escalator that still count as a click on it
    MODE_LABEL = {'both': 'both ways', 'up': 'up (leaves platform)', 'down': 'down (to platform)'}
    MODE_COLOR = {'both': MUTED, 'up': '#15803d', 'down': '#1d4ed8'}          # text on the cards
    ARROW_COLOR = {'both': '#333333', 'up': '#0b6b2f', 'down': '#12369e'}     # arrows on the map

    def __init__(self, platform=PLATFORM, escalators=None):
        """escalators: starting directions for the escalators, as for --escalators (a dict or the string "3=up,P5-S8=down");
        click an escalator on the map or its card to change it."""
        print("Loading station geometry...")
        self.station = load_station()
        self.escalator_spec = parse_directions(escalators) if isinstance(escalators, str) else dict(escalators or {})
        self.platform_modes = {}          # platform id -> {VCE number: direction}; kept while you switch platforms
        self.modes = {}                   # directions on the platform shown
        self.right_ids = set()            # VCEs the eastern preference favours (alighting riders' choices only)
        self.arrow_artists = []
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
        self.fig.text(0.97, 0.262, "click an escalator (map or card): both ways → up (riders leave the platform) → down "
                      "(riders arrive on it)    ·    (E) = eastern-preference VCE",
                      fontsize=8, color=FAINT, va='center', ha='right')
        self.vce_cards = {}
        for i in range(1, MAX_VCE_CARDS + 1):
            ax = self._card_axes([0.03, 0.1, 0.1, 0.05])
            edge = Rectangle((0, 0), 0.012, 1, transform=ax.transAxes, color=BORDER, clip_on=False)
            ax.add_patch(edge)
            name = ax.text(0.06, 0.80, "", fontsize=9, fontweight='bold', color=TEXT, transform=ax.transAxes, va='center')
            kind = ax.text(0.06, 0.52, "", fontsize=8, color=MUTED, transform=ax.transAxes, va='center')
            detail = ax.text(0.06, 0.24, "", fontsize=7.5, color=MUTED, transform=ax.transAxes, va='center')
            ax.set_visible(False)
            self.vce_cards[i] = (ax, edge, name, kind, detail)
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)

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
        for a in self.scene_artists + self.layout_artists + self.arrow_artists:
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
        self._draw_arrows()
        self._apply_view_mode()

    def _draw_arrows(self):
        """An arrow along every usable escalator showing its direction: 'up' points from the platform end (the mouth) toward
        the concourse end, 'down' the other way, 'both' has a head at each end."""
        self._clear(self.arrow_artists)
        sc, lv = self.scene, self.scene['labeled_vces']
        halo = [patheffects.withStroke(linewidth=2.8, foreground='white')]
        for v, info in sc['vce_info'].items():
            g = self.geo[v]
            if info['kind'] != 'escalator' or g.get('blocked'):
                continue
            ys, xs = np.nonzero(lv == v)
            u = np.asarray(g['axis'], dtype=float)
            c = np.array([g['cx'], g['cy']])
            t = (xs - c[0]) * u[0] + (ys - c[1]) * u[1]
            lo, hi = t.min() + 1.0, t.max() - 1.0                       # keep the arrowheads inside the escalator
            if hi - lo < 4:
                continue
            at_mouth, at_far = (hi, lo) if g['side'] == 1 else (lo, hi)  # which end of the axis meets the platform
            mode = self.modes.get(v, 'both')
            a, b = {'up': (at_mouth, at_far), 'down': (at_far, at_mouth), 'both': (lo, hi)}[mode]
            arrow = FancyArrowPatch(tuple(c + a * u), tuple(c + b * u), arrowstyle='<|-|>' if mode == 'both' else '-|>',
                                    mutation_scale=9, linewidth=1.5, color=self.ARROW_COLOR[mode], zorder=5.5,
                                    shrinkA=0, shrinkB=0)
            arrow.set_path_effects(halo)
            self.ax.add_patch(arrow)
            arrow.set_visible(self.view_mode != 'masks')
            self.arrow_artists.append(arrow)

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
        for i, (ax, edge, name, kind, detail) in self.vce_cards.items():
            if i > n:
                ax.set_visible(False)
                continue
            r, c = divmod(i - 1, self.VCE_PER_ROW)
            ax.set_position([0.03 + c * (cw + 0.01), 0.245 - ch - r * (ch + 0.008), cw, ch])
            info = self.scene['vce_info'][i]
            tag = " (E)" if i in self.right_ids else ""
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
        if pid not in self.platform_modes:
            self.platform_modes[pid] = resolve_directions(self.scene, self.escalator_spec)
        self.modes = self.platform_modes[pid]
        self.set_bias(self.s_east.val)               # the field alighting riders follow (depends on bias and directions)
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
        """(Re)compute the field alighting riders follow. It depends on the eastern-preference bias and on the escalator
        directions (an escalator set to 'down' is no way off the platform), so a change to either comes through here."""
        self.platform_field, self.right_ids = alight_field(self.routing, self.geo, self.modes, bias)
        self.applied_bias = bias
        if self.model is not None:
            self.model.platform_field = self.platform_field

    # ---------- escalator directions ----------
    def _escalator_at(self, event):
        """The escalator under a click on the map (within CLICK_TOLERANCE_PX screen pixels of it), or None."""
        x0, x1 = self.ax.get_xlim()
        tol = self.CLICK_TOLERANCE_PX * abs(x1 - x0) / max(self.ax.bbox.width, 1.0)      # in raster pixels
        best, best_d = None, -tol
        for v, info in self.scene['vce_info'].items():
            if info['kind'] != 'escalator' or self.geo[v].get('blocked'):
                continue
            d = cv2.pointPolygonTest(info['ring_px'].astype(np.float32), (float(event.xdata), float(event.ydata)), True)
            if d >= best_d:
                best, best_d = v, d
        return best

    def _on_click(self, event):
        """Click an escalator (on the map or its card) to cycle it: both ways -> up -> down -> both ways."""
        if event.button != 1 or event.inaxes is None or self.scene is None:
            return
        tb = getattr(self.fig.canvas, 'toolbar', None)
        if tb is not None and getattr(tb, 'mode', ''):                  # the toolbar's zoom/pan tool is active: not ours
            return
        v = None
        if event.inaxes is self.ax:
            v = self._escalator_at(event)
        else:
            for i, (cax, *_rest) in self.vce_cards.items():
                if event.inaxes is cax and cax.get_visible() and i <= self.scene['n_vces']:
                    v = i
                    break
        if v is not None and self.scene['vce_info'][v]['kind'] == 'escalator' and not self.geo[v].get('blocked'):
            self.set_mode(v, NEXT_MODE[self.modes.get(v, 'both')])

    def set_mode(self, v, mode):
        """Set escalator v (its number in the dashboard) to 'both', 'up' or 'down' - also while the simulation runs: riders
        already on it finish their ride, everyone else follows the new setting."""
        info = self.scene['vce_info'][v]
        if info['kind'] != 'escalator':
            raise ValueError(f"VCE {v} ({info['name'] or 'unnamed'}) is a {info['kind']}; only escalators have a direction")
        if mode not in VCE_MODES:
            raise ValueError(f"direction must be one of {', '.join(VCE_MODES)}")
        self.modes[v] = mode
        self.set_bias(self.s_east.val)
        if self.model is not None:
            self.model.set_modes({v: mode})
        print(f"VCE {v} ({info['name'] or 'escalator'}): {self.MODE_LABEL[mode]}")
        if np.isinf(self.platform_field).all():
            print("  warning: no VCE is left for alighting riders to leave the platform by")
        self._draw_arrows()
        self._update_vce_cards()
        if self.model is not None:
            self.refresh()
        self.fig.canvas.draw_idle()

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
                                     self.platform_field, params, self.modes)
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

        for vce_id, (ax, edge, name, kind, detail) in self.vce_cards.items():
            if vce_id > self.scene['n_vces']:
                continue
            info = self.scene['vce_info'][vce_id]
            mode = self.modes.get(vce_id, 'both') if info['kind'] == 'escalator' else 'both'
            if self.geo[vce_id].get('blocked'):
                ax.set_facecolor('#f3f3f3')
                edge.set_color('#cccccc')
                kind.set_text(info['kind'])
                kind.set_color(MUTED)
                detail.set_text("closed (no way in from the platform)")
                continue
            if info['kind'] == 'escalator':
                kind.set_text(f"escalator · {self.MODE_LABEL[mode]}")
                kind.set_color(self.MODE_COLOR[mode])
            else:
                kind.set_text(info['kind'])
                kind.set_color(MUTED)
            q = in_vce.get(vce_id, 0)
            congested = q > CONGESTED_THRESHOLD
            ax.set_facecolor(CONGESTED_BG if congested else 'white')
            edge.set_color(CONGESTED_EDGE if congested else (ACCENT if vce_id in self.right_ids else BORDER))
            parts = [f"In VCE: {q}"]
            if mode != 'down':
                parts.append(f"Exited: {m.vce_counts[vce_id]}")           # alighting riders who left the platform by it
            if mode != 'up':
                parts.append(f"Entered: {m.vce_boarded[vce_id]}")         # boarding riders who came onto the platform by it
            detail.set_text(" | ".join(parts))

