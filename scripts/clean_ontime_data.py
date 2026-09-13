import os

import pandas as pd
from pathlib import Path

# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

ontime_folder = base_folder / "on_time_data"

input_file = (
    ontime_folder
    / "On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2023_1.csv"
)

output_folder = ontime_folder / "processed"
output_folder.mkdir(parents=True, exist_ok=True)

output_file = (
    output_folder
    / "envoy_ontime_jan2023_clean.csv"
)


# ============================================================
# 2. COLUMNS WE WANT TO KEEP
# ============================================================

columns_to_keep = [
    "FlightDate",
    "Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "Tail_Number",
    "Origin",
    "Dest",
    "CRSDepTime",
    "CRSArrTime",
    "DepTime",
    "ArrTime",
    "Cancelled",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "AirTime",
    "Distance"
]


# ============================================================
# 3. LOAD JANUARY 2023 ON-TIME DATA
# ============================================================

df = pd.read_csv(
    input_file,
    usecols=columns_to_keep
)

print("Total January 2023 records:", len(df))


# ============================================================
# 4. FILTER ENVOY AIR
# ============================================================

# MQ = Envoy Air
envoy = df[
    df["Reporting_Airline"] == "MQ"
].copy()

print("Envoy / MQ records:", len(envoy))


# ============================================================
# 5. SORT FLIGHTS
# ============================================================

envoy = envoy.sort_values(
    by=[
        "FlightDate",
        "CRSDepTime",
        "Origin",
        "Dest"
    ]
).reset_index(drop=True)


# ============================================================
# 6. BASIC VALIDATION
# ============================================================

unique_origins = envoy["Origin"].nunique()
unique_destinations = envoy["Dest"].nunique()

all_airports = set(envoy["Origin"]).union(
    set(envoy["Dest"])
)

unique_airports = len(all_airports)

cancelled_flights = int(
    envoy["Cancelled"].sum()
)

diverted_flights = int(
    envoy["Diverted"].sum()
)

missing_tail_numbers = int(
    envoy["Tail_Number"].isna().sum()
)


# ============================================================
# 7. SAVE CLEAN DATA
# ============================================================

envoy.to_csv(
    output_file,
    index=False
)


# ============================================================
# 8. PRINT RESULTS
# ============================================================

print("\n-----------------------------------")
print("ENVOY JANUARY 2023 SCHEDULE")
print("-----------------------------------")

print("Flights:", len(envoy))
print("Unique origins:", unique_origins)
print("Unique destinations:", unique_destinations)
print("Unique airports:", unique_airports)
print("Cancelled flights:", cancelled_flights)
print("Diverted flights:", diverted_flights)
print("Missing tail numbers:", missing_tail_numbers)


print("\nFirst 10 flights:")
print(
    envoy[
        [
            "FlightDate",
            "Flight_Number_Reporting_Airline",
            "Tail_Number",
            "Origin",
            "Dest",
            "CRSDepTime",
            "CRSArrTime",
            "Cancelled",
            "Diverted"
        ]
    ].head(10)
)


# ============================================================
# 9. CONFIRM OUTPUT
# ============================================================

print("\n-----------------------------------")
print("OUTPUT FILE")
print("-----------------------------------")

print("Saved at:")
print(output_file)

print("\nFile exists:", output_file.exists())

