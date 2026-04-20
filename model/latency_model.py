"""
Latency model: standard fibre vs hollow-core fibre vs Starlink.

All distances in km, times in ms, speeds in km/s.
Physics is deliberately simple and fully cited — see refs in docs/index.html.
"""
from __future__ import annotations
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

C_KMS = 299_792.458                 # speed of light in vacuum, km/s
N_SMF = 1.468                       # effective group index of standard single-mode silica fibre (ITU-T G.652)
V_SMF = C_KMS / N_SMF               # ≈ 204,218 km/s  (≈ 0.681 c)
V_HCF = 0.9970 * C_KMS              # hollow-core NANF, Microsoft/Lumenisity published figure
V_VAC = C_KMS                       # Starlink: c in vacuum, ~c in atmosphere

EARTH_R_KM = 6371.0
STARLINK_ALT_KM = 550.0             # Gen1/Gen2 shell altitude
T_SAT_PROC_MS = 1.0                 # per-satellite processing + pointing + queuing budget (conservative)
T_GS_PROC_MS = 2.0                  # ground-station bent-pipe processing
T_ROUTER_MS = 0.05                  # ~50 µs per terrestrial router hop
N_ROUTER_HOPS = 8                   # typical long-haul traceroute hop count


# ---------- geometry ----------

def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine great-circle distance in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def leo_arc_km(gc_km: float, alt_km: float = STARLINK_ALT_KM) -> float:
    """Great-circle distance scaled to orbital radius — the ISL path length at altitude."""
    return gc_km * (EARTH_R_KM + alt_km) / EARTH_R_KM


# ---------- endpoints ----------

CITIES = {
    "London":    (51.5074,  -0.1278),
    "New York":  (40.7128, -74.0060),
    "Sydney":   (-33.8688, 151.2093),
}

# Submarine-cable routed distance (not great-circle) — sourced from TeleGeography
# London↔NYC: Grace Hopper 7,530 km; AEConnect 5,536 km; EXA Express 5,218 km; TAT-14 legs ~5,800 km.
#             Representative long-haul production path: 6,200 km.
# London↔Sydney: no direct cable. Two realistic routings:
#   (a) via Suez / SEA-ME-WE / SMW6: ~23,500 km
#   (b) via USA (trans-Atlantic + trans-US + trans-Pacific): ~21,500 km
#             Representative: 22,000 km.
CABLE_KM = {
    ("London", "New York"): 6_200.0,
    ("London", "Sydney"):  22_000.0,
}


# ---------- model ----------

@dataclass
class Result:
    route: str
    tech: str
    path_km: float
    speed_kms: float
    propagation_ms: float
    overhead_ms: float
    one_way_ms: float
    rtt_ms: float
    notes: str


def fibre_result(route: str, tech: str, v: float, cable_km: float, notes: str) -> Result:
    prop = cable_km / v * 1000.0
    overhead = N_ROUTER_HOPS * T_ROUTER_MS
    one_way = prop + overhead
    return Result(route, tech, cable_km, v, prop, overhead, one_way, 2 * one_way, notes)


def starlink_idealised(route: str, gc_km: float) -> Result:
    """Pure LEO + ISL great-circle — the physical upper bound for Starlink."""
    arc = leo_arc_km(gc_km)
    up_down = 2 * STARLINK_ALT_KM                     # ground → sat, sat → ground
    # Hop count roughly every ~2,000 km of arc (rough ISL geometry); each hop adds processing
    n_hops = max(1, round(arc / 2_000))
    path = arc + up_down
    prop = path / C_KMS * 1000.0
    overhead = n_hops * T_SAT_PROC_MS + 2 * T_GS_PROC_MS
    one_way = prop + overhead
    notes = f"LEO great-circle at {STARLINK_ALT_KM:.0f} km, {n_hops} ISL hops, c in vacuum."
    return Result(route, "Starlink (ideal LEO+ISL)", path, C_KMS, prop, overhead, one_way, 2 * one_way, notes)


def starlink_realistic(route: str, gc_km: float, fibre_backhaul_km: float, backhaul_v: float) -> Result:
    """
    Realistic 'today' model: LEO first/last mile, terrestrial fibre across ocean basins
    where the ISL mesh doesn't yet form a usable path.
    """
    up_down = 2 * STARLINK_ALT_KM
    # Assume 500 km of LEO on each side before handing off to a ground gateway
    leo_segment = 2 * leo_arc_km(500.0)
    sat_prop = (up_down + leo_segment) / C_KMS * 1000.0
    fibre_prop = fibre_backhaul_km / backhaul_v * 1000.0
    overhead = 2 * T_SAT_PROC_MS + 4 * T_GS_PROC_MS + N_ROUTER_HOPS * T_ROUTER_MS
    one_way = sat_prop + fibre_prop + overhead
    path = up_down + leo_segment + fibre_backhaul_km
    notes = (
        f"LEO access hop each side, plus {fibre_backhaul_km:,.0f} km of terrestrial/submarine "
        "fibre where the ISL mesh gap exists."
    )
    return Result(route, "Starlink (realistic today)", path, 0.0, sat_prop + fibre_prop, overhead, one_way, 2 * one_way, notes)


def build_all() -> list[Result]:
    results: list[Result] = []
    for (a, b), cable_km in CABLE_KM.items():
        route = f"{a} ↔ {b}"
        gc = great_circle_km(*CITIES[a], *CITIES[b])

        results.append(fibre_result(
            route, "Standard SMF fibre", V_SMF, cable_km,
            f"n={N_SMF}, v≈{V_SMF:,.0f} km/s (~0.681 c). Cable route {cable_km:,.0f} km vs great-circle {gc:,.0f} km."
        ))
        results.append(fibre_result(
            route, "Hollow-core fibre (NANF)", V_HCF, cable_km,
            f"v=0.997 c ≈ {V_HCF:,.0f} km/s. Same cable routing; latency saving is pure physics."
        ))
        results.append(starlink_idealised(route, gc))
        # "Realistic today": assume the transoceanic leg rides fibre at SMF speed
        if (a, b) == ("London", "Sydney"):
            results.append(starlink_realistic(route, gc, fibre_backhaul_km=20_000.0, backhaul_v=V_SMF))
        elif (a, b) == ("London", "New York"):
            results.append(starlink_realistic(route, gc, fibre_backhaul_km=5_000.0, backhaul_v=V_SMF))
    return results


def main(out: Path) -> None:
    rows = [asdict(r) for r in build_all()]
    out.write_text(json.dumps({
        "constants": {
            "c_kms": C_KMS, "n_smf": N_SMF, "v_smf_kms": V_SMF,
            "v_hcf_kms": V_HCF, "v_hcf_frac_c": 0.997,
            "starlink_alt_km": STARLINK_ALT_KM,
        },
        "cities": {k: {"lat": v[0], "lon": v[1]} for k, v in CITIES.items()},
        "cable_km": {f"{a}↔{b}": v for (a, b), v in CABLE_KM.items()},
        "results": rows,
    }, indent=2, ensure_ascii=False))
    print(f"wrote {out} with {len(rows)} rows")
    for r in rows:
        print(f"  {r['route']:22s}  {r['tech']:30s}  one-way {r['one_way_ms']:6.1f} ms   RTT {r['rtt_ms']:6.1f} ms")


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "data" / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    main(out)
