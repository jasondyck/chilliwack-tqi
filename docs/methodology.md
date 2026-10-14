# Chilliwack Transit Quality Index (TQI)

## Methodology Design Document

---

## 1. Objective

Produce a single numeric score (0–100) that answers: **"How good is public transit in Chilliwack?"** — defined as the average ease of getting from any arbitrary point A to any arbitrary point B using transit, across all times of day.

The score should be:
- **Intuitive** — 0 = no transit, 100 = instant teleportation everywhere
- **Reproducible** — anyone with the same GTFS feed gets the same number
- **Comparable** — can be computed for any BC Transit city (or any GTFS-publishing agency)
- **Time-aware** — captures how service quality varies throughout the day

---

## 2. Conceptual Framework

### What "transit quality" means here

A transit trip from A→B consists of five time components:

| Component | Symbol | Description |
|-----------|--------|-------------|
| Walk to stop | `t_access` | Walking from origin to nearest usable stop |
| Wait for bus | `t_wait` | Time until the next departure |
| In-vehicle | `t_ride` | Time spent on the bus (may span multiple legs) |
| Transfer | `t_transfer` | Walking between stops + waiting for next bus (per transfer) |
| Walk from stop | `t_egress` | Walking from alighting stop to destination |

**Total transit time:**
```
T_transit(A, B, t_depart) = t_access + t_wait + t_ride + Σ(t_transfer_i) + t_egress
```

The TQI compares this against the **straight-line baseline** — how long it would take to walk the crow-flies distance — to produce a ratio that's independent of city size.

### The core metric: Transit Speed Ratio (TSR)

For a given OD pair at a given departure time:

```
TSR(A, B, t) = d_euclidean(A, B) / T_transit(A, B, t)
```

This gives an "effective speed" in km/h. If transit makes you no faster than walking (5 km/h), TSR ≈ 5. A good urban bus system might yield TSR ≈ 15–25. A car would be ~30–50.

The TQI normalizes TSR into a 0–100 scale.

---

## 3. Data Inputs

### 3.1 Required: GTFS Static Feed

**Source:** `https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=13`

This is the Fraser Valley Region feed (operator 13), which covers Chilliwack, Central Fraser Valley, Agassiz-Harrison, and Hope. You'll need to filter to Chilliwack-relevant routes.

Key GTFS files used:

| File | Purpose |
|------|---------|
| `stops.txt` | Stop locations (lat/lon), stop names |
| `stop_times.txt` | Arrival/departure times at each stop for each trip |
| `trips.txt` | Trip→route mapping, direction, service_id |
| `routes.txt` | Route metadata (short_name, type) |
| `calendar.txt` / `calendar_dates.txt` | Which services run on which days |
| `shapes.txt` | Route geometry (optional, for visualization) |

### 3.2 Required: Analysis Grid

A set of origin/destination points covering Chilliwack's urban area. Two approaches:

**Option A — Regular grid (recommended for simplicity):**
Generate a grid of points at ~250m spacing within Chilliwack's urban boundary. At roughly 12km × 8km urban extent, this gives ~1,500 grid points.

**Option B — Population-weighted (better for equity analysis):**
Use Statistics Canada Dissemination Area centroids, weighted by population. This focuses the analysis on where people actually live.

**Suggested bounding box for Chilliwack urban area:**
```
SW corner: 49.130, -121.985
NE corner: 49.195, -121.895
```

### 3.3 Parameters (Configurable)

| Parameter | Default | Notes |
|-----------|---------|-------|
| Walk speed | 5.0 km/h (83.3 m/min) | Standard planning assumption |
| Max walk to stop | 800m (~10 min) | Beyond this, transit is "unavailable" from that origin |
| Max walk between transfers | 400m (~5 min) | Conservative for transfers |
| Max total trip time | 90 min | Cap to avoid absurd multi-hour itineraries |
| Max transfers | 2 | Realistic for a small city system |
| Time window | 06:00–22:00 | Span of analysis |
| Time resolution | 15 min | Departure time granularity (yields 64 time slots) |
| Analysis day | A typical Wednesday | Avoids weekend/holiday schedule edge cases |

---

## 4. Algorithm

### Step 1: Build the Transit Graph

From the GTFS data, construct a time-expanded graph:

1. **Parse stops.** Extract all stops with lat/lon.
2. **Parse stop_times + trips + calendar.** For the target analysis day, resolve which `service_id` values are active, then collect all (trip, stop, arrival_time, departure_time) tuples.
3. **Build stop-to-stop travel times.** For each consecutive stop pair within a trip, record the scheduled travel time.
4. **Build transfer edges.** For each pair of stops within 400m walking distance (but on different routes), add a walking transfer edge with time = distance / walk_speed.

The result is a directed graph where:
- **Nodes** = (stop, time) pairs
- **Edges** = riding a bus segment, walking between stops, or waiting at a stop

### Step 2: Compute Travel Time Matrix

For each grid point `A`, at each departure time `t`:

1. **Find accessible stops.** All stops within 800m of `A`. Compute walk time to each.
2. **Run RAPTOR or Dijkstra.** From each accessible stop (arriving at stop at `t + walk_time`), find shortest path to all other stops in the network, respecting the time-expanded schedule.
3. **For each grid point `B`:** Find all stops within 800m of `B`. The travel time is:
   ```
   T(A, B, t) = min over all (stop_origin, stop_dest) pairs of:
       walk_to(A, stop_origin) + transit(stop_origin, stop_dest, t + walk_to) + walk_from(stop_dest, B)
   ```
4. **If no path exists** within the max trip time / max transfers constraint, mark as `∞` (unreachable).

**Recommended algorithm: RAPTOR** (Round-Based Public Transit Routing). It's designed specifically for GTFS timetable data and handles the time-dependent nature of transit natively. Much faster than adapting Dijkstra to time-expanded graphs.

Reference implementation: see the `r5py` Python library which wraps Conveyal's R5 engine, or implement a simplified RAPTOR in Python directly.

### Step 3: Compute Per-Pair Metrics

For each OD pair (A, B), across all departure times:

```python
# Pseudo-code
for each OD pair (A, B) where A ≠ B:
    d = haversine(A, B)  # km
    
    times = [T_transit(A, B, t) for t in departure_times]
    reachable = [t for t in times if t < ∞]
    
    pair_metrics = {
        "reachability": len(reachable) / len(times),       # fraction of day pair is connected
        "median_time": median(reachable) if reachable else ∞,
        "mean_tsr": mean(d / t for t in reachable) if reachable else 0,
    }
```

### Step 4: Aggregate to TQI Score

The TQI combines two sub-scores:

#### 4a. Coverage Score (0–100)
What fraction of OD pairs are reachable by transit at all?

```
coverage = mean(pair.reachability for all pairs where d > 0.5 km)
coverage_score = coverage × 100
```

We exclude very short OD pairs (< 500m) since those are trivially walkable and shouldn't penalize the transit score.

#### 4b. Speed Score (0–100)
For reachable pairs, how fast is transit relative to walking?

```
mean_tsr = mean(pair.mean_tsr for all reachable pairs)

# Normalize: walking speed (5 km/h) = 0, car-like speed (40 km/h) = 100
speed_score = clamp((mean_tsr - 5) / (40 - 5) × 100, 0, 100)
```

#### 4c. Final TQI

```
TQI = 0.5 × coverage_score + 0.5 × speed_score
```

Equal weighting because both dimensions matter — a fast bus that only serves one corridor isn't "good transit," and neither is comprehensive but glacially slow coverage.

---

## 5. Sub-Indices (Optional but Valuable)

Beyond the single TQI number, compute these breakdowns for richer insight:

### 5a. Time-of-Day Profile
Compute TQI separately for each time slot. Plot as a line chart showing how transit quality varies from 6am to 10pm. Peak vs off-peak gap is a key indicator of service investment.

### 5b. Spatial Heat Map
For each grid point, compute its "average outbound TQI" — how well-connected is *this* location to the rest of the city? Reveals transit deserts vs well-served corridors.

### 5c. Temporal Reliability
Standard deviation of travel time across departure times for each OD pair. High variance = you're at the mercy of the schedule. Low variance = frequent, reliable service.

### 5d. Equity Overlay (requires census data)
Cross-reference the spatial heat map with Statistics Canada income/demographics data to see whether transit quality correlates with socioeconomic need.

---

## 6. Benchmarking & Interpretation

### What the numbers mean (rough calibration)

| TQI Range | Interpretation | Example |
|-----------|---------------|---------|
| 0–10 | Effectively no transit | Rural area with 1 bus/day |
| 10–25 | Minimal transit | Small town, few routes, hourly service |
| 25–40 | Basic transit | Mid-size city with reasonable core coverage |
| 40–60 | Good transit | Well-funded mid-size system or outer suburbs of major city |
| 60–80 | Very good transit | Major city core, frequent service |
| 80–100 | Exceptional | Dense metro with subway/BRT, <5 min headways |

**Prediction for Chilliwack:** Based on ~10 local routes, mostly 30–60 min headways, hub-and-spoke from downtown exchange — likely TQI in the **10–25 range**.

### Cross-city comparison
Run the same methodology against other BC Transit feeds to produce a ranking. Interesting comparisons: Victoria (operatorId 48), Kelowna (47), Kamloops (46), Nanaimo (41).

---

## 7. Implementation Notes

### Recommended Stack

| Component | Tool | Why |
|-----------|------|-----|
| GTFS parsing | `gtfs-kit` or raw pandas | Lightweight, no Java dependency |
| Routing engine | Custom RAPTOR or `r5py` | RAPTOR is the right algorithm for this |
| Spatial ops | `scipy.spatial.cKDTree` | Fast nearest-stop lookups |
| Distance | `haversine` | Euclidean on a sphere |
| Grid generation | `numpy.meshgrid` | Simple regular grid |
| Visualization | `matplotlib` / `folium` | Heat maps, time profiles |

### Performance Considerations

For 1,500 grid points × 64 time slots × 1,500 destinations:
- That's ~144 million OD-time combinations
- RAPTOR from one origin at one time visits all stops — so it's really 1,500 × 64 = 96,000 RAPTOR runs
- Each RAPTOR run on a small network (~300 stops) takes ~1–5ms
- **Total: ~2–8 minutes** on a modern machine. Very tractable.

### Simplification Option: Stop-to-Stop Only

If computing a full grid is overkill for a first pass, simplify:
- Use the ~300 GTFS stops as both origins and destinations
- Skip the walk-to-stop component (assume you're at a stop)
- This reduces to 300 × 64 = 19,200 RAPTOR runs (~20–60 seconds)
- Gives a "network-centric" TQI that measures how well the bus system connects its own stops

This is a great MVP approach before investing in the full grid analysis.

### Key GTFS Gotchas for Chilliwack

1. **Operator 13 covers the whole Fraser Valley Region**, not just Chilliwack. Filter routes by `route_short_name` — Chilliwack routes are 1–9, 12, 15–17, 21–26, 51–59, 66, 71, 72 (per the BC Transit website). Routes 31–35, 39 appear to be Central Fraser Valley / Mission area.
2. **Calendar parsing:** Check both `calendar.txt` and `calendar_dates.txt`. Some feeds use only `calendar_dates` with no `calendar`.
3. **Timepoints vs interpolated times:** Some `stop_times` entries have `timepoint=0` meaning the time is approximate/interpolated. For this analysis, treat them as exact.
4. **Overnight trips:** Some trips may have `stop_times` > 24:00:00 (e.g., `25:30:00` = 1:30 AM next day). Handle this in your parser.

---

## 8. Extensions & Future Work

- **Include walking as a competing mode.** For any OD pair where walking is faster than transit, the transit system gets no credit. This naturally penalizes systems that are slower than just walking.
- **Weight OD pairs by trip demand.** If you can get census commute flow data, weight the pairs by actual travel demand rather than treating all pairs equally.
- **Temporal expansion.** Run the analysis for multiple days (weekday, Saturday, Sunday) and report a weighted average.
- **Compare against driving.** Use OSRM or Google Distance Matrix API to get driving times for the same OD pairs. Report TQI as a fraction of car accessibility.
- **Longitudinal tracking.** Archive GTFS feeds monthly and track TQI over time to measure whether service is improving or degrading.

---

## 9. Quick-Start Pseudocode

```python
import pandas as pd
from scipy.spatial import cKDTree
from math import radians, cos, sin, asin, sqrt

# ── 1. Load GTFS ──
stops = pd.read_csv("gtfs/stops.txt")
stop_times = pd.read_csv("gtfs/stop_times.txt")
trips = pd.read_csv("gtfs/trips.txt")
calendar = pd.read_csv("gtfs/calendar.txt")

# ── 2. Filter to Chilliwack + target day (Wednesday) ──
active_services = calendar[calendar.wednesday == 1].service_id
chw_routes = [1,2,3,4,5,6,7,9,12,15,16,17,21,22,24,26,51,52,53,54,55,57,58,59,66]
# Join trips → routes, filter
active_trips = trips[
    trips.service_id.isin(active_services) & 
    trips.route_id.isin(get_route_ids_for(chw_routes))
]

# ── 3. Build stop time index ──
# For each stop: sorted list of (departure_time, trip_id, next_stop, arrival_at_next)
timetable = build_timetable(stop_times, active_trips)

# ── 4. Generate analysis grid ──
lat_range = np.linspace(49.130, 49.195, 30)  # ~250m spacing
lon_range = np.linspace(-121.985, -121.895, 40)
grid = [(lat, lon) for lat in lat_range for lon in lon_range]  # ~1200 points

# ── 5. Build spatial index for stops ──
stop_coords = stops[["stop_lat", "stop_lon"]].values
stop_tree = cKDTree(np.radians(stop_coords) * 6371000)  # meters approx

# ── 6. For each origin, each departure time: run RAPTOR ──
departure_times = range(6*60, 22*60, 15)  # minutes since midnight, every 15 min
results = {}

for origin in grid:
    nearby_stops = stop_tree.query_ball_point(
        np.radians(origin) * 6371000, r=800
    )
    for t_depart in departure_times:
        # RAPTOR: returns dict of {stop_id: earliest_arrival_time}
        arrivals = raptor(
            timetable, nearby_stops, origin, t_depart,
            max_transfers=2, max_time=t_depart + 90
        )
        results[(origin, t_depart)] = arrivals

# ── 7. Compute TQI ──
# For each OD pair, compute TSR and reachability
# Aggregate per Section 4
tqi = compute_tqi(results, grid, stops)
print(f"Chilliwack TQI: {tqi:.1f} / 100")
```

---

## 10. References

- **RAPTOR algorithm:** Delling, Pajor, Werneck (2012). "Round-Based Public Transit Routing." ALENEX.
- **GTFS accessibility analysis:** Farber, Morang, Widener (2014). "Temporal variability in transit-based accessibility."
- **r5py library:** [https://r5py.readthedocs.io/](https://r5py.readthedocs.io/) — Python wrapper for Conveyal R5.
- **GTFS2STN:** Khadka et al. (2024). "Analyzing Transit Systems Using GTFS by Generating Spatiotemporal Networks." MDPI Information.
- **BC Transit Open Data:** [https://www.bctransit.com/open-data/](https://www.bctransit.com/open-data/)
