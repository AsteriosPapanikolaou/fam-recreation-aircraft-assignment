import os


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
    / "envoy_ontime_jan2023_with_faa_model.csv"
)

output_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_ontime_jan2023_model_ready.csv"
)


# ============================================================
# 2. LOAD FULL PROCESSED DATASET
# ============================================================

df = pd.read_csv(input_file)

print("Input rows:", len(df))
print("Input columns:", len(df.columns))


# ============================================================
# 3. KEEP ONLY MODEL-RELEVANT COLUMNS
# ============================================================

model_columns = [
    "FlightDate",
    "Flight_Number_Reporting_Airline",
    "Origin",
    "Dest",

    "CRSDepTime",
    "CRSArrTime",
    "CRSElapsedTime",
    "Distance",

    "DEP_REFERENCE_TIME",
    "ARR_REFERENCE_TIME",
    "DEP_TIME_INDEX_COMMON",
    "ARR_TIME_INDEX_COMMON",

    "Tail_Number",
    "AIRCRAFT_TYPE",

    "Cancelled",
    "Diverted"
]


# Check that all required columns exist
missing_columns = [
    col for col in model_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


model_df = df[model_columns].copy()


# ============================================================
# 4. VALIDATION
# ============================================================

print("\nMODEL-READY DATASET")
print("-------------------")

print("Rows:", len(model_df))
print("Columns:", len(model_df.columns))

print("\nAircraft types:")
print(model_df["AIRCRAFT_TYPE"].value_counts(dropna=False))

print("\nUnique tails:")
print(model_df["Tail_Number"].nunique())


# ============================================================
# 5. SAVE
# ============================================================

model_df.to_csv(
    output_file,
    index=False
)

print("\nSaved at:")
print(output_file)

