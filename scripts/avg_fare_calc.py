# -*- coding: utf-8 -*-
import os
"""
Created on Tue Sep  8 19:11:40 2026

@author: Asteris
"""

import pandas as pd
from pathlib import Path

# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

db1b_file = (
    base_folder
    / "DB1B"
    / "processed"
    / "envoy_db1b_q1_2023_clean.csv"
)

output_folder = base_folder / "DB1B" / "processed"


# ============================================================
# 2. LOAD CLEAN ENVOY DB1B DATA
# ============================================================

df = pd.read_csv(db1b_file)

print("DB1B Envoy rows:", len(df))


# ============================================================
# 3. REMOVE INVALID FARE RECORDS
# ============================================================

df = df[
    (df["MARKET_FARE"].notna()) &
    (df["PASSENGERS"] > 0) &
    (df["MARKET_FARE"] > 0)
].copy()


# ============================================================
# 4. CALCULATE PASSENGER-WEIGHTED FARE
# ============================================================

df["FARE_X_PASSENGERS"] = (
    df["MARKET_FARE"] * df["PASSENGERS"]
)

route_fare = (
    df
    .groupby(["ORIGIN", "DEST"], as_index=False)
    .agg(
        TOTAL_DB1B_PASSENGERS=("PASSENGERS", "sum"),
        TOTAL_FARE_WEIGHT=("FARE_X_PASSENGERS", "sum"),
        DB1B_RECORDS=("MARKET_FARE", "count")
    )
)

route_fare["AVG_FARE"] = (
    route_fare["TOTAL_FARE_WEIGHT"]
    / route_fare["TOTAL_DB1B_PASSENGERS"]
)


# ============================================================
# 5. SORT
# ============================================================

route_fare = route_fare.sort_values(
    ["ORIGIN", "DEST"]
).reset_index(drop=True)


# ============================================================
# 6. SAVE
# ============================================================

route_fare.to_csv(
    output_folder / "envoy_db1b_q1_2023_route_fares.csv",
    index=False
)


# ============================================================
# 7. PRINT SAMPLE
# ============================================================

print("\nRoute fares:")
print(route_fare.head(10))

print("\nNumber of DB1B OD markets:", len(route_fare))

