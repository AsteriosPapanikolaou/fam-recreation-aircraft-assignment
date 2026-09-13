# -*- coding: utf-8 -*-
import os
"""
Created on Wed Sep  9 10:57:40 2026

@author: Asteris
"""

import pandas as pd
from pathlib import Path

# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

input_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_ontime_jan2023_clean.csv"
)

output_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_ontime_jan2023_time_indexed.csv"
)


# ============================================================
# 2. LOAD DATA
# ============================================================

df = pd.read_csv(input_file)

df["FlightDate"] = pd.to_datetime(df["FlightDate"])


# ============================================================
# 3. FUNCTION: HHMM -> MINUTES AFTER MIDNIGHT
# ============================================================

def hhmm_to_minutes(value):

    value = int(value)

    hours = value // 100
    minutes = value % 100

    return hours * 60 + minutes


# ============================================================
# 4. CONVERT CRS TIMES TO MINUTES
# ============================================================

df["DEP_MINUTES"] = df["CRSDepTime"].apply(
    hhmm_to_minutes
)

df["ARR_MINUTES"] = df["CRSArrTime"].apply(
    hhmm_to_minutes
)


# ============================================================
# 5. BUILD SCHEDULED DATETIMES
# ============================================================

df["DEP_DATETIME"] = (
    df["FlightDate"]
    + pd.to_timedelta(
        df["DEP_MINUTES"],
        unit="m"
    )
)

df["ARR_DATETIME"] = (
    df["FlightDate"]
    + pd.to_timedelta(
        df["ARR_MINUTES"],
        unit="m"
    )
)


# ============================================================
# 6. HANDLE OVERNIGHT FLIGHTS
# ============================================================

# If scheduled arrival clock time is earlier than departure
# clock time, arrival takes place on the following day.

overnight_mask = (
    df["ARR_DATETIME"]
    < df["DEP_DATETIME"]
)

df.loc[
    overnight_mask,
    "ARR_DATETIME"
] += pd.Timedelta(days=1)

print(
    "Overnight flights:",
    overnight_mask.sum()
)


# ============================================================
# 7. ROUND DOWN TO NEAREST 15 MINUTES
# ============================================================

df["DEP_TIME_15MIN"] = (
    df["DEP_DATETIME"]
    .dt.floor("15min")
)

df["ARR_TIME_15MIN"] = (
    df["ARR_DATETIME"]
    .dt.floor("15min")
)


# ============================================================
# 8. CREATE TIME INDICES
# ============================================================

timeline_start = pd.Timestamp(
    "2023-01-01 00:00:00"
)

df["DEP_TIME_INDEX"] = (
    (
        df["DEP_TIME_15MIN"]
        - timeline_start
    ).dt.total_seconds()
    // (15 * 60)
).astype(int)

df["ARR_TIME_INDEX"] = (
    (
        df["ARR_TIME_15MIN"]
        - timeline_start
    ).dt.total_seconds()
    // (15 * 60)
).astype(int)


# ============================================================
# 9. SAVE
# ============================================================

df.to_csv(
    output_file,
    index=False
)


# ============================================================
# 10. CHECK RESULTS
# ============================================================

print("\n-----------------------------------")
print("TIME INDEX SUMMARY")
print("-----------------------------------")

print(
    "Minimum departure index:",
    df["DEP_TIME_INDEX"].min()
)

print(
    "Maximum departure index:",
    df["DEP_TIME_INDEX"].max()
)

print(
    "Minimum arrival index:",
    df["ARR_TIME_INDEX"].min()
)

print(
    "Maximum arrival index:",
    df["ARR_TIME_INDEX"].max()
)


print("\nSample flights:")

print(
    df[
        [
            "FlightDate",
            "Origin",
            "Dest",
            "CRSDepTime",
            "CRSArrTime",
            "DEP_DATETIME",
            "ARR_DATETIME",
            "DEP_TIME_15MIN",
            "ARR_TIME_15MIN",
            "DEP_TIME_INDEX",
            "ARR_TIME_INDEX"
        ]
    ].head(10)
)


print("\nSaved at:")
print(output_file)

print(
    "\nFile exists:",
    output_file.exists()
)

