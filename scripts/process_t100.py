import os
import pandas as pd
from pathlib import Path

# ============================================================
# 1. LOAD RAW T-100 DATA
# ============================================================


base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

# Create T100 subfolder if it does not already exist
t100_folder = base_folder / "T100"
t100_folder.mkdir(parents=True, exist_ok=True)

# Raw input file
file_path = base_folder / "T100" / "T_T100D_SEGMENT_US_CARRIER_ONLY.csv"

# Load data
df = pd.read_csv(file_path)


# ============================================================
# 2. FILTER ENVOY AIR
# ============================================================

# MQ = Envoy Air
# F  = Scheduled Passenger/Cargo Service
# 1  = Passenger aircraft configuration

envoy = df[
    (df["UNIQUE_CARRIER"] == "MQ") &
    (df["CLASS"] == "F") &
    (df["AIRCRAFT_CONFIG"] == 1)
].copy()

print("Envoy rows:", len(envoy))


# ============================================================
# 3. KEEP ONLY USEFUL COLUMNS
# ============================================================

columns_to_keep = [
    "YEAR",
    "MONTH",
    "UNIQUE_CARRIER",
    "AIRLINE_ID",
    "ORIGIN",
    "DEST",
    "AIRCRAFT_TYPE",
    "DEPARTURES_PERFORMED",
    "PASSENGERS",
    "SEATS",
    "RAMP_TO_RAMP"
]

envoy_clean = envoy[columns_to_keep].copy()


# Optional: make aircraft type easier to read
aircraft_map = {
    673: "ERJ175",
    675: "ERJ145",
    677: "ERJ170"
}

envoy_clean["AIRCRAFT_NAME"] = (
    envoy_clean["AIRCRAFT_TYPE"].map(aircraft_map)
)


# ============================================================
# 4. CALCULATE PASSENGER DEMAND BY ROUTE
# ============================================================

# Important:
# We group only by Origin-Destination.
# If the same route was flown by multiple aircraft types,
# passengers and departures are added together.

route_demand = (
    envoy_clean
    .groupby(["ORIGIN", "DEST"], as_index=False)
    .agg(
        TOTAL_DEPARTURES=("DEPARTURES_PERFORMED", "sum"),
        TOTAL_PASSENGERS=("PASSENGERS", "sum")
    )
)


# Remove routes with zero performed departures
route_demand = route_demand[
    route_demand["TOTAL_DEPARTURES"] > 0
].copy()


# Average passenger demand per flight
route_demand["AVG_PAX_PER_FLIGHT"] = (
    route_demand["TOTAL_PASSENGERS"]
    / route_demand["TOTAL_DEPARTURES"]
)


# ============================================================
# 5. SORT RESULTS
# ============================================================

route_demand = route_demand.sort_values(
    by=["ORIGIN", "DEST"]
).reset_index(drop=True)


# ============================================================
# 6. SAVE OUTPUT FILES
# ============================================================

envoy_clean.to_csv(
    t100_folder / "envoy_t100_jan2023_clean.csv",
    index=False
)

route_demand.to_csv(
    t100_folder / "envoy_t100_jan2023_demand.csv",
    index=False
)

print("\nFiles saved in:")
print(t100_folder)


# ============================================================
# 7. PRINT SAMPLE RESULTS
# ============================================================

print("\nClean Envoy T-100 data:")
print(envoy_clean.head())

print("\nRoute demand:")
print(route_demand.head(10))

print("\nNumber of OD routes:", len(route_demand))

