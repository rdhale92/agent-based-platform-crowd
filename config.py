"""Configuration parameters and theme colours for the Penn Station crowd simulator (see simulator.py for the model).

Every tunable of the model and of the dashboard lives here; the other modules import them with `from config import *`.
"""
import matplotlib.pyplot as plt


# ==========================================
# CONFIGURATION PARAMETERS (defaults for the GUI sliders)
# ==========================================
# ---- station geometry (replaces the old platform5_polygons.png) ----
GEOJSON_FILE = "shapes_pcip_phase_1.geojson"   # whole-station geometry in feet (downloaded automatically if missing)
GEOJSON_URL = ("https://github.com/effective-transit-alliance/platform-crowd-model/raw/refs/heads/"
               "kkysen/per-vce/data/shapes_pcip_phase_1.geojson")
PLATFORM_LEVEL_ONLY = True       # skip features whose "level" is not "platform" (concourse-level stairs, elevators, walls)
SKIP_PLANNED = True              # skip features marked "status": "planned" (on the plans, not built)
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
DOOR_REACH_FT = 8.0              # every door opens; one with a wall/stair right in front of it lets riders off onto the
                                 # nearest open platform if it is within this distance (else onto the walkable cells there)
DOOR_POSITIONS_FT = (3.0, 18.0, 67.0, 82.0) # door centres measured from the car's west end (approximate: one per end)
DOORS_PER_CAR = len(DOOR_POSITIONS_FT)
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
DEPART_RATE = 4.0                # Departing passengers appearing on the stairs/escalators per second (per train)
DEPARTING_START_AT_VCE_EXIT = True   # True = boarding riders appear where alighting riders vanish (the exit line at the far end
                                 # of each stair/escalator) and walk to the mouth. False = the old rule: they appear on the
                                 # platform a few px beyond the mouth
IN_CAR_LOADING = True            # True (new) = every alighting rider is created inside its train at simulation start, drawn
                                 # loaded in the car, and steps onto the platform through its door when the train arrives
                                 # (rate-limited per door as before). False = the old rule: riders materialise at the doors
                                 # after the train arrives.
BOARDING_DELAY = 120             # Seconds after a train's arrival before its departing passengers start to appear
DEPARTING_MAX_CROWD = 2          # A departing passenger only steps off the stairs into a cell with at most this many
                                 # neighbours (otherwise they wait on the stairs) - keeps stair mouths from locking up
MOUTH_BACKLOG_MAX = 2            # A stair/escalator starts no new boarding rider while this many are already waiting at its
                                 # mouth for room to step off (a stair backs up when the platform in front of it is full).
                                 # Stops boarders piling into walled pockets in front of a mouth. 0 = off.
# Alighting riders choose which door of their own car to leave by: a random-utility choice made when the train arrives.
#   cost(door) = DOOR_PREF_WEIGHT * walking distance to the stairs/escalators (ft)
#              + queue-length cost (riders already heading for that door) + logistic noise
DOOR_CHOICE_RANGE_CARS = 1       # Doors considered for a rider's door choice: 0 = only the doors of the rider's own car;
                                 # 1 = also the neighbouring cars' doors (a rider whose own doors are bottlenecked can walk
                                 # through the train to an adjacent car's door). The extra friction is CAR_CROSS_PENALTY_FT.
CAR_CROSS_PENALTY_FT = 20.0      # Extra cost (ft of walking) for choosing a door in a neighbouring car, per car boundary
                                 # crossed. Same car = 0. More than the in-car friction (queue + DOOR_NOISE_FT, ~12 ft), so
                                 # riders prefer their own doors and only spill over when those are genuinely congested.
IN_CAR_FRICTION = 1.0            # IN_CAR_LOADING: cost (ft) per ft walked inside the train to reach a door
CAR_CHANGE_DELAY_S = 3.0         # IN_CAR_LOADING: seconds to get through the end doors into the next car
CAR_WALK_SPEED = 3.0             # IN_CAR_LOADING: px per second walking down a crowded car (~1.3 ft/s)
DOOR_RECHECK_S = 5.0             # IN_CAR_LOADING: a rider still on board looks at the doors again about this often...
DOOR_SWITCH_MARGIN_FT = 6.0      # ...and changes door only if the new one is cheaper by more than this (ft)
DOOR_PATIENCE_S = 20.0           # IN_CAR_LOADING: a rider who has waited this long AT their door (s) starts to consider the
                                 # next door along the train on either side (possibly in the next car), every DOOR_RECHECK_S.
                                 # Their own door counts the riders ahead of them, scaled up by how long it has gone without
                                 # letting anyone off; 0 = never leave a door once there.
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
# ---- escalator directions ----
# An escalator (a VCE the GeoJSON types "escalator"; the rest are stairs) runs 'up' (platform -> concourse: alighting riders use
# it, nobody comes down it), 'down' (concourse -> platform: boarding riders come down it, alighting riders never enter it) or
# 'both' (a lane each way, which is how stairs always behave). Click an escalator in the dashboard, or pass --escalators, to
# change one; these two settings are the starting point.
DEFAULT_ESCALATOR_DIRECTION = 'both'   # for every escalator not listed below
ESCALATOR_DIRECTIONS = {}              # per escalator, by its GeoJSON vce_name: {'P5-S8': 'up', 'P6-S10': 'down'}
CROWDING_PENALTY = 40.0          # Penalty factor for local crowding
SWAP_OPPOSING_RIDERS = True      # alighting and departing riders who block each other head-on swap places
PATIENCE_TICKS = 90              # A rider who makes no progress for this many moves (~10 s) stops avoiding crowds: the
                                 # crowding penalty fades linearly to zero. Prevents standoff rings around crowded stairs
                                 # and doors. 0 = off (the original behaviour: crowding is always avoided).
DEADLOCK_SWAP_TICKS = 450        # A rider who has made no progress for this many moves (~50 s) and finds no ordinary swap
                                 # partner swaps places with an opposing rider (alighting <-> boarding) however many riders
                                 # are in the way and even across a keep-clear zone. Undoes head-on standoffs in narrow gaps
                                 # (e.g. boarders walking west, alighters from a door still in use walking east, in a 4 ft
                                 # wide gap). Never reached in normal flow. 0 = off.
DEADLOCK_SQUEEZE_TICKS = 30      # A BOARDING rider jammed that long (DEADLOCK_SWAP_TICKS) also accepts 1 px less personal
                                 # space, and 1 px less again per this many further moves, so a pocket whose only way out is a
                                 # 1 ft gap (e.g. in front of a stair mouth) empties instead of locking up. 0 = off.
EDGE_STRIP_PX = 3                # Width (px, ~1.5 ft) of the strip along each track-side platform edge that riders are
                                 # discouraged from hanging out on. A rider can always walk on it (a step that brings the
                                 # rider closer to its target costs nothing extra), but a step onto or along it that doesn't
                                 # costs EDGE_STRIP_PENALTY, so a rider who is waiting, jostling or shuffling prefers cells
                                 # off the strip. Riders leaving the train still start on it. 0 = off.
EDGE_STRIP_PENALTY = 40.0        # Cost (px of walking) of such an idle step onto the strip; same scale as CROWDING_PENALTY.
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
DEFAULT_ZOOM = 1.0               # initial zoom (1 = whole platform length visible)
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



__all__ = [
    # station geometry
    'GEOJSON_FILE', 'GEOJSON_URL', 'PLATFORM_LEVEL_ONLY', 'SKIP_PLANNED', 'PLATFORM', 'PX_PER_FT',
    'INCLUDE_UNNAMED_VCES', 'INCLUDE_ELEVATORS', 'OPEN_BLOCKED_VCE_MOUTHS', 'TRACK_MARGIN_FT', 'END_MARGIN_FT',
    # train cars
    'CAR_LENGTH_FT', 'CAR_WIDTH_FT', 'CAR_COUPLER_GAP_FT', 'CAR_PLATFORM_GAP_FT', 'DOOR_WIDTH_FT',
    'DOOR_POSITIONS_FT', 'DOOR_REACH_FT', 'DOORS_PER_CAR', 'CARS_PER_TRAIN', 'MAX_CARS',
    # passengers / flows
    'AGENT_SIZE_FT', 'WALL_DILATE_PX', 'CROWDING_BUFFER_PX', 'PAXPERDOOR', 'DEPARTING_PER_DOOR',
    'MAX_PAX_PER_DOOR', 'MAX_DEPARTING_PER_DOOR', 'SPAWN_RATE_PER_SECOND', 'MAX_SPAWN_RATE', 'DEPART_RATE',
    'DEPARTING_START_AT_VCE_EXIT', 'IN_CAR_LOADING', 'BOARDING_DELAY', 'DEPARTING_MAX_CROWD', 'MOUTH_BACKLOG_MAX',
    'DOOR_CHOICE_RANGE_CARS', 'CAR_CROSS_PENALTY_FT', 'IN_CAR_FRICTION', 'CAR_CHANGE_DELAY_S', 'CAR_WALK_SPEED',
    'DOOR_RECHECK_S', 'DOOR_SWITCH_MARGIN_FT', 'DOOR_PATIENCE_S', 'DOOR_PREF_WEIGHT', 'DOOR_QUEUE_AWARENESS', 'DOOR_NOISE_FT',
    'CAR_CROWD_WEIGHT_FT', 'CAR_NOISE_FT', 'TIME_STEP', 'PLATFORM_SPEED', 'VCE_SPEED',
    'ANIMATION_INTERVAL', 'RIGHT_VCE_PREFERENCE_BIAS',
    # escalator directions
    'DEFAULT_ESCALATOR_DIRECTION', 'ESCALATOR_DIRECTIONS',
    # crowd-movement additions
    'CROWDING_PENALTY', 'SWAP_OPPOSING_RIDERS', 'PATIENCE_TICKS', 'DEADLOCK_SWAP_TICKS',
    'DEADLOCK_SQUEEZE_TICKS', 'EDGE_STRIP_PX', 'EDGE_STRIP_PENALTY',
    # optional extras (off by default)
    'SQUEEZE_TICKS', 'MOUTH_SPACING_PX', 'MOUTH_ZONE_PX', 'STAIR_ENTRY_NEEDS_PLATFORM_ROOM',
    'KEEP_CLEAR_PX', 'CONGESTED_THRESHOLD',
    # window
    'FIG_W', 'FIG_H', 'DEFAULT_ZOOM', 'MAX_VCE_CARDS',
    # theme
    'BG', 'CANVAS_BG', 'BORDER', 'CARD_BORDER', 'TEXT', 'MUTED', 'FAINT', 'DOOR_COLOR',
    'IMG_VCE_SWATCH', 'IMG_OBS_SWATCH', 'VCE_COLOR', 'OBSTACLE_COLOR', 'FLOOR_COLOR', 'FLOOR_EDGE',
    'STAIR_COLOR', 'ESCALATOR_COLOR', 'ELEVATOR_COLOR', 'CAR_COLOR', 'CAR_EDGE',
    'PAX_RGBA', 'DEP_RGBA', 'ACCENT', 'CONGESTED_EDGE', 'CONGESTED_BG',
]
