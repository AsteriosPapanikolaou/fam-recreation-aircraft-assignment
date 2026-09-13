# -*- coding: utf-8 -*-
import os
"""
Created on Wed Sep  9 17:23:02 2026

@author: Asteris
"""

import pandas as pd
from pathlib import Path


# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

financial_folder = base_folder / "financial"

input_file = (
    financial_folder
    / "T_F41SCHEDULE_P52.csv"
)

output_file = (
    financial_folder
    / "envoy_p52_q1_2023_operating_expenses.csv"
)


# ============================================================
# 2. LOAD P-5.2 DATA
# ============================================================

df = pd.read_csv(input_file)

print("Raw rows:", len(df))
print("Raw columns:", len(df.columns))


# ============================================================
# 3. FILTER ENVOY AIR — Q1 2023
# ============================================================

envoy = df[
    (df["YEAR"] == 2023)
    & (df["QUARTER"] == 1)
    & (df["UNIQUE_CARRIER"] == "MQ")
].copy()

print("\nEnvoy Q1 2023 rows:")
print(len(envoy))


# ============================================================
# 4. AIRCRAFT TYPE MAPPING
# ============================================================

aircraft_type_map = {
    673: "ERJ175",
    675: "ERJ145",
    677: "ERJ170"
}

envoy["AIRCRAFT_MODEL"] = (
    envoy["AIRCRAFT_TYPE"]
    .map(aircraft_type_map)
)


# ============================================================
# 5. INSPECT RAW ENVOY EXPENSE ROWS
# ============================================================

print("\nRaw Envoy operating-expense rows:")

print(
    envoy[
        [
            "AIRCRAFT_TYPE",
            "AIRCRAFT_MODEL",
            "REGION",
            "TOT_AIR_OP_EXPENSES"
        ]
    ]
    .sort_values(
        ["AIRCRAFT_TYPE", "REGION"]
    )
    .to_string(index=False)
)


# ============================================================
# 6. KEEP THE THREE AIRCRAFT TYPES USED IN THE PAPER
# ============================================================

envoy_clean = envoy[
    envoy["AIRCRAFT_MODEL"].notna()
].copy()


# ============================================================
# 7. AGGREGATE ACROSS REGIONS
# ============================================================

expenses = (
    envoy_clean
    .groupby(
        "AIRCRAFT_MODEL",
        as_index=False
    )["TOT_AIR_OP_EXPENSES"]
    .sum()
)

expenses["TOTAL_AIR_OPERATING_EXPENSES_USD"] = (
    expenses["TOT_AIR_OP_EXPENSES"]
    * 1000
)

expenses = expenses.rename(
    columns={
        "AIRCRAFT_MODEL": "AIRCRAFT_TYPE",
        "TOT_AIR_OP_EXPENSES":
            "TOTAL_AIR_OPERATING_EXPENSES_1000_USD"
    }
)


# ============================================================
# 8. VALIDATION
# ============================================================

print("\n===================================")
print("P-5.2 Q1 2023 VALIDATION")
print("===================================")

print(
    expenses.to_string(index=False)
)

paper_values = {
    "ERJ145": 31_091_760,
    "ERJ170": 13_596_590,
    "ERJ175": 192_728_340
}

print("\nComparison with paper:")

for aircraft, paper_value in paper_values.items():

    our_value = expenses.loc[
        expenses["AIRCRAFT_TYPE"] == aircraft,
        "TOTAL_AIR_OPERATING_EXPENSES_USD"
    ].iloc[0]

    print(
        f"{aircraft}: "
        f"Our data = ${our_value:,.0f} | "
        f"Paper = ${paper_value:,.0f} | "
        f"Difference = ${our_value - paper_value:,.0f}"
    )


# ============================================================
# 9. SAVE CLEAN DATASET
# ============================================================

expenses.to_csv(
    output_file,
    index=False
)

print("\nSaved at:")
print(output_file)

