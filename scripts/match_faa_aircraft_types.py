import os

import pandas as pd
from pathlib import Path


# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

faa_folder = (
    base_folder
    / "ReleasableAircraft"
)

schedule_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_ontime_jan2023_common_time_indexed.csv"
)

master_file = (
    faa_folder
    / "MASTER.txt"
)

acftref_file = (
    faa_folder
    / "ACFTREF.txt"
)

output_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_ontime_jan2023_with_faa_model.csv"
)


# ============================================================
# 2. LOAD ENVOY SCHEDULE
# ============================================================

df = pd.read_csv(schedule_file)

print("Schedule rows:", len(df))
print("Unique BTS tail numbers:", df["Tail_Number"].nunique())


# ============================================================
# 3. LOAD FAA MASTER
# ============================================================

master = pd.read_csv(
    master_file,
    encoding="utf-8-sig",
    usecols=[
        "N-NUMBER",
        "MFR MDL CODE"
    ],
    dtype=str
)


# Remove spaces that exist in FAA text fields
master["N-NUMBER"] = master["N-NUMBER"].str.strip()
master["MFR MDL CODE"] = master["MFR MDL CODE"].str.strip()


# ============================================================
# 4. LOAD FAA AIRCRAFT REFERENCE
# ============================================================

acftref = pd.read_csv(
    acftref_file,
    encoding="utf-8-sig",
    usecols=[
        "CODE",
        "MFR",
        "MODEL"
    ],
    dtype=str
)

acftref["CODE"] = acftref["CODE"].str.strip()
acftref["MFR"] = acftref["MFR"].str.strip()
acftref["MODEL"] = acftref["MODEL"].str.strip()


# ============================================================
# 5. PREPARE BTS TAIL NUMBER FOR FAA
# ============================================================

# Example:
# BTS: N123AB
# FAA: 123AB

df["FAA_N_NUMBER"] = (
    df["Tail_Number"]
    .str.strip()
    .str.upper()
    .str.replace(r"^N", "", regex=True)
)


# ============================================================
# 6. MERGE SCHEDULE WITH FAA MASTER
# ============================================================

df = df.merge(
    master,
    left_on="FAA_N_NUMBER",
    right_on="N-NUMBER",
    how="left",
    validate="many_to_one"
)


# ============================================================
# 7. MERGE WITH AIRCRAFT REFERENCE
# ============================================================

df = df.merge(
    acftref,
    left_on="MFR MDL CODE",
    right_on="CODE",
    how="left",
    validate="many_to_one"
)

def classify_aircraft(model):

    if pd.isna(model):
        return None

    model = model.strip().upper()

    if model in ["EMB-145", "EMB-145LR"]:
        return "ERJ145"

    elif model in ["ERJ 170-100 LR", "ERJ 170-100 STD"]:
        return "ERJ170"

    elif model == "ERJ 170-200 LR":
        return "ERJ175"

    else:
        return "UNKNOWN"


df["AIRCRAFT_TYPE"] = df["MODEL"].apply(
    classify_aircraft
)

# ============================================================
# 8. CHECK RESULTS
# ============================================================

print("\n-----------------------------------")
print("FAA MAPPING SUMMARY")
print("-----------------------------------")

print("Rows after merge:", len(df))

print(
    "Flights without FAA model:",
    df["MODEL"].isna().sum()
)

print(
    "Unique tails with FAA model:",
    df.loc[df["MODEL"].notna(), "Tail_Number"].nunique()
)

print("\nAircraft models found:")

print(
    df[
        ["MFR", "MODEL"]
    ]
    .dropna()
    .drop_duplicates()
    .sort_values(["MFR", "MODEL"])
    .to_string(index=False)
)

print("\nUnique aircraft by type:")

print(
    df.groupby("AIRCRAFT_TYPE")["Tail_Number"]
    .nunique()
)

# ============================================================
# CREATE CLEAN MODEL-READY SCHEDULE
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

model_df = df[model_columns].copy()


output_model_file = (
    base_folder
    / "on_time_data"
    / "processed"
    / "envoy_ontime_jan2023_model_ready.csv"
)

model_df.to_csv(
    output_model_file,
    index=False
)


print("Model-ready rows:", len(model_df))
print("Model-ready columns:", len(model_df.columns))

print("\nColumns:")
print(model_df.columns.tolist())

print("\nSaved at:")
print(output_model_file)

# ============================================================
# 9. SAVE
# ============================================================

df.to_csv(
    output_file,
    index=False
)

print("\nSaved at:")
print(output_file)




