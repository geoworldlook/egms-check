"""Internal-consistency checks for the tables transcribed from Fabris & Nazari (2026).

Purpose: catch transcription errors in data/04_Reference/*.csv before those files are used as
regression targets (files in data/04_Reference/). The checks use only relations stated in the article:

  1. Table 4 "before calibration" = CGNSS LOS velocity - mean EGMS PS velocity (200 m buffer).
  2. Table 4 "after calibration"  = "before" - "before" at the calibration station PTO1,
     same track (the article calibrates InSAR velocities to PTO1).
  3. The CGNSS LOS velocity is one value per (station, track).
  4. The number of PS does not decrease as the buffer radius grows.
  5. V_LOS = V_V * cos(theta) (article eq. 1): the incidence angle implied by Table 2 and
     Table 3 must be compatible with the Sentinel-1 IW incidence-angle range.

Units: all velocities in mm/yr, angles in degrees.
Sign convention: negative = subsidence / motion away from the satellite.

Run from the repository root:  python step_00_reference_check.py
Exit code 0 = all checks passed, 1 = at least one check failed.
"""

import csv
import math
import sys
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent / "data" / "04_Reference"

# All published values are rounded to 0.1 mm/yr, i.e. each carries up to +-0.05 mm/yr of
# rounding error. A difference of two rounded values compared with a third rounded value
# can therefore deviate by up to 0.15 mm/yr without any transcription error.
ROUNDING_HALF_STEP_MM_YR = 0.05
DIFF_TOLERANCE_MM_YR = 3 * ROUNDING_HALF_STEP_MM_YR + 1e-9

# Sentinel-1 Interferometric Wide swath incidence-angle range (near to far range), degrees.
# Nominal mission value; used only as a plausibility window, not as a processing parameter.
S1_IW_INCIDENCE_MIN_DEG = 29.1
S1_IW_INCIDENCE_MAX_DEG = 46.0

CALIBRATION_STATION = "PTO1"   # article section 2.4
REFERENCE_BUFFER_M = 200       # Table 4 is defined for the 200 m buffer


def read_rows(filename):
    with open(REFERENCE_DIR / filename, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    table2 = read_rows("fabris2026_tab2_gnss_vertical.csv")
    table3 = read_rows("fabris2026_tab3_egms_buffers.csv")
    table4 = read_rows("fabris2026_tab4_differences.csv")

    failures = []

    # --- Check 3: one CGNSS LOS value per (station, track) --------------------------------
    gnss_los = {}
    for row in table3:
        key = (row["station"], int(row["track"]))
        value = float(row["gnss_los_mm_yr"])
        if key in gnss_los and gnss_los[key] != value:
            failures.append(f"check 3: {key} has several CGNSS LOS values")
        gnss_los[key] = value

    # --- Check 4: PS count is non-decreasing with buffer radius ---------------------------
    counts = {}
    for row in table3:
        if row["selection"] == "buffer" and row["n_ps"] != "":
            key = (row["station"], int(row["track"]))
            counts.setdefault(key, []).append((int(row["radius_m"]), int(row["n_ps"])))
    for key, pairs in counts.items():
        pairs.sort()
        n_values = [n for _, n in pairs]
        if n_values != sorted(n_values):
            failures.append(f"check 4: {key} PS counts not monotonic: {pairs}")

    # --- Check 1: Table 4 'before' = CGNSS LOS - mean PS velocity (200 m) -----------------
    ps_200 = {}
    for row in table3:
        if row["selection"] == "buffer" and row["radius_m"] == str(REFERENCE_BUFFER_M):
            if row["ps_vel_mm_yr"] != "":
                ps_200[(row["station"], int(row["track"]))] = float(row["ps_vel_mm_yr"])

    before = {}
    print("Check 1: Table 4 (before calibration) vs Table 3")
    for row in table4:
        key = (row["station"], int(row["track"]))
        published = float(row["diff_before_calibration_mm_yr"])
        before[key] = published
        recomputed = gnss_los[key] - ps_200[key]
        deviation = abs(recomputed - published)
        status = "ok" if deviation <= DIFF_TOLERANCE_MM_YR else "FAIL"
        print(f"  {key[0]} track {key[1]:>3}: published {published:+.1f}, "
              f"recomputed {recomputed:+.2f}  [{status}]")
        if status == "FAIL":
            failures.append(f"check 1: {key} published {published} vs recomputed {recomputed:.2f}")

    # --- Check 2: Table 4 'after' = 'before' - 'before' at PTO1 on the same track ---------
    print("Check 2: Table 4 (after calibration) = before - before(PTO1)")
    for row in table4:
        key = (row["station"], int(row["track"]))
        published = float(row["diff_after_calibration_mm_yr"])
        recomputed = before[key] - before[(CALIBRATION_STATION, key[1])]
        deviation = abs(recomputed - published)
        status = "ok" if deviation <= DIFF_TOLERANCE_MM_YR else "FAIL"
        print(f"  {key[0]} track {key[1]:>3}: published {published:+.1f}, "
              f"recomputed {recomputed:+.2f}  [{status}]")
        if status == "FAIL":
            failures.append(f"check 2: {key} published {published} vs recomputed {recomputed:.2f}")

    # --- Check 5: implied incidence angle is plausible for Sentinel-1 IW ------------------
    # theta = arccos(V_LOS / V_V). Both inputs are rounded, so an interval is computed.
    print("Check 5: incidence angle implied by V_LOS = V_V * cos(theta)")
    vertical = {row["station"]: float(row["vv_2018_2022_mm_yr"]) for row in table2}
    for (station, track), v_los in sorted(gnss_los.items()):
        v_vert = vertical[station]
        ratio_low = (abs(v_los) - ROUNDING_HALF_STEP_MM_YR) / (abs(v_vert) + ROUNDING_HALF_STEP_MM_YR)
        ratio_high = (abs(v_los) + ROUNDING_HALF_STEP_MM_YR) / (abs(v_vert) - ROUNDING_HALF_STEP_MM_YR)
        if not 0.0 < ratio_low <= ratio_high < 1.0:
            failures.append(f"check 5: {station} track {track} cos(theta) interval "
                            f"[{ratio_low:.3f}, {ratio_high:.3f}] is not inside (0, 1)")
            continue
        theta_max_deg = math.degrees(math.acos(ratio_low))
        theta_min_deg = math.degrees(math.acos(ratio_high))
        overlaps = (theta_min_deg <= S1_IW_INCIDENCE_MAX_DEG
                    and theta_max_deg >= S1_IW_INCIDENCE_MIN_DEG)
        status = "ok" if overlaps else "FAIL"
        print(f"  {station} track {track:>3}: theta in [{theta_min_deg:.1f}, {theta_max_deg:.1f}] deg  [{status}]")
        if not overlaps:
            failures.append(f"check 5: {station} track {track} implied incidence angle "
                            f"[{theta_min_deg:.1f}, {theta_max_deg:.1f}] deg outside Sentinel-1 IW range")

    if failures:
        print("\nFAILED:")
        for message in failures:
            print("  -", message)
        return 1
    print("\nAll reference consistency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
