# -*- coding: utf-8 -*-
import os
"""
Created on Thu Sep 10 11:40:05 2026

@author: Asteris
"""

import pandas as pd
from pathlib import Path


# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

schedule_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_ontime_jan2023_model_ready.csv"
)

output_folder = (
    base_folder
    / "initial_conditions"
)

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

# Detailed tail-level audit file
tail_output_file = (
    output_folder
    / "envoy_tail_initial_positions_proxy.csv"
)

# Aggregated file that will later enter the FAM
initial_positions_file = (
    output_folder
    / "envoy_initial_aircraft_positions.csv"
)


# ============================================================
# 2. LOAD SCHEDULE
# ============================================================

schedule = pd.read_csv(schedule_file)

print("Schedule rows:", len(schedule))


# ============================================================
# 3. BASIC VALIDATION
# ============================================================

required_columns = [
    "Tail_Number",
    "AIRCRAFT_TYPE",
    "Origin",
    "Dest",
    "DEP_REFERENCE_TIME",
    "Cancelled"
]

missing_columns = [
    col
    for col in required_columns
    if col not in schedule.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# 4. CREATE USABLE TAIL SCHEDULE FOR INITIAL POSITION INFERENCE
# ============================================================
#
# A flight can be used to infer the initial physical position
# of a tail only if:
#
# - Tail number is known
# - Aircraft type is known
# - Flight was not cancelled
#
# IMPORTANT:
# Cancelled flights are NOT removed from the FAM schedule.
# They are excluded only from this proxy initial-position
# inference.
#

tail_schedule = schedule[
    schedule["Tail_Number"].notna()
    & schedule["AIRCRAFT_TYPE"].notna()
    & (schedule["Cancelled"] == 0)
].copy()

print(
    "Rows usable for tail-position inference:",
    len(tail_schedule)
)

print(
    "Rows excluded from tail-position inference:",
    len(schedule) - len(tail_schedule)
)

# ============================================================
# 5. PARSE COMMON REFERENCE DEPARTURE TIME
# ============================================================

tail_schedule["DEP_REFERENCE_TIME"] = pd.to_datetime(
    tail_schedule["DEP_REFERENCE_TIME"]
)

if tail_schedule["DEP_REFERENCE_TIME"].isna().any():
    raise ValueError(
        "Some DEP_REFERENCE_TIME values could not be parsed."
    )


# ============================================================
# 6. VALIDATE ONE AIRCRAFT TYPE PER TAIL
# ============================================================

types_per_tail = (
    tail_schedule
    .groupby("Tail_Number")["AIRCRAFT_TYPE"]
    .nunique()
)

multi_type_tails = types_per_tail[
    types_per_tail > 1
]

print("\nTails mapped to more than one aircraft type:")
print(len(multi_type_tails))

if len(multi_type_tails) > 0:
    print(multi_type_tails)

    raise ValueError(
        "At least one tail is mapped to multiple aircraft types."
    )


# ============================================================
# 7. FIND FIRST OBSERVED DEPARTURE OF EACH TAIL
# ============================================================
#
# [INFERENCE / PROXY]
#
# For each tail number:
#
#   initial airport
#   =
#   Origin of its earliest scheduled departure
#   within the January 2023 schedule.
#
# We assume the aircraft is already positioned at that airport
# at the beginning of the optimization horizon.
#

tail_schedule = tail_schedule.sort_values(
    [
        "DEP_REFERENCE_TIME",
        "Tail_Number"
    ]
)

first_flights = (
    tail_schedule
    .drop_duplicates(
        subset=["Tail_Number"],
        keep="first"
    )
    .copy()
)


# ============================================================
# 8. CREATE TAIL-LEVEL INITIAL POSITION TABLE
# ============================================================

tail_initial_positions = first_flights[
    [
        "Tail_Number",
        "AIRCRAFT_TYPE",
        "Origin",
        "DEP_REFERENCE_TIME",
        "FlightDate",
        "Flight_Number_Reporting_Airline"
    ]
].copy()

tail_initial_positions = tail_initial_positions.rename(
    columns={
        "Origin": "INITIAL_AIRPORT",
        "DEP_REFERENCE_TIME": "FIRST_OBSERVED_DEPARTURE"
    }
)

tail_initial_positions[
    "INITIAL_POSITION_METHOD"
] = "FIRST_OBSERVED_DEPARTURE_PROXY"


# ============================================================
# 9. VALIDATE UNIQUE TAIL COUNT
# ============================================================

print("\n===================================")
print("TAIL-LEVEL INITIAL POSITIONS")
print("===================================")

print(
    "Unique tails:",
    tail_initial_positions["Tail_Number"].nunique()
)

print("\nUnique tails by aircraft type:")

tail_counts = (
    tail_initial_positions
    .groupby("AIRCRAFT_TYPE")["Tail_Number"]
    .nunique()
    .sort_index()
)

print(tail_counts)


# ============================================================
# 10. EXPECTED FLEET VALIDATION
# ============================================================
#
# [PUBLIC DATA / OUR FAA MAPPING]
#
# The January schedule + FAA mapping produced:
#
# ERJ145 = 28
# ERJ170 = 8
# ERJ175 = 101
#
# Note:
# The paper contains an internal inconsistency:
# one section reports 101 ERJ175, another reports 103.
# We use the fleet actually observed in our processed data.
#

expected_fleet = {
    "ERJ145": 28,
    "ERJ170": 8,
    "ERJ175": 101
}

print("\nFleet-count validation:")

for aircraft, expected_count in expected_fleet.items():

    actual_count = int(
        tail_counts.get(
            aircraft,
            0
        )
    )

    print(
        f"{aircraft}: "
        f"{actual_count} "
        f"(expected {expected_count})"
    )

    if actual_count != expected_count:

        raise ValueError(
            f"Unexpected fleet count for {aircraft}: "
            f"{actual_count}, expected {expected_count}"
        )


print(
    "\nTotal fleet:",
    tail_initial_positions["Tail_Number"].nunique()
)


# ============================================================
# 11. AGGREGATE INTO y[a,p,0]
# ============================================================
#
# y[a,p,0]
# =
# number of aircraft of type a initially located at airport p
#

nonzero_positions = (
    tail_initial_positions
    .groupby(
        [
            "AIRCRAFT_TYPE",
            "INITIAL_AIRPORT"
        ]
    )
    .size()
    .reset_index(
        name="INITIAL_COUNT"
    )
)


# ============================================================
# 12. CREATE COMPLETE TYPE × AIRPORT TABLE
# ============================================================
#
# For the FAM it is convenient to explicitly have zero values
# as well.
#
# 135 airports × 3 aircraft types = 405 possible combinations.
#

all_airports = sorted(
    schedule["Origin"]
    .dropna()
    .tolist()
    +
    schedule["Dest"]
    .dropna()
    .tolist()
)

all_airports = sorted(
    set(all_airports)
)

aircraft_types = [
    "ERJ145",
    "ERJ170",
    "ERJ175"
]

complete_index = pd.MultiIndex.from_product(
    [
        aircraft_types,
        all_airports
    ],
    names=[
        "AIRCRAFT_TYPE",
        "AIRPORT"
    ]
)

initial_positions = (
    nonzero_positions
    .rename(
        columns={
            "INITIAL_AIRPORT": "AIRPORT"
        }
    )
    .set_index(
        [
            "AIRCRAFT_TYPE",
            "AIRPORT"
        ]
    )
    .reindex(
        complete_index,
        fill_value=0
    )
    .reset_index()
)


# ============================================================
# 13. FINAL VALIDATION
# ============================================================

print("\n===================================")
print("INITIAL POSITION VALIDATION")
print("===================================")

print("\nNumber of airports:")
print(len(all_airports))

print("\nTotal type-airport combinations:")
print(len(initial_positions))

print("\nNon-zero initial positions:")
print(
    (
        initial_positions["INITIAL_COUNT"] > 0
    ).sum()
)


print("\nTotal initial aircraft by type:")

validation = (
    initial_positions
    .groupby("AIRCRAFT_TYPE")[
        "INITIAL_COUNT"
    ]
    .sum()
)

print(validation)


print("\nTotal initial aircraft:")
print(
    initial_positions[
        "INITIAL_COUNT"
    ].sum()
)


# ============================================================
# 14. SHOW NON-ZERO POSITIONS
# ============================================================

print("\n===================================")
print("NON-ZERO INITIAL AIRCRAFT POSITIONS")
print("===================================")

print(
    initial_positions[
        initial_positions["INITIAL_COUNT"] > 0
    ]
    .sort_values(
        [
            "AIRCRAFT_TYPE",
            "INITIAL_COUNT"
        ],
        ascending=[
            True,
            False
        ]
    )
    .to_string(index=False)
)


# ============================================================
# 15. SAVE OUTPUTS
# ============================================================

tail_initial_positions.to_csv(
    tail_output_file,
    index=False
)

initial_positions.to_csv(
    initial_positions_file,
    index=False
)

print("\n===================================")
print("FILES SAVED")
print("===================================")

print("\nTail-level audit file:")
print(tail_output_file)

print("\nFAM initial-position file:")
print(initial_positions_file)

