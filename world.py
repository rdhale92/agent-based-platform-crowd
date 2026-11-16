"""WORLD BUILDING: compose one platform's raster scene, VCE mouths, routing fields and (doors' walking-distance fields)."""
from config import *
from station import build_scene
from routing import analyze_vces, build_routing_fields, door_field


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

