"""Central configuration for the TQI analysis."""

from pathlib import Path

# ── Project paths ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GTFS_DIR = DATA_DIR / "gtfs"
CENSUS_DIR = DATA_DIR / "census"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = PROJECT_ROOT / "output"

# ── GTFS source ──
GTFS_URL = "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=13"

# ── Chilliwack municipal boundary ──
# Official boundary from City of Chilliwack Open Data (GeoJSON)
BOUNDARY_GEOJSON = DATA_DIR / "chilliwack_boundary.geojson"
# Bounding box derived from official municipal boundary polygon
BBOX_SW = (49.045918, -122.124370)
BBOX_NE = (49.225607, -121.777247)

# ── Chilliwack route short names (strings, as in GTFS) ──
# Routes 1-9, 12, 15-17, 21-26 are Abbotsford/Central Fraser Valley, NOT Chilliwack.
# Routes 31-35, 39 are Mission area.
# Routes 71, 72 are Agassiz-Harrison and Hope (intercity).
# Route 66 (Fraser Valley Express) connects Chilliwack to Abbotsford — included
#   because it provides meaningful transit access for Chilliwack residents.
CHILLIWACK_ROUTES = [
    "51", "52", "53", "54", "55", "57", "58", "59",  # Chilliwack local
    "66",                                              # Fraser Valley Express
]

# ── Grid parameters ──
GRID_SPACING_M = 250

# ── Walking / routing parameters ──
WALK_SPEED_KMH = 5.0
WALK_SPEED_M_PER_MIN = WALK_SPEED_KMH * 1000 / 60  # 83.33 m/min
MAX_WALK_TO_STOP_M = 800
MAX_TRANSFER_WALK_M = 400
MAX_TRIP_MIN = 90
MAX_TRANSFERS = 2

# ── Time window (minutes since midnight) ──
TIME_START = 6 * 60   # 06:00
TIME_END = 22 * 60    # 22:00
TIME_STEP = 15        # 15-minute resolution
DEPARTURE_TIMES = list(range(TIME_START, TIME_END, TIME_STEP))  # 64 slots

# ── Scoring normalisation ──
TSR_WALK = 5.0    # km/h — walking baseline (score = 0)
TSR_CAR = 40.0    # km/h — car baseline (score = 100)
MIN_OD_DIST_KM = 0.5  # exclude trivially walkable pairs

# ── Walk Score Transit Score ranges (walkscore.com/transit-score-methodology.shtml) ──
WALKSCORE_RANGES = [
    (90, 100, "Rider's Paradise", "World-class public transportation"),
    (70, 89, "Excellent Transit", "Transit convenient for most trips"),
    (50, 69, "Good Transit", "Many nearby public transportation options"),
    (25, 49, "Some Transit", "A few nearby public transportation options"),
    (0, 24, "Minimal Transit", "It is possible to get on a bus"),
]

# ── TCQSM LOS grades (TCRP Report 165, 3rd Edition) ──
# (max_headway_min, grade, description)
TCQSM_LOS = [
    (10, "A", "Passengers don't need schedules"),
    (14, "B", "Frequent service, passengers consult schedules"),
    (20, "C", "Maximum desirable wait if bus is missed"),
    (30, "D", "Service unattractive to choice riders"),
    (60, "E", "Service available during the hour"),
    (999, "F", "Service unattractive to all riders"),
]

# ── PTAL grade boundaries (TfL methodology) ──
# (max_ai, grade)
PTAL_GRADES = [
    (2.5, "1a"),
    (5.0, "1b"),
    (10.0, "2"),
    (15.0, "3"),
    (20.0, "4"),
    (25.0, "5"),
    (40.0, "6a"),
    (float("inf"), "6b"),
]
PTAL_WALK_SPEED_M_PER_MIN = 80.0  # PTAL standard: 80m/min (4.8 km/h)
PTAL_BUS_CATCHMENT_M = 640         # 8 min walk at 80m/min

# ── Earth radius (metres) for spatial projections ──
EARTH_RADIUS_M = 6_371_000

# ── Multi-city comparison configs (BC Transit operators) ──
CITY_CONFIGS = {
    "chilliwack": {
        "operator_id": 13,
        "url": "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=13",
        "bbox_sw": (49.045918, -122.124370),
        "bbox_ne": (49.225607, -121.777247),
        "routes": CHILLIWACK_ROUTES,
    },
    "victoria": {
        "operator_id": 48,
        "url": "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=48",
        "bbox_sw": (48.40, -123.50),
        "bbox_ne": (48.55, -123.30),
        "routes": None,  # use all routes
    },
    "kelowna": {
        "operator_id": 47,
        "url": "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=47",
        "bbox_sw": (49.82, -119.55),
        "bbox_ne": (49.95, -119.40),
        "routes": None,
    },
    "kamloops": {
        "operator_id": 46,
        "url": "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=46",
        "bbox_sw": (50.65, -120.45),
        "bbox_ne": (50.75, -120.25),
        "routes": None,
    },
    "nanaimo": {
        "operator_id": 41,
        "url": "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=41",
        "bbox_sw": (49.12, -124.00),
        "bbox_ne": (49.22, -123.90),
        "routes": None,
    },
}
