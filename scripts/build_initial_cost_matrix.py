import os
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

spill_file = (
    base_folder
    / "RouteInputs"
    / "route_inputs_jan2023_with_spill.csv"
)

cost_per_mile_file = (
    base_folder
    / "financial"
    / "envoy_q1_2023_cost_per_mile.csv"
)

output_file = (
    base_folder
    / "RouteInputs"
    / "envoy_jan2023_initial_assignment_costs.csv"
)


# ============================================================
# 2. LOAD DATA
# ============================================================

schedule = pd.read_csv(schedule_file)
spill_full = pd.read_csv(spill_file)
cost_data = pd.read_csv(cost_per_mile_file)

print("Schedule rows:", len(schedule))
print("Spill routes:", len(spill_full))
print("Cost-per-mile rows:", len(cost_data))


# ============================================================
# 3. CREATE UNIQUE FLIGHT ID
# ============================================================
#
# [INFERENCE]
# Flight numbers repeat across days and may change route.
# Therefore every schedule row receives a unique flight ID.
#

schedule["FLIGHT_ID"] = [
    f"F{i:05d}"
    for i in range(1, len(schedule) + 1)
]


# ============================================================
# 4. PREPARE SPILL DATA
# ============================================================

spill_full = spill_full.rename(
    columns={
        "ORIGIN": "Origin",
        "DEST": "Dest"
    }
)

# Keep original DB1B fare for traceability
spill_full["AVG_FARE_ORIGINAL"] = spill_full["AVG_FARE"]

spill_full["FARE_IMPUTED"] = False
spill_full["FARE_SOURCE"] = "DB1B"


# ============================================================
# 5. CHECK FOR DUPLICATE ROUTES
# ============================================================

duplicate_routes = spill_full.duplicated(
    subset=["Origin", "Dest"]
).sum()

print("\nDuplicate spill routes:", duplicate_routes)

if duplicate_routes > 0:
    raise ValueError(
        "Spill dataset contains duplicate Origin-Dest routes."
    )


# ============================================================
# 6. GET ROUTE DISTANCE FROM JANUARY SCHEDULE
# ============================================================
#
# One representative distance is calculated for each
# directed Origin-Destination pair.
#

route_distances = (
    schedule
    .groupby(
        ["Origin", "Dest"],
        as_index=False
    )["Distance"]
    .median()
    .rename(
        columns={
            "Distance": "ROUTE_DISTANCE"
        }
    )
)

spill_full = spill_full.merge(
    route_distances,
    on=["Origin", "Dest"],
    how="left",
    validate="one_to_one"
)


# ============================================================
# 7. FIND MISSING-FARE ROUTES USED IN JANUARY SCHEDULE
# ============================================================

schedule_routes = (
    schedule[
        ["Origin", "Dest"]
    ]
    .drop_duplicates()
)

missing_schedule_routes = (
    spill_full[
        spill_full["AVG_FARE"].isna()
    ]
    .merge(
        schedule_routes,
        on=["Origin", "Dest"],
        how="inner"
    )
)

print("\n===================================")
print("MISSING FARES USED BY JAN SCHEDULE")
print("===================================")

print(
    missing_schedule_routes[
        [
            "Origin",
            "Dest",
            "AVG_PAX_PER_FLIGHT",
            "ROUTE_DISTANCE"
        ]
    ].to_string(index=False)
)

print(
    "\nNumber of schedule routes requiring fare treatment:",
    len(missing_schedule_routes)
)


# ============================================================
# 8. TEMPORARY FARE IMPUTATION
# ============================================================
#
# [INFERENCE / TEMPORARY PROXY]
#
# This is NOT the historical 2010-2023 DB1B method
# described in the paper.
#
# For missing fares used by the January schedule:
#
# 1. Use reverse-route fare IF the reverse route has an
#    ORIGINAL DB1B fare.
#
# 2. Otherwise use the median fare of the 5 closest routes
#    in distance that:
#       - have an ORIGINAL DB1B fare
#       - have known schedule distance
#       - share the same origin OR destination
#
# 3. If no such routes exist, use the closest routes
#    in the whole network.
#

missing_indices = spill_full[
    spill_full["AVG_FARE"].isna()
    & spill_full["ROUTE_DISTANCE"].notna()
].index


for idx in missing_indices:

    origin = spill_full.loc[idx, "Origin"]
    dest = spill_full.loc[idx, "Dest"]
    distance = spill_full.loc[idx, "ROUTE_DISTANCE"]


    # --------------------------------------------------------
    # 8A. CHECK ORIGINAL FARE OF REVERSE ROUTE
    # --------------------------------------------------------

    reverse = spill_full[
        (spill_full["Origin"] == dest)
        & (spill_full["Dest"] == origin)
        & (spill_full["AVG_FARE_ORIGINAL"].notna())
    ]

    if len(reverse) > 0:

        proxy_fare = reverse[
            "AVG_FARE_ORIGINAL"
        ].iloc[0]

        source = "PROXY_REVERSE_ROUTE"


    else:

        # ----------------------------------------------------
        # 8B. SIMILAR ROUTES
        # ----------------------------------------------------

        candidates = spill_full[
            spill_full["AVG_FARE_ORIGINAL"].notna()
            & spill_full["ROUTE_DISTANCE"].notna()
            & (
                (spill_full["Origin"] == origin)
                | (spill_full["Dest"] == dest)
            )
        ].copy()


        # ----------------------------------------------------
        # 8C. FALLBACK TO NETWORK-WIDE DISTANCE MATCH
        # ----------------------------------------------------

        if len(candidates) == 0:

            candidates = spill_full[
                spill_full["AVG_FARE_ORIGINAL"].notna()
                & spill_full["ROUTE_DISTANCE"].notna()
            ].copy()

            source = "PROXY_NETWORK_DISTANCE"

        else:

            source = "PROXY_SIMILAR_ROUTE"


        candidates["DISTANCE_DIFFERENCE"] = (
            candidates["ROUTE_DISTANCE"]
            - distance
        ).abs()


        nearest = (
            candidates
            .sort_values("DISTANCE_DIFFERENCE")
            .head(5)
        )


        if len(nearest) == 0:
            raise ValueError(
                f"No fare proxy candidates found "
                f"for {origin}-{dest}."
            )


        proxy_fare = (
            nearest["AVG_FARE_ORIGINAL"]
            .median()
        )


    spill_full.loc[idx, "AVG_FARE"] = proxy_fare
    spill_full.loc[idx, "FARE_IMPUTED"] = True
    spill_full.loc[idx, "FARE_SOURCE"] = source


# ============================================================
# 9. SHOW TEMPORARILY IMPUTED ROUTES
# ============================================================

print("\n===================================")
print("TEMPORARILY IMPUTED FARES")
print("===================================")

imputed = spill_full[
    spill_full["FARE_IMPUTED"]
].copy()

print(
    imputed[
        [
            "Origin",
            "Dest",
            "ROUTE_DISTANCE",
            "AVG_PAX_PER_FLIGHT",
            "AVG_FARE_ORIGINAL",
            "AVG_FARE",
            "FARE_SOURCE"
        ]
    ].to_string(index=False)
)


# ============================================================
# 10. RECOMPUTE SPILL COSTS
# ============================================================
#
# [PAPER]
#
# spill cost =
# max(average demand - aircraft capacity, 0)
# × average fare
#

capacities = {
    "ERJ145": 50,
    "ERJ170": 65,
    "ERJ175": 76
}

for aircraft, capacity in capacities.items():

    spilled_pax = (
        spill_full["AVG_PAX_PER_FLIGHT"]
        - capacity
    ).clip(lower=0)

    spill_full[
        f"SPILLED_PAX_{aircraft}"
    ] = spilled_pax

    spill_full[
        f"SPILL_COST_{aircraft}"
    ] = (
        spilled_pax
        * spill_full["AVG_FARE"]
    )


# ============================================================
# 11. PREPARE SPILL DATA FOR SCHEDULE MERGE
# ============================================================

spill_columns = [
    "Origin",
    "Dest",

    "AVG_PAX_PER_FLIGHT",
    "AVG_FARE",
    "AVG_FARE_ORIGINAL",
    "FARE_IMPUTED",
    "FARE_SOURCE",

    "SPILL_COST_ERJ145",
    "SPILL_COST_ERJ170",
    "SPILL_COST_ERJ175"
]

spill = spill_full[
    spill_columns
].copy()


# ============================================================
# 12. MERGE SCHEDULE WITH ROUTE INPUTS
# ============================================================

cost_matrix = schedule.merge(
    spill,
    on=["Origin", "Dest"],
    how="left",
    validate="many_to_one"
)

print("\nRows after schedule/spill merge:")
print(len(cost_matrix))


# ============================================================
# 13. LOAD COST PER MILE
# ============================================================

cost_per_mile = (
    cost_data
    .set_index(
        "AIRCRAFT_TYPE"
    )["COST_PER_MILE_USD"]
    .to_dict()
)

print("\nCost per mile:")
print(cost_per_mile)


required_types = [
    "ERJ145",
    "ERJ170",
    "ERJ175"
]

missing_types = [
    aircraft
    for aircraft in required_types
    if aircraft not in cost_per_mile
]

if missing_types:
    raise ValueError(
        f"Missing aircraft types in "
        f"cost-per-mile data: {missing_types}"
    )


# ============================================================
# 14. CALCULATE OPERATING COST
# ============================================================
#
# [PAPER - INITIAL COST MATRIX]
#
# Operating Cost[f,a]
# =
# Distance[f] × Cost per Mile[a]
#

for aircraft in required_types:

    cost_matrix[
        f"OPERATING_COST_{aircraft}"
    ] = (
        cost_matrix["Distance"]
        * cost_per_mile[aircraft]
    )


# ============================================================
# 15. CALCULATE TOTAL ASSIGNMENT COST
# ============================================================
#
# [PAPER]
#
# c[f,a]
# =
# operating cost[f,a]
# +
# spill cost[f,a]
#

for aircraft in required_types:

    cost_matrix[
        f"TOTAL_COST_{aircraft}"
    ] = (
        cost_matrix[
            f"OPERATING_COST_{aircraft}"
        ]
        +
        cost_matrix[
            f"SPILL_COST_{aircraft}"
        ]
    )


# ============================================================
# 16. FINAL VALIDATION
# ============================================================

print("\n===================================")
print("INITIAL COST MATRIX VALIDATION")
print("===================================")

print("\nTotal flights:")
print(len(cost_matrix))


# ------------------------------------------------------------
# Missing route-level spill inputs
# ------------------------------------------------------------

no_spill_route = cost_matrix[
    [
        "SPILL_COST_ERJ145",
        "SPILL_COST_ERJ170",
        "SPILL_COST_ERJ175"
    ]
].isna().all(axis=1)

print("\nFlights without spill data:")
print(no_spill_route.sum())


# ------------------------------------------------------------
# Missing spill values
# ------------------------------------------------------------

print("\nMissing values by spill-cost column:")

print(
    cost_matrix[
        [
            "SPILL_COST_ERJ145",
            "SPILL_COST_ERJ170",
            "SPILL_COST_ERJ175"
        ]
    ].isna().sum()
)


# ------------------------------------------------------------
# Missing total costs
# ------------------------------------------------------------

print("\nMissing values by total-cost column:")

print(
    cost_matrix[
        [
            "TOTAL_COST_ERJ145",
            "TOTAL_COST_ERJ170",
            "TOTAL_COST_ERJ175"
        ]
    ].isna().sum()
)


# ------------------------------------------------------------
# Check number of flights using proxy fares
# ------------------------------------------------------------

print("\nFlights using an imputed fare:")

print(
    cost_matrix[
        "FARE_IMPUTED"
    ].fillna(False).sum()
)


# ============================================================
# 17. SHOW EXAMPLE FLIGHTS
# ============================================================

display_columns = [
    "FLIGHT_ID",
    "FlightDate",
    "Flight_Number_Reporting_Airline",
    "Origin",
    "Dest",
    "Distance",

    "AVG_PAX_PER_FLIGHT",
    "AVG_FARE",
    "FARE_SOURCE",

    "OPERATING_COST_ERJ145",
    "SPILL_COST_ERJ145",
    "TOTAL_COST_ERJ145",

    "OPERATING_COST_ERJ170",
    "SPILL_COST_ERJ170",
    "TOTAL_COST_ERJ170",

    "OPERATING_COST_ERJ175",
    "SPILL_COST_ERJ175",
    "TOTAL_COST_ERJ175"
]

print("\nFirst 10 flights:")

print(
    cost_matrix[
        display_columns
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# 18. SHOW FLIGHTS USING PROXY FARES
# ============================================================

proxy_flights = cost_matrix[
    cost_matrix["FARE_IMPUTED"] == True
].copy()

print("\n===================================")
print("FLIGHTS USING PROXY FARES")
print("===================================")

print(
    proxy_flights[
        [
            "FLIGHT_ID",
            "FlightDate",
            "Origin",
            "Dest",
            "AVG_PAX_PER_FLIGHT",
            "AVG_FARE",
            "FARE_SOURCE"
        ]
    ].to_string(index=False)
)


# ============================================================
# 19. SAVE
# ============================================================

cost_matrix.to_csv(
    output_file,
    index=False
)

print("\nSaved at:")
print(output_file)

