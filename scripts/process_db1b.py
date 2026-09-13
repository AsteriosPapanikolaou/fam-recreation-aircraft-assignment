import os
import pandas as pd
from pathlib import Path

# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))
db1b_folder = base_folder / "DB1B"

file_path = (
    db1b_folder /
    "Origin_and_Destination_Survey_DB1BMarket_2023_1.csv"
)

processed_folder = db1b_folder / "processed"
processed_folder.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. COLUMNS WE NEED
# ============================================================

columns_to_keep = [
    "Year",
    "Quarter",
    "Origin",
    "Dest",
    "MktCoupons",
    "RPCarrier",
    "TkCarrier",
    "OpCarrier",
    "Passengers",
    "MktFare",
    "MktDistance",
    "NonStopMiles"
]


# ============================================================
# 3. LOAD FULL DB1B FILE
# ============================================================

df = pd.read_csv(
    file_path,
    usecols=columns_to_keep
)

print("Full DB1B shape:", df.shape)


# ============================================================
# 4. FILTER ENVOY AIR
# ============================================================

envoy_db1b = df[
    df["RPCarrier"] == "MQ"
].copy()

print("Envoy DB1B rows:", len(envoy_db1b))


# ============================================================
# 5. RENAME COLUMNS
# ============================================================

envoy_db1b = envoy_db1b.rename(
    columns={
        "Year": "YEAR",
        "Quarter": "QUARTER",
        "Origin": "ORIGIN",
        "Dest": "DEST",
        "MktCoupons": "MARKET_COUPONS",
        "RPCarrier": "REPORTING_CARRIER",
        "TkCarrier": "TICKET_CARRIER",
        "OpCarrier": "OPERATING_CARRIER",
        "Passengers": "PASSENGERS",
        "MktFare": "MARKET_FARE",
        "MktDistance": "MARKET_DISTANCE",
        "NonStopMiles": "NONSTOP_MILES"
    }
)


# ============================================================
# 6. SAVE CLEAN ENVOY FILE
# ============================================================

envoy_db1b.to_csv(
    processed_folder / "envoy_db1b_q1_2023_clean.csv",
    index=False
)


# ============================================================
# 7. BASIC CHECKS
# ============================================================

print("\nFirst rows:")
print(envoy_db1b.head())

print("\nOperating carriers:")
print(envoy_db1b["OPERATING_CARRIER"].value_counts().head(10))

print("\nTicket carriers:")
print(envoy_db1b["TICKET_CARRIER"].value_counts().head(10))

print("\nMarket coupons:")
print(envoy_db1b["MARKET_COUPONS"].value_counts().sort_index())

