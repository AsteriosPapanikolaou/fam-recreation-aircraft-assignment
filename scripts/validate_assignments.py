# -*- coding: utf-8 -*-
import os
"""
Created on Sun Sep 13 12:43:17 2026

@author: Asteris
"""

from pathlib import Path
import json
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

ACTUAL_PATH = (
    BASE / "on_time_data" / "processed"
    / "envoy_ontime_jan2023_with_faa_model.csv"
)

FAM_PATH = BASE / "Results" / "envoy_FAM_assignment_results.csv"

OUT = BASE / "Results" / "validation"
OUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# READ DATA
# ============================================================

actual = pd.read_csv(ACTUAL_PATH, low_memory=False)
fam = pd.read_csv(FAM_PATH, low_memory=False)


# ============================================================
# COMMON FLIGHT KEY
# ============================================================

KEY = [
    "FlightDate",
    "Flight_Number_Reporting_Airline",
    "Origin",
    "Dest",
]


def prepare_key(df):
    df = df.copy()

    df["FlightDate"] = (
        pd.to_datetime(df["FlightDate"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
    )

    df["Flight_Number_Reporting_Airline"] = (
        pd.to_numeric(
            df["Flight_Number_Reporting_Airline"],
            errors="coerce"
        )
        .astype("Int64")
        .astype(str)
    )

    df["Origin"] = df["Origin"].astype(str).str.strip().str.upper()
    df["Dest"] = df["Dest"].astype(str).str.strip().str.upper()

    return df


actual = prepare_key(actual)
fam = prepare_key(fam)


# ============================================================
# KEEP RELEVANT COLUMNS
# ============================================================

actual_small = actual[
    KEY
    + [
        "Tail_Number",
        "AIRCRAFT_TYPE",
        "Cancelled",
        "Diverted",
        "Distance",
    ]
].copy()

fam_small = fam[
    KEY
    + [
        "FLIGHT_ID",
        "Assigned_Aircraft",
        "Departure_slot",
        "Arrival_slot",
        "Distance",
        "Total_Assignment_Cost",
    ]
].copy()


# ============================================================
# CHECK DUPLICATES
# ============================================================

if actual_small.duplicated(KEY).any():
    raise ValueError("Υπάρχουν duplicate flight keys στο actual αρχείο.")

if fam_small.duplicated(KEY).any():
    raise ValueError("Υπάρχουν duplicate flight keys στο FAM αρχείο.")


# ============================================================
# MERGE ACTUAL WITH FAM
# ============================================================

comparison = actual_small.merge(
    fam_small,
    on=KEY,
    how="outer",
    suffixes=("_Actual", "_FAM"),
    indicator=True,
    validate="one_to_one",
)


comparison["Route"] = (
    comparison["Origin"] + "-" + comparison["Dest"]
)

comparison["Actual_Aircraft"] = comparison["AIRCRAFT_TYPE"]
comparison["FAM_Aircraft"] = comparison["Assigned_Aircraft"]


# ============================================================
# ELIGIBILITY
# Cancelled flights are excluded from aircraft matching
# ============================================================

comparison["Actual_Type_Available"] = (
    comparison["Actual_Aircraft"]
    .isin(["ERJ145", "ERJ170", "ERJ175"])
)

comparison["Actual_Operated"] = (
    comparison["Cancelled"].fillna(1).ne(1)
)

comparison["Comparison_Eligible"] = (
    comparison["_merge"].eq("both")
    & comparison["Actual_Type_Available"]
    & comparison["Actual_Operated"]
)


comparison["Assignment_Match"] = pd.NA

comparison.loc[
    comparison["Comparison_Eligible"],
    "Assignment_Match"
] = (
    comparison.loc[
        comparison["Comparison_Eligible"],
        "Actual_Aircraft"
    ]
    ==
    comparison.loc[
        comparison["Comparison_Eligible"],
        "FAM_Aircraft"
    ]
)


comparison["Comparison_Status"] = "not_eligible"

comparison.loc[
    comparison["Comparison_Eligible"]
    & comparison["Assignment_Match"].eq(True),
    "Comparison_Status"
] = "match"

comparison.loc[
    comparison["Comparison_Eligible"]
    & comparison["Assignment_Match"].eq(False),
    "Comparison_Status"
] = "mismatch"


# ============================================================
# EXPORT 1: COMPLETE COMPARISON
# ============================================================

comparison.to_csv(
    OUT / "assignment_comparison.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# EXPORT 2: ONLY MISMATCHES
# ============================================================

mismatches = comparison[
    comparison["Comparison_Status"].eq("mismatch")
].copy()

mismatches.to_csv(
    OUT / "assignment_mismatches.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# CONFUSION MATRIX
# Rows    = actual aircraft
# Columns = FAM assigned aircraft
# ============================================================

TYPES = ["ERJ145", "ERJ170", "ERJ175"]

eligible = comparison[
    comparison["Comparison_Eligible"]
].copy()

confusion_matrix = pd.crosstab(
    eligible["Actual_Aircraft"],
    eligible["FAM_Aircraft"]
).reindex(
    index=TYPES,
    columns=TYPES,
    fill_value=0
)

confusion_matrix.index.name = "Actual_Aircraft"
confusion_matrix.columns.name = "FAM_Assigned_Aircraft"

confusion_matrix.to_csv(
    OUT / "assignment_confusion_matrix.csv",
    encoding="utf-8-sig"
)


# ============================================================
# FLEET DISTRIBUTION
# ============================================================

fleet_distribution = pd.DataFrame({
    "Actual": eligible["Actual_Aircraft"]
        .value_counts()
        .reindex(TYPES, fill_value=0),

    "FAM": eligible["FAM_Aircraft"]
        .value_counts()
        .reindex(TYPES, fill_value=0),
})

fleet_distribution.to_csv(
    OUT / "fleet_distribution_comparison.csv",
    encoding="utf-8-sig"
)


# ============================================================
# SUMMARY
# ============================================================

matched = int(
    eligible["Assignment_Match"].eq(True).sum()
)

mismatched = int(
    eligible["Assignment_Match"].eq(False).sum()
)

eligible_count = len(eligible)

summary = {
    "actual_rows": int(len(actual)),
    "fam_rows": int(len(fam)),
    "eligible_rows": eligible_count,
    "matched_rows": matched,
    "mismatched_rows": mismatched,
    "match_percentage": (
        matched / eligible_count * 100
        if eligible_count > 0 else 0
    ),
    "not_eligible_rows": int(
        (~comparison["Comparison_Eligible"]).sum()
    ),
    "outputs_folder": "Results/validation",
}

with open(
    OUT / "validation_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=2)


# ============================================================
# PRINT RESULTS
# ============================================================

print("\nVALIDATION RESULTS")
print("=" * 60)
print(f"Actual rows:       {len(actual):,}")
print(f"FAM rows:          {len(fam):,}")
print(f"Eligible rows:     {eligible_count:,}")
print(f"Matched rows:      {matched:,}")
print(f"Mismatched rows:   {mismatched:,}")
print(
    f"Match percentage:  "
    f"{summary['match_percentage']:.2f}%"
)

print("\nCONFUSION MATRIX")
print("=" * 60)
print(confusion_matrix)

print("\nOUTPUT FILES")
print("=" * 60)
print(OUT / "assignment_comparison.csv")
print(OUT / "assignment_mismatches.csv")
print(OUT / "assignment_confusion_matrix.csv")
print(OUT / "fleet_distribution_comparison.csv")
print(OUT / "validation_summary.json")

