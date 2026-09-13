import os
import pandas as pd
from pathlib import Path


# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

financial_folder = base_folder / "financial"

t100_file = (
    financial_folder
    / "T_T100D_SEGMENT_US_CARRIER_ONLY.csv"
)

expenses_file = (
    financial_folder
    / "envoy_p52_q1_2023_operating_expenses.csv"
)

output_file = (
    financial_folder
    / "envoy_q1_2023_cost_per_mile.csv"
)


# ============================================================
# 2. LOAD T-100
# ============================================================

t100 = pd.read_csv(t100_file)

print("T-100 raw rows:", len(t100))
print("T-100 raw columns:", len(t100.columns))

print("\nT-100 columns:")
print(t100.columns.tolist())


# ============================================================
# 3. FILTER ENVOY — Q1 2023
# ============================================================

t100_q1 = t100[
    (t100["MONTH"].isin([1, 2, 3]))
    & (t100["UNIQUE_CARRIER"] == "MQ")
].copy()

print("\nEnvoy Q1 rows before service filters:")
print(len(t100_q1))


# ============================================================
# 4. KEEP SCHEDULED PASSENGER OPERATIONS
# ============================================================

t100_q1 = t100_q1[
    (t100_q1["CLASS"] == "F")
    & (t100_q1["AIRCRAFT_CONFIG"] == 1)
].copy()

print("\nEnvoy Q1 rows after CLASS / CONFIG filter:")
print(len(t100_q1))


# ============================================================
# 5. AIRCRAFT TYPE MAPPING
# ============================================================

aircraft_type_map = {
    673: "ERJ175",
    675: "ERJ145",
    677: "ERJ170"
}

t100_q1["AIRCRAFT_MODEL"] = (
    t100_q1["AIRCRAFT_TYPE"]
    .map(aircraft_type_map)
)


print("\nAircraft type codes found in Envoy Q1:")
print(
    t100_q1[
        ["AIRCRAFT_TYPE", "AIRCRAFT_MODEL"]
    ]
    .drop_duplicates()
    .sort_values("AIRCRAFT_TYPE")
    .to_string(index=False)
)


# ============================================================
# 6. KEEP ONLY ERJ145 / ERJ170 / ERJ175
# ============================================================

t100_q1 = t100_q1[
    t100_q1["AIRCRAFT_MODEL"].notna()
].copy()


# ============================================================
# 7. CALCULATE MILES FLOWN
# ============================================================

t100_q1["MILES_FLOWN"] = (
    t100_q1["DISTANCE"]
    * t100_q1["DEPARTURES_PERFORMED"]
)


# ============================================================
# 8. AGGREGATE MILES BY AIRCRAFT TYPE
# ============================================================

miles = (
    t100_q1
    .groupby(
        "AIRCRAFT_MODEL",
        as_index=False
    )["MILES_FLOWN"]
    .sum()
)

miles = miles.rename(
    columns={
        "AIRCRAFT_MODEL": "AIRCRAFT_TYPE"
    }
)

print("\n===================================")
print("Q1 T-100 MILES")
print("===================================")

print(miles.to_string(index=False))


# ============================================================
# 9. LOAD P-5.2 OPERATING EXPENSES
# ============================================================

expenses = pd.read_csv(expenses_file)

print("\n===================================")
print("P-5.2 EXPENSES")
print("===================================")

print(expenses.to_string(index=False))


# ============================================================
# 10. CHECK AIRCRAFT TYPES BEFORE MERGE
# ============================================================

print("\nAircraft types in miles:")
print(miles["AIRCRAFT_TYPE"].unique())

print("\nAircraft types in expenses:")
print(expenses["AIRCRAFT_TYPE"].unique())


# ============================================================
# 11. MERGE EXPENSES + MILES
# ============================================================

financial = expenses.merge(
    miles,
    on="AIRCRAFT_TYPE",
    how="inner",
    validate="one_to_one"
)

print("\nAircraft types after merge:")
print(financial["AIRCRAFT_TYPE"].unique())


# ============================================================
# 12. CALCULATE COST PER MILE
# ============================================================

financial["COST_PER_MILE_USD"] = (
    financial["TOTAL_AIR_OPERATING_EXPENSES_USD"]
    / financial["MILES_FLOWN"]
)


# ============================================================
# 13. SHOW FINAL TABLE
# ============================================================

print("\n===================================")
print("Q1 2023 COST PER MILE")
print("===================================")

print(
    financial[
        [
            "AIRCRAFT_TYPE",
            "TOTAL_AIR_OPERATING_EXPENSES_USD",
            "MILES_FLOWN",
            "COST_PER_MILE_USD"
        ]
    ].to_string(index=False)
)


# ============================================================
# 14. VALIDATION AGAINST PAPER
# ============================================================

paper_miles = {
    "ERJ145": 2_932_203,
    "ERJ170": 1_601_976,
    "ERJ175": 23_921_987
}

paper_cost_per_mile = {
    "ERJ145": 10.60,
    "ERJ170": 8.49,
    "ERJ175": 8.06
}


print("\n===================================")
print("COMPARISON WITH PAPER")
print("===================================")

for aircraft in ["ERJ145", "ERJ170", "ERJ175"]:

    match = financial[
        financial["AIRCRAFT_TYPE"] == aircraft
    ]

    if match.empty:
        print(f"\n{aircraft}: NOT FOUND")
        continue

    row = match.iloc[0]

    our_miles = row["MILES_FLOWN"]
    our_cost = row["COST_PER_MILE_USD"]

    print(
        f"\n{aircraft}"
        f"\nOur miles: {our_miles:,.0f}"
        f"\nPaper miles: {paper_miles[aircraft]:,.0f}"
        f"\nMiles difference: {our_miles - paper_miles[aircraft]:,.0f}"
        f"\nOur cost/mile: ${our_cost:.2f}"
        f"\nPaper cost/mile: ${paper_cost_per_mile[aircraft]:.2f}"
    )


# ============================================================
# 15. SAVE
# ============================================================

financial.to_csv(
    output_file,
    index=False
)

print("\nSaved at:")
print(output_file)

