# -*- coding: utf-8 -*-
import os
"""
Created on Tue Sep  8 19:17:09 2026

@author: Asteris
"""

import pandas as pd
from pathlib import Path

# ============================================================
# 1. BASE FOLDER
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))


# ============================================================
# 2. INPUT FILES
# ============================================================

t100_file = (
    base_folder
    / "T100"
    / "envoy_t100_jan2023_demand.csv"
)

db1b_file = (
    base_folder
    / "DB1B"
    / "processed"
    / "envoy_db1b_q1_2023_route_fares.csv"
)


# ============================================================
# 3. OUTPUT FOLDER
# ============================================================

output_folder = base_folder / "RouteInputs"
output_folder.mkdir(parents=True, exist_ok=True)

output_file = (
    output_folder
    / "route_inputs_jan2023.csv"
)


# ============================================================
# 4. LOAD DATA
# ============================================================

demand = pd.read_csv(t100_file)
fares = pd.read_csv(db1b_file)

print("T-100 demand rows:", len(demand))
print("DB1B fare rows:", len(fares))


# ============================================================
# 5. KEEP ONLY USEFUL DB1B COLUMNS
# ============================================================

fares_small = fares[
    [
        "ORIGIN",
        "DEST",
        "AVG_FARE"
    ]
].copy()


# ============================================================
# 6. MERGE T-100 DEMAND WITH DB1B FARES
# ============================================================

# Left merge:
# Keep all T-100 routes, even if no DB1B fare is available.

route_inputs = demand.merge(
    fares_small,
    on=["ORIGIN", "DEST"],
    how="left"
)


# ============================================================
# 7. SORT ROUTES
# ============================================================

route_inputs = route_inputs.sort_values(
    by=["ORIGIN", "DEST"]
).reset_index(drop=True)


# ============================================================
# 8. SAVE MERGED ROUTE INPUT FILE
# ============================================================

route_inputs.to_csv(
    output_file,
    index=False
)


# ============================================================
# 9. BASIC CHECKS
# ============================================================

total_routes = len(route_inputs)

routes_with_fare = (
    route_inputs["AVG_FARE"]
    .notna()
    .sum()
)

routes_missing_fare = (
    route_inputs["AVG_FARE"]
    .isna()
    .sum()
)

fare_coverage = (
    routes_with_fare
    / total_routes
    * 100
)


# ============================================================
# 10. PRINT RESULTS
# ============================================================

print("\nFirst 10 merged routes:")
print(route_inputs.head(10))

print("\n-----------------------------------")
print("ROUTE INPUT SUMMARY")
print("-----------------------------------")

print("Total T-100 routes:", total_routes)
print("Routes with fare:", routes_with_fare)
print("Routes missing fare:", routes_missing_fare)
print(f"Fare coverage: {fare_coverage:.2f}%")


# ============================================================
# 11. PRINT ROUTES WITH MISSING FARES
# ============================================================

missing_fares = route_inputs[
    route_inputs["AVG_FARE"].isna()
].copy()

print("\nRoutes with missing fare:")
print(
    missing_fares[
        [
            "ORIGIN",
            "DEST",
            "AVG_PAX_PER_FLIGHT"
        ]
    ]
)


# ============================================================
# 12. CONFIRM FILE SAVE
# ============================================================

print("\n-----------------------------------")
print("OUTPUT FILE")
print("-----------------------------------")

print("Saved at:")
print(output_file)

print("\nFile exists:", output_file.exists())

