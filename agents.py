"""AGENT SYSTEM: the Agent and PedestrianModel movement rules."""
import random
import numpy as np
import cv2
from config import *
from trains import edge_strip_mask


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
        self.train = None         # departing riders: the train they board (1 or 2)
        self.best_field = float('inf')   # closest to their goal they have been so far (for the patience rule)
        self.stall = 0                   # moves since they last got closer


class PedestrianModel:
    def __init__(self, scene, geo, routing, layout, door_fields, platform_field, params, modes=None):
        """modes: escalator directions {VCE number: 'both' | 'up' | 'down'} (see set_modes; default: every VCE 'both').
        platform_field is the field alighting riders follow: build it with alight_field(routing, geo, modes, bias) so that it
        leaves out the escalators set to 'down'."""
        self.grid_shape = scene['obstacle_mask'].shape
        self.obstacle_mask = scene['obstacle_mask']
        self.wall_mask = scene['wall_mask']
        self.labeled_vces = scene['labeled_vces']
        self.platform_field = platform_field
        self.vce_fields = routing['internal']
        self.vce_up_fields = routing['internal_up']               # boarding riders: distance to the stair cells at the mouth
        self.door_fields = door_fields

        # Zone around every usable stair/escalator mouth where riders funnel in closer together (see MOUTH_SPACING_PX)
        mouth = np.zeros(self.grid_shape, dtype=np.uint8)
        for v, g in geo.items():
            if not g.get('blocked'):
                mouth[g['entry'][0], g['entry'][1]] = 1
        k = 2 * MOUTH_ZONE_PX + 1
        self.mouth_zone = cv2.dilate(mouth, np.ones((k, k), np.uint8)) > 0

        # Strip along the track-side platform edges that riders are discouraged from hanging out on (see EDGE_STRIP_PX)
        self.edge_strip = edge_strip_mask(scene, EDGE_STRIP_PX) if EDGE_STRIP_PX > 0 else None

        self.agents = []
        self.vce_counts = {i: 0 for i in range(1, scene['n_vces'] + 1)}      # alighting riders who left the platform by each VCE
        self.vce_boarded = {i: 0 for i in range(1, scene['n_vces'] + 1)}     # boarding riders who came onto the platform by it
        self.vce_mode = {i: 'both' for i in range(1, scene['n_vces'] + 1)}   # escalator directions (set_modes)
        self.no_alight = None                                                 # pixels of the VCEs alighting riders may not enter

        # Footprint bookkeeping: boolean grid of agent CENTER pixels (padded so window slices stay in bounds)
        self.S = params['agent_px']
        self.pad = self.S + CROWDING_BUFFER_PX + 1
        # Three layers: agents on the platform and agents inside a VCE never see each other. The VCE walls are only
        # a few pixels thick, so a shared grid let platform agents standing just outside a wall block the
        # cells inside it (this is what froze the front of the easternmost VCE). Inside a VCE, boarding riders (going up
        # to the platform) have a layer of their own, so they and the alighting riders (going away from it) never
        # block each other: every stair/escalator has a lane each way. (Naming: 'vce_up' is the lane of riders walking from the
        # exit line toward the platform - the way a DOWN escalator runs in station terms; alighting riders, who ride UP, use 'vce'.)
        shape = (self.grid_shape[0] + 2 * self.pad, self.grid_shape[1] + 2 * self.pad)
        self.centers = {'platform': np.zeros(shape, dtype=bool), 'vce': np.zeros(shape, dtype=bool),
                        'vce_up': np.zeros(shape, dtype=bool)}
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

        # where departing riders start (VCEs weighted by the width of their mouth). 'band' is the platform just beyond the
        # mouth, starting beyond the footprint of anyone entering it so they don't block the entry. With
        # DEPARTING_START_AT_VCE_EXIT riders start on the exit line of the stair/escalator - the very cells where alighting
        # riders vanish -, walk up it to the mouth and step off onto the band; otherwise they simply appear on the band.
        self._dep_candidates = []
        for v, g in geo.items():
            if g.get('blocked') or not len(g['src'][0]):
                continue
            ys, xs, ds = g['src']
            sel = (ds >= self.S + 1) & (ds <= self.S + 4)
            if not sel.any():
                sel = ds >= self.S + 1
            if not sel.any():
                continue
            band = (ys[sel], xs[sel])
            if DEPARTING_START_AT_VCE_EXIT:
                eys, exs = np.nonzero(g['exit_mask'])
                if len(eys) and np.isfinite(self.vce_up_fields[v][eys, exs]).all():
                    self._dep_candidates.append({'v': v, 'ys': eys, 'xs': exs, 'band': band})
            else:
                self._dep_candidates.append({'v': v, 'ys': band[0], 'xs': band[1], 'band': band})
        self.step_off = {s['v']: s['band'] for s in self._dep_candidates}
        self.set_modes(modes)                     # chooses dep_sources / dep_weights among the candidates

    def set_modes(self, modes=None):
        """Apply escalator directions {VCE number: 'both' | 'up' | 'down'}; may be called while the model runs, and riders
        already on an escalator finish their ride.
          'up'   (platform -> concourse only): no boarding rider starts on it.
          'down' (concourse -> platform only): alighting riders may not step onto it (no_alight). Keeping them from
                 *heading* for it is the job of the platform_field the caller passes in (alight_field leaves it out)."""
        if modes:
            self.vce_mode.update({v: m for v, m in modes.items() if v in self.vce_mode})
        self.dep_sources = [s for s in self._dep_candidates if self.vce_mode[s['v']] != 'up']
        w = np.array([len(s['ys']) for s in self.dep_sources], dtype=float)
        self.dep_weights = w / w.sum() if len(w) else w
        down = [v for v, m in self.vce_mode.items() if m == 'down']
        self.no_alight = np.isin(self.labeled_vces, down) if down else None
        if self._dep_candidates and not self.dep_sources and self.total_dep > 0:
            print("  warning: every VCE that could bring boarding riders onto the platform is set to 'up' - nobody will board")

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

    def _swap_partner(self, agent, target_field, y, x, here, desperate=False):
        """Two riders who block each other head-on and would BOTH get closer to where they are going by trading
        places do so (people step round one another). Exchanging two equal footprints keeps every other rider's
        spacing intact. Only done when exactly one rider is in the way and both gain, so it never makes a queue
        jump the line: riders walking the same way never both gain.
        desperate (a rider stuck for DEADLOCK_SWAP_TICKS): the partner may be any OPPOSING rider (the other kind) among
        several in the way, need not gain, and the keep-clear zones are ignored - only the mover has to get closer."""
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
            n_in = int(win.sum())
            if n_in == 0 or (n_in != 1 and not desperate):
                continue
            for wy, wx in zip(*np.nonzero(win)):
                by, bx = ny - r + int(wy), nx - r + int(wx)
                other = self.occ.get((by, bx))
                if other is None or other.state != 'platform':
                    continue
                if desperate:
                    if other.kind == agent.kind:
                        continue
                else:
                    if agent.kind == 'depart' and self.keep_clear[by, bx] and not self.keep_clear[y, x]:
                        continue
                    if other.kind == 'depart' and self.keep_clear[y, x] and not self.keep_clear[by, bx]:
                        continue
                pf = self.door_fields[other.target] if other.kind == 'depart' else self.platform_field
                mover_gain = here - target_field[by, bx]
                partner_gain = pf[by, bx] - pf[y, x]
                if mover_gain >= 1.0 and (desperate or partner_gain >= 1.0) and (best is None or mover_gain > best[0]):
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
    def _choose_door(self, t, y, x):
        """The door of train t a rider standing at (y, x) boards: walking distance, crowd at the door, noise. Doors still
        letting people off are not used. None if there is no such door."""
        best, best_cost = None, np.inf
        r = min(7, self.pad)
        for d in self.trains[t]['doors']:
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
        return best

    def _spawn_departing(self, t):
        tr = self.trains[t]
        if not self.dep_sources or not tr['doors']:
            return False
        src = self.dep_sources[np.random.choice(len(self.dep_sources), p=self.dep_weights)]
        ys, xs = src['ys'], src['xs']
        if DEPARTING_START_AT_VCE_EXIT:                              # on the exit line of the stair/escalator, in the up lane
            j = np.random.randint(len(ys))
            y, x = int(ys[j]), int(xs[j])
            if not self._is_free('vce_up', y, x):
                return False
            if MOUTH_BACKLOG_MAX:                                    # riders already queueing at this mouth: nobody new starts
                field = self.vce_up_fields[src['v']]
                waiting = sum(1 for o in self.agents if o.kind == 'depart' and o.state == 'vce' and o.current_vce == src['v']
                              and field[o.pos[0], o.pos[1]] <= 2 * self.S)
                if waiting >= MOUTH_BACKLOG_MAX:
                    return False
            a = Agent([y, x], kind='depart')
            a.state, a.current_vce, a.train = 'vce', src['v'], t     # the door is chosen when they step off the stairs
            self.agents.append(a)
            self._place(a, 'vce_up', y, x)
            return True
        for _ in range(3):
            j = np.random.randint(len(ys))
            y, x = int(ys[j]), int(xs[j])
            if self._is_free('platform', y, x) and self._crowding('platform', y, x) <= DEPARTING_MAX_CROWD:
                break
        else:
            return False
        best = self._choose_door(t, y, x)
        if best is None:
            return False
        a = Agent([y, x], kind='depart', target=best)
        a.train = t
        self.agents.append(a)
        self._place(a, 'platform', y, x)
        return True

    def _step_stair_boarder(self, agent):
        """One move of a boarding rider who is still on a stair/escalator. They walk up it in their own lane (only other
        boarding riders get in their way) to the cells at the mouth, then step off onto the platform just beyond it - a free,
        uncrowded cell (DEPARTING_MAX_CROWD), where they pick a door that is no longer letting people off - and carry on to
        it as ordinary platform riders. Until a cell and a door are free they wait at the mouth."""
        y, x = agent.pos
        v = agent.current_vce
        field = self.vce_up_fields[v]
        here = field[y, x]
        H, W = self.grid_shape
        if here == 0:                                                      # at the mouth: step off
            bys, bxs = self.step_off[v]
            for _ in range(3):
                j = np.random.randint(len(bys))
                ny, nx = int(bys[j]), int(bxs[j])
                if self._is_free('platform', ny, nx) and self._crowding('platform', ny, nx) <= DEPARTING_MAX_CROWD:
                    door = self._choose_door(agent.train, ny, nx)
                    if door is not None:
                        self._lift('vce_up', y, x)
                        agent.state, agent.current_vce, agent.target = 'platform', None, door
                        agent.pos = [ny, nx]
                        agent.best_field, agent.stall = float('inf'), 0
                        self._place(agent, 'platform', ny, nx)
                        self.vce_boarded[v] += 1
                    break
            return
        # still on the stairs: walk toward the mouth
        if here < agent.best_field - 0.5:
            agent.best_field = here
            agent.stall = 0
        else:
            agent.stall += 1
        crowd_w = self.crowding_penalty * (max(0.0, 1.0 - agent.stall / PATIENCE_TICKS) if PATIENCE_TICKS > 0 else 1.0)
        self._lift('vce_up', y, x)
        best_pos, best_score = agent.pos, float('inf')
        steps = NEIGHBOR_STEPS[:]
        random.shuffle(steps)
        for dy, dx in steps:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < H and 0 <= nx < W) or self.labeled_vces[ny, nx] != v:
                continue                                                   # stay on this stair/escalator
            if dy and dx and (self.wall_mask[ny, x] or self.wall_mask[y, nx]):
                continue
            if not self._is_free('vce_up', ny, nx):
                continue
            score = field[ny, nx] + self._crowding('vce_up', ny, nx) * crowd_w
            if score < best_score:
                best_score, best_pos = score, [ny, nx]
        self._place(agent, 'vce_up', best_pos[0], best_pos[1])
        agent.pos = best_pos

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

            if departing and agent.state == 'vce':                         # boarding rider still on the stairs/escalator
                self._step_stair_boarder(agent)
                surviving_agents.append(agent)
                continue

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
            if departing and DEADLOCK_SWAP_TICKS and DEADLOCK_SQUEEZE_TICKS and agent.stall >= DEADLOCK_SWAP_TICKS:
                r_eff = max(1, min(r_eff, self.S - 2 - (agent.stall - DEADLOCK_SWAP_TICKS) // DEADLOCK_SQUEEZE_TICKS))

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
                    if layer == 'platform' and not departing and self.no_alight is not None and self.no_alight[ny, nx]:
                        continue                                           # a 'down' escalator is no way off the platform
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
                        if self.edge_strip is not None and layer == 'platform' and self.edge_strip[ny, nx] and tf >= here - 0.5:
                            score += EDGE_STRIP_PENALTY                        # idling on the edge strip costs extra
                        if score < best_score:
                            best_score = score
                            best_pos = [ny, nx]

            # Boxed in by someone walking the other way? Swap places with them.
            if SWAP_OPPOSING_RIDERS and layer == 'platform' and agent.stall >= 5 and best_free_field >= here - 0.5:
                sw = self._swap_partner(agent, target_field, y, x, here)
                if sw is None and DEADLOCK_SWAP_TICKS and agent.stall >= DEADLOCK_SWAP_TICKS:
                    sw = self._swap_partner(agent, target_field, y, x, here, desperate=True)
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

