# -*- coding: utf-8 -*-
import os
"""
Created on Wed Sep  9 12:24:35 2026

@author: Asteris
"""

import pandas as pd
from pathlib import Path
from zoneinfo import ZoneInfo
import airportsdata


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
    / "envoy_ontime_jan2023_common_time_indexed.csv"
)

timezone_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_airport_timezones.csv"
)


# ============================================================
# 2. COMMON REFERENCE TIMEZONE
# ============================================================

# All flights will be expressed using Central Time.
reference_timezone = ZoneInfo("America/Chicago")


# ============================================================
# 3. LOAD FLIGHT DATA
# ============================================================

df = pd.read_csv(input_file)

df["FlightDate"] = pd.to_datetime(
    df["FlightDate"]
)


# ============================================================
# 4. LOAD AIRPORT TIMEZONES
# ============================================================

iata_airports = airportsdata.load("IATA")

all_airports = sorted(
    set(df["Origin"]).union(
        set(df["Dest"])
    )
)

airport_timezone_rows = []

for airport in all_airports:

    airport_info = iata_airports.get(airport)

    if airport_info is None:
        timezone = None
    else:
        timezone = airport_info["tz"]

    airport_timezone_rows.append(
        {
            "AIRPORT": airport,
            "TIMEZONE": timezone
        }
    )


airport_timezones = pd.DataFrame(
    airport_timezone_rows
)

airport_timezones.to_csv(
    timezone_file,
    index=False
)


# ============================================================
# 5. CHECK FOR MISSING TIMEZONES
# ============================================================

missing_timezones = airport_timezones[
    airport_timezones["TIMEZONE"].isna()
    | (airport_timezones["TIMEZONE"] == "")
]

print("Total airports:", len(airport_timezones))
print("Missing airport timezones:", len(missing_timezones))

if len(missing_timezones) > 0:

    print("\nAirports with missing timezone:")
    print(missing_timezones)

    raise ValueError(
        "Some airports do not have timezone information."
    )


timezone_map = dict(
    zip(
        airport_timezones["AIRPORT"],
        airport_timezones["TIMEZONE"]
    )
)


# ============================================================
# 6. FUNCTION: BUILD LOCAL DATETIME FROM BTS HHMM
# ============================================================

def build_naive_datetime(date, hhmm):

    if pd.isna(hhmm):
        return pd.NaT

    hhmm = int(hhmm)

    hour = hhmm // 100
    minute = hhmm % 100

    day_offset = 0

    # Safety for possible BTS value 2400
    if hour == 24 and minute == 0:
        hour = 0
        day_offset = 1

    return (
        pd.Timestamp(date)
        + pd.Timedelta(days=day_offset)
        + pd.Timedelta(hours=hour)
        + pd.Timedelta(minutes=minute)
    )


# ============================================================
# 7. CONVERT EACH FLIGHT TO COMMON REFERENCE TIME
# ============================================================

def convert_flight_time(row):

    origin_timezone = ZoneInfo(
        timezone_map[row["Origin"]]
    )

    destination_timezone = ZoneInfo(
        timezone_map[row["Dest"]]
    )

    # Local clock times from BTS
    dep_naive = build_naive_datetime(
        row["FlightDate"],
        row["CRSDepTime"]
    )

    arr_naive = build_naive_datetime(
        row["FlightDate"],
        row["CRSArrTime"]
    )

    # Attach correct airport timezone
    dep_local = dep_naive.tz_localize(
        origin_timezone
    )

    arr_local = arr_naive.tz_localize(
        destination_timezone
    )

    # Convert both to Central Time
    dep_reference = dep_local.tz_convert(
        reference_timezone
    )

    arr_reference = arr_local.tz_convert(
        reference_timezone
    )

    overnight = False

    # If arrival is really on the next calendar day
    if arr_reference <= dep_reference:

        arr_naive = (
            arr_naive
            + pd.Timedelta(days=1)
        )

        arr_local = arr_naive.tz_localize(
            destination_timezone
        )

        arr_reference = arr_local.tz_convert(
            reference_timezone
        )

        overnight = True

    return pd.Series(
        {
            "ORIGIN_TIMEZONE":
                timezone_map[row["Origin"]],

            "DEST_TIMEZONE":
                timezone_map[row["Dest"]],

            "DEP_REFERENCE_TIME":
                dep_reference,

            "ARR_REFERENCE_TIME":
                arr_reference,

            "OVERNIGHT_CORRECTION":
                overnight
        }
    )


converted_times = df.apply(
    convert_flight_time,
    axis=1
)

df = pd.concat(
    [df, converted_times],
    axis=1
)


# ============================================================
# 8. VALIDATE AGAINST CRS ELAPSED TIME
# ============================================================

df["REFERENCE_ELAPSED_MIN"] = (
    (
        df["ARR_REFERENCE_TIME"]
        - df["DEP_REFERENCE_TIME"]
    ).dt.total_seconds()
    / 60
)

df["ELAPSED_DIFF_MIN"] = (
    df["REFERENCE_ELAPSED_MIN"]
    - df["CRSElapsedTime"]
)


# ============================================================
# 9. ROUND DOWN TO 15-MINUTE INTERVALS
# ============================================================

df["DEP_REFERENCE_15MIN"] = (
    df["DEP_REFERENCE_TIME"]
    .dt.floor("15min")
)

df["ARR_REFERENCE_15MIN"] = (
    df["ARR_REFERENCE_TIME"]
    .dt.floor("15min")
)


# ============================================================
# 10. CREATE COMMON TIME INDICES
# ============================================================

timeline_start = pd.Timestamp(
    "2023-01-01 00:00:00",
    tz=reference_timezone
)

df["DEP_TIME_INDEX_COMMON"] = (
    (
        df["DEP_REFERENCE_15MIN"]
        - timeline_start
    ).dt.total_seconds()
    // (15 * 60)
).astype(int)


df["ARR_TIME_INDEX_COMMON"] = (
    (
        df["ARR_REFERENCE_15MIN"]
        - timeline_start
    ).dt.total_seconds()
    // (15 * 60)
).astype(int)


# ============================================================
# 11. SAVE
# ============================================================

df.to_csv(
    output_file,
    index=False
)


# ============================================================
# 12. VALIDATION
# ============================================================

print("\n-----------------------------------")
print("COMMON TIME VALIDATION")
print("-----------------------------------")

print(
    "Overnight corrections:",
    df["OVERNIGHT_CORRECTION"].sum()
)

print(
    "Max absolute elapsed-time difference:",
    df["ELAPSED_DIFF_MIN"].abs().max(),
    "minutes"
)

print(
    "Flights with elapsed difference > 1 min:",
    (df["ELAPSED_DIFF_MIN"].abs() > 1).sum()
)

print(
    "Flights with ARR index <= DEP index:",
    (
        df["ARR_TIME_INDEX_COMMON"]
        <= df["DEP_TIME_INDEX_COMMON"]
    ).sum()
)

print(
    "Minimum departure index:",
    df["DEP_TIME_INDEX_COMMON"].min()
)

print(
    "Maximum departure index:",
    df["DEP_TIME_INDEX_COMMON"].max()
)

print(
    "Maximum arrival index:",
    df["ARR_TIME_INDEX_COMMON"].max()
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
            "ORIGIN_TIMEZONE",
            "DEST_TIMEZONE",
            "DEP_REFERENCE_TIME",
            "ARR_REFERENCE_TIME",
            "CRSElapsedTime",
            "REFERENCE_ELAPSED_MIN",
            "DEP_TIME_INDEX_COMMON",
            "ARR_TIME_INDEX_COMMON"
        ]
    ].head(10)
)


print("\nSaved at:")
print(output_file)

print("\nAirport timezone mapping saved at:")
print(timezone_file)

