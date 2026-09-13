# -*- coding: utf-8 -*-
import os
"""
Created on Thu Sep 10 11:59:45 2026

@author: Asteris
"""
import json
import pandas as pd
from pathlib import Path


# ============================================================
# 1. PATHS
# ============================================================

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

cost_matrix_file = (
    base_folder
    / "RouteInputs"
    / "envoy_jan2023_initial_assignment_costs.csv"
)

initial_positions_file = (
    base_folder
    / "initial_conditions"
    / "envoy_initial_aircraft_positions_feasible.csv"
)


# ============================================================
# 2. LOAD INPUT DATA
# ============================================================

flights_df = pd.read_csv(cost_matrix_file)

initial_positions_df = pd.read_csv(
    initial_positions_file
)

print("Flights loaded:", len(flights_df))
print(
    "Initial-position rows:",
    len(initial_positions_df)
)


# ============================================================
# 3. DEFINE AIRCRAFT TYPES A
# ============================================================
#
# [PAPER]
# A = set of aircraft types
#

A = [
    "ERJ145",
    "ERJ170",
    "ERJ175"
]

print("\nAircraft types A:")
print(A)


# ============================================================
# 4. DEFINE FLIGHT SET F
# ============================================================
#
# [PAPER]
# F = set of flights
#
# We use our unique FLIGHT_ID as the index f.
#

if flights_df["FLIGHT_ID"].duplicated().any():
    raise ValueError(
        "FLIGHT_ID is not unique."
    )

F = flights_df[
    "FLIGHT_ID"
].tolist()

print("\nNumber of flights |F|:")
print(len(F))


# ============================================================
# 5. DEFINE AIRPORT SET P
# ============================================================
#
# [PAPER]
# P = set of airports
# βγάζει όλα τα διαφορετικά airport που εμφανίζονται στο dataset.

P = sorted(
    set(
        flights_df["Origin"].dropna()
    )
    |
    set(
        flights_df["Dest"].dropna()
    )
)

print("\nNumber of airports |P|:")
print(len(P))


# ============================================================
# 6. DEFINE TIME SET T
# ============================================================
#
# [PAPER]
# T = discretized 15-minute time indices
#
# We use the common-reference indices created earlier.
#

min_time = int(
    min(
        flights_df[
            "DEP_TIME_INDEX_COMMON"
        ].min(),
        flights_df[
            "ARR_TIME_INDEX_COMMON"
        ].min()
    )
)

max_time = int(
    max(
        flights_df[
            "DEP_TIME_INDEX_COMMON"
        ].max(),
        flights_df[
            "ARR_TIME_INDEX_COMMON"
        ].max()
    )
)

T = list(
    range(
        0,
        max_time + 1
    )
)

print("\nTime index information:")
print("Minimum observed time index:", min_time)
print("Maximum observed time index:", max_time)
print("Number of model time indices:", len(T))


# ============================================================
# 7. BUILD BASIC FLIGHT PARAMETERS
# ============================================================

origin = (
    flights_df
    .set_index("FLIGHT_ID")[
        "Origin"
    ]
    .to_dict()
)

destination = (
    flights_df
    .set_index("FLIGHT_ID")[
        "Dest"
    ]
    .to_dict()
)

departure_time = (
    flights_df
    .set_index("FLIGHT_ID")[
        "DEP_TIME_INDEX_COMMON"
    ]
    .astype(int)
    .to_dict()
)

arrival_time = (
    flights_df
    .set_index("FLIGHT_ID")[
        "ARR_TIME_INDEX_COMMON"
    ]
    .astype(int)
    .to_dict()
)

distance = (
    flights_df
    .set_index("FLIGHT_ID")[
        "Distance"
    ]
    .to_dict()
)


# ============================================================
# 8. BUILD ASSIGNMENT COST PARAMETER c[f,a]
# ============================================================
#
# [PAPER]
#
# c[f,a] =
# total assignment cost of assigning aircraft type a
# to flight f.
#

cost_column = {
    "ERJ145": "TOTAL_COST_ERJ145",
    "ERJ170": "TOTAL_COST_ERJ170",
    "ERJ175": "TOTAL_COST_ERJ175"
}

c = {}

for _, row in flights_df.iterrows(): #αυτή η κάτω πάυλα σημαίνει ότι αγνοεί το indexing.

    f = row["FLIGHT_ID"]

    for a in A:

        c[f, a] = float(
            row[
                cost_column[a]
            ]
        )


# ============================================================
# 9. BUILD INITIAL POSITION PARAMETER y0[a,p]
# ============================================================
#
# [PAPER]
#
# y[a,p,0]
# =
# initial number of aircraft of type a
# at airport p.
#

y0 = {}

for _, row in initial_positions_df.iterrows():

    a = row["AIRCRAFT_TYPE"]
    p = row["AIRPORT"]

    y0[a, p] = int(
        row["INITIAL_COUNT"]
    )

# Ensure every type-airport combination exists

for a in A:
    for p in P:

        if (a, p) not in y0:

            y0[a, p] = 0


# ============================================================
# 10. FLEET SIZE FROM INITIAL CONDITIONS
# ============================================================

fleet_size = {
    a: sum(
        y0[a, p]
        for p in P
    )
    for a in A
}

print("\nFleet size:")
print(fleet_size)


# ============================================================
# 11. CREATE DEPARTURE AND ARRIVAL LOOKUPS
# ============================================================
#
# These will later be used in the flow-balance constraint.
#
# dep[p,t] = flights departing airport p at time t
# arr[p,t] = flights arriving airport p at time t
#

departures = {
    (p, t): []
    for p in P
    for t in T
}

arrivals = {
    (p, t): []
    for p in P
    for t in T
}


for f in F:

    p_dep = origin[f]
    t_dep = departure_time[f]

    p_arr = destination[f]
    t_arr = arrival_time[f]

    departures[
        p_dep,
        t_dep
    ].append(f)

    arrivals[
        p_arr,
        t_arr
    ].append(f)


# ============================================================
# 12. VALIDATION
# ============================================================

print("\n===================================")
print("FAM INPUT VALIDATION")
print("===================================")

print("\nFlights:")
print(len(F))

print("\nAircraft types:")
print(len(A))

print("\nAirports:")
print(len(P))

print("\nTime indices:")
print(len(T))

print("\nCost coefficients:")
print(len(c))

expected_cost_coefficients = (
    len(F)
    * len(A)
)

print(
    "Expected cost coefficients:",
    expected_cost_coefficients
)


# ------------------------------------------------------------
# Every flight should appear once as departure
# and once as arrival
# ------------------------------------------------------------

departure_count = sum(
    len(v)
    for v in departures.values()
)

arrival_count = sum(
    len(v)
    for v in arrivals.values()
)

print("\nFlights represented as departures:")
print(departure_count)

print("\nFlights represented as arrivals:")
print(arrival_count)


# ------------------------------------------------------------
# Initial fleet validation
# ------------------------------------------------------------

print("\nInitial fleet by aircraft type:")

for a in A:

    print(
        a,
        fleet_size[a]
    )

print(
    "\nTotal fleet:",
    sum(
        fleet_size.values()
    )
)



# ------------------------------------------------------------
# Missing costs
# ------------------------------------------------------------

missing_costs = [
    (f, a)
    for f in F
    for a in A
    if pd.isna(
        c[f, a]
    )
]

print("\nMissing cost coefficients:")
print(len(missing_costs))


# ------------------------------------------------------------
# Invalid time order
# ------------------------------------------------------------

invalid_time_order = [
    f
    for f in F
    if arrival_time[f]
    <= departure_time[f]
]

print("\nFlights with arrival <= departure:")
print(len(invalid_time_order))


# ------------------------------------------------------------
# Example data
# ------------------------------------------------------------

example_flight = F[0]

print("\n===================================")
print("EXAMPLE FLIGHT")
print("===================================")

print("Flight:", example_flight)

print(
    "Route:",
    origin[example_flight],
    "->",
    destination[example_flight]
)

print(
    "Time:",
    departure_time[example_flight],
    "->",
    arrival_time[example_flight]
)

print(
    "Distance:",
    distance[example_flight]
)

print("\nAssignment costs:")

for a in A:

    print(
        a,
        c[
            example_flight,
            a
        ]
    )


import pulp


# ============================================================
# 13. CREATE OPTIMIZATION MODEL
# ============================================================

model = pulp.LpProblem(
    "Envoy_Conventional_FAM",
    pulp.LpMinimize
)


# ============================================================
# 14. ASSIGNMENT VARIABLES x[f,a]
# ============================================================

x = pulp.LpVariable.dicts(
    "x",
    [(f, a) for f in F for a in A],
    cat="Binary"
)

print("\nNumber of x variables:")
print(len(x))

# ============================================================
# 15. CREATE ACTIVE TIME NODES PER AIRPORT
# ============================================================
#
# Instead of creating y variables for every airport at every
# global 15-minute index, keep only time indices where an
# arrival or departure event occurs.
#
# t = 0 is always included because it contains the initial
# aircraft inventory y[a,p,0].
#

airport_times = {}

for p in P:

    event_times = {0}

    # Departure events
    dep_times_p = flights_df.loc[
        flights_df["Origin"] == p,
        "DEP_TIME_INDEX_COMMON"
    ].astype(int)

    event_times.update(dep_times_p)

    # Arrival events
    arr_times_p = flights_df.loc[
        flights_df["Dest"] == p,
        "ARR_TIME_INDEX_COMMON"
    ].astype(int)

    event_times.update(arr_times_p)

    airport_times[p] = sorted(event_times)


# ============================================================
# 16. VALIDATE COMPRESSED NETWORK SIZE
# ============================================================

number_of_airport_time_nodes = sum(
    len(airport_times[p])
    for p in P
)

print("\n===================================")
print("COMPRESSED TIME-SPACE NETWORK")
print("===================================")

print(
    "Full airport-time combinations:",
    len(P) * len(T)
)

print(
    "Active airport-time nodes:",
    number_of_airport_time_nodes
)

print(
    "Potential y variables per aircraft type:",
    number_of_airport_time_nodes
)

print(
    "Potential y variables across all types:",
    number_of_airport_time_nodes * len(A)
)

# ============================================================
# 17. CREATE OPTIMIZATION MODEL
# ============================================================

import pulp

model = pulp.LpProblem(
    "Envoy_Conventional_FAM",
    pulp.LpMinimize
)

# ============================================================
# 18. FLIGHT ASSIGNMENT VARIABLES x[f,a]
# ============================================================
#
# x[f,a] = 1 if aircraft type a is assigned to flight f
#          0 otherwise
#

x = pulp.LpVariable.dicts(
    "x",
    [
        (f, a)
        for f in F
        for a in A
    ],
    cat="Binary"
)

print("\nNumber of x variables:")
print(len(x))

# ============================================================
# 19. CREATE ACTIVE AIRPORT-TIME NODE LIST
# ============================================================

active_nodes = [
    (p, t)
    for p in P
    for t in airport_times[p]
]

print("\nNumber of active airport-time nodes:")
print(len(active_nodes))

# ============================================================
# 20. START-OF-NODE AIRCRAFT VARIABLES y_minus[a,p,t]
# ============================================================
#
# Number of aircraft of type a available at airport p
# immediately before processing the events at time t.
#

y_minus = pulp.LpVariable.dicts(
    "y_minus",
    [
        (a, p, t)
        for a in A
        for (p, t) in active_nodes
    ],
    lowBound=0,
    cat="Integer"
)

print("\nNumber of y_minus variables:")
print(len(y_minus))

# ============================================================
# 21. END-OF-NODE AIRCRAFT VARIABLES y_plus[a,p,t]
# ============================================================
#
# Number of aircraft of type a remaining at airport p
# immediately after processing the events at time t.
#

y_plus = pulp.LpVariable.dicts(
    "y_plus",
    [
        (a, p, t)
        for a in A
        for (p, t) in active_nodes
    ],
    lowBound=0,
    cat="Integer"
)

print("\nNumber of y_plus variables:")
print(len(y_plus))

# ============================================================
# 22. OBJECTIVE FUNCTION (4a)
# ============================================================
#
# Minimize total assignment cost:
#
# sum over all flights f
# and aircraft types a
# of:
#
# c[f,a] * x[f,a]
#

model += pulp.lpSum(
    c[f, a] * x[f, a]
    for f in F
    for a in A
)

print("\nObjective function added.")

# ============================================================
# 23. COVER CONSTRAINT (4b)
# ============================================================
#
# Exactly one aircraft type must be assigned to every flight.
#

for f in F:

    model += (
        pulp.lpSum(
            x[f, a]
            for a in A
        )
        == 1
    )

print(
    "Cover constraints added:",
    len(F)
)


# ============================================================
# 24. AIRCRAFT RANGE PARAMETERS
# ============================================================
#
# [MISSING FROM PAPER]
# Numerical range values are not reported in the paper.
#
# [PUBLIC DATA]
# Manufacturer LR range specifications are used.
#
# BTS Distance is expressed in statute miles, therefore
# aircraft ranges are converted from nautical miles to miles.
#

NM_TO_MILES = 1.15078

aircraft_range_nm = {
    "ERJ145": 1550,
    "ERJ170": 2100,
    "ERJ175": 2150
}

aircraft_range = {
    a: aircraft_range_nm[a] * NM_TO_MILES
    for a in A
}

print("\nAircraft ranges:")

for a in A:
    print(
        a,
        aircraft_range_nm[a],
        "nm =",
        round(aircraft_range[a], 1),
        "miles"
    )
    
    range_constraints = 0

for f in F:
    for a in A:

        if distance[f] > aircraft_range[a]:

            model += x[f, a] == 0

            range_constraints += 1

print(
    "Range-infeasible assignments fixed to zero:",
    range_constraints
)

# ============================================================
# 26. FLOW BALANCE CONSTRAINT (4d)
# ============================================================
#
# For each aircraft type a,
# airport p,
# and active time node t:
#
# available before
# + arriving aircraft
# =
# available after
# + departing aircraft
#

flow_balance_constraints = 0

for a in A:

    for p in P:

        for t in airport_times[p]:

            model += (
                y_minus[a, p, t]
                +
                pulp.lpSum(
                    x[f, a]
                    for f in arrivals[(p, t)]
                )
                ==
                y_plus[a, p, t]
                +
                pulp.lpSum(
                    x[f, a]
                    for f in departures[(p, t)]
                )
            )

            flow_balance_constraints += 1


print(
    "\nFlow balance constraints added:",
    flow_balance_constraints
)

# ============================================================
# 27. INITIAL AIRCRAFT POSITION CONSTRAINT (4e)
# ============================================================

initial_condition_constraints = 0

for a in A:

    for p in P:

        model += (
            y_minus[a, p, 0]
            ==
            y0[a, p]
        )

        initial_condition_constraints += 1


print(
    "Initial-condition constraints added:",
    initial_condition_constraints
)

# ============================================================
# 28. TIME PRECEDENCE CONSTRAINT (4f)
# ============================================================
#
# Compressed-network equivalent of:
#
# y_minus[a,p,t] = y_plus[a,p,t-1]
#
# We connect each active airport-time node directly
# to the previous active node at that airport.
#

precedence_constraints = 0

for a in A:

    for p in P:

        times_p = airport_times[p]

        for i in range(1, len(times_p)):

            previous_t = times_p[i - 1]
            current_t = times_p[i]

            model += (
                y_minus[a, p, current_t]
                ==
                y_plus[a, p, previous_t]
            )

            precedence_constraints += 1


print(
    "Precedence constraints added:",
    precedence_constraints
)

# ============================================================
# 29. SOLVE THE FAM
# ============================================================

print("\n===================================")
print("SOLVING FAM")
print("===================================")

solver = pulp.PULP_CBC_CMD(
    msg=True
)

model.solve(solver)


# ============================================================
# 31. EXPORT FAM SOLUTION RESULTS
# ============================================================

if model.status != pulp.LpStatusOptimal:

    raise RuntimeError(
        "FAM did not reach an optimal solution. "
        f"Solver status: {pulp.LpStatus[model.status]}"
    )


print("\n===================================")
print("EXPORTING ASSIGNMENT RESULTS")
print("===================================")


# Model time is represented by 15-minute time buckets.
BASE_DATE = pd.Timestamp("2023-01-01")


def slot_to_bucket_datetime(slot):

    return (
        BASE_DATE
        + pd.Timedelta(
            minutes=int(slot) * 15
        )
    )


capacities = {
    "ERJ145": 50,
    "ERJ170": 65,
    "ERJ175": 76
}


# Faster lookup by FLIGHT_ID
flight_rows = flights_df.set_index(
    "FLIGHT_ID",
    drop=False
)

results = []


for f in F:

    assigned_aircraft = next(
        (
            a
            for a in A
            if pulp.value(x[f, a]) > 0.5
        ),
        None
    )

    if assigned_aircraft is None:

        raise ValueError(
            f"No aircraft assigned to flight {f}"
        )


    row = flight_rows.loc[f]


    operating_cost = float(
        row[f"OPERATING_COST_{assigned_aircraft}"]
    )

    spill_cost = float(
        row[f"SPILL_COST_{assigned_aircraft}"]
    )

    total_assignment_cost = float(
        c[f, assigned_aircraft]
    )


    # Route-level average demand used by the model
    average_pax = row.get(
        "AVG_PAX_PER_FLIGHT",
        None
    )


    capacity = capacities[
        assigned_aircraft
    ]


    if pd.notna(average_pax):

        average_seat_slack = (
            capacity
            - float(average_pax)
        )

    else:

        average_seat_slack = None


    results.append({

        # ---------------------------------
        # Schedule identifiers
        # ---------------------------------

        "FLIGHT_ID": f,

        "FlightDate": row.get(
            "FlightDate"
        ),

        "Flight_Number_Reporting_Airline":
            row.get(
                "Flight_Number_Reporting_Airline"
            ),


        # ---------------------------------
        # Route and schedule information
        # ---------------------------------

        "Origin": origin[f],

        "Dest": destination[f],

        "DEP_REFERENCE_TIME":
            row.get(
                "DEP_REFERENCE_TIME"
            ),

        "ARR_REFERENCE_TIME":
            row.get(
                "ARR_REFERENCE_TIME"
            ),

        "CRSDepTime":
            row.get(
                "CRSDepTime"
            ),

        "CRSArrTime":
            row.get(
                "CRSArrTime"
            ),


        # ---------------------------------
        # FAM model time representation
        # ---------------------------------

        "Departure_slot":
            departure_time[f],

        "Arrival_slot":
            arrival_time[f],

        "Model_Departure_Bucket_Datetime":
            slot_to_bucket_datetime(
                departure_time[f]
            ),

        "Model_Arrival_Bucket_Datetime":
            slot_to_bucket_datetime(
                arrival_time[f]
            ),


        # ---------------------------------
        # Flight characteristics
        # ---------------------------------

        "Distance": distance[f],


        # ---------------------------------
        # FAM assignment
        # ---------------------------------

        "Assigned_Aircraft":
            assigned_aircraft,


        # ---------------------------------
        # FAM costs
        # ---------------------------------

        "Operating_Cost":
            operating_cost,

        "Spill_Cost":
            spill_cost,

        "Total_Assignment_Cost":
            total_assignment_cost,

        "Cost_Check_Diff":
            total_assignment_cost
            - (
                operating_cost
                + spill_cost
            ),


        # ---------------------------------
        # FAM demand/capacity diagnostics
        # ---------------------------------

        "Average_Pax_Per_Flight":
            average_pax,

        "Aircraft_Capacity":
            capacity,

        "Average_Seat_Slack":
            average_seat_slack

    })


results_df = pd.DataFrame(
    results
)


# ============================================================
# SAVE RESULTS
# ============================================================

output_dir = (
    base_folder
    / "Results"
)

output_dir.mkdir(
    exist_ok=True
)


# 1. Main FAM assignment output

output_file = (
    output_dir
    / "envoy_FAM_assignment_results.csv"
)

results_df.to_csv(
    output_file,
    index=False
)


# 2. Fleet distribution output

fleet_distribution = (

    results_df[
        "Assigned_Aircraft"
    ]

    .value_counts()

    .reindex(
        A,
        fill_value=0
    )

    .rename_axis(
        "Aircraft_Type"
    )

    .reset_index(
        name="Assigned_Flights"
    )
)


fleet_distribution[
    "Assigned_Share"
] = (

    fleet_distribution[
        "Assigned_Flights"
    ]

    / len(results_df)
)


distribution_file = (
    output_dir
    / "envoy_FAM_fleet_distribution.csv"
)

fleet_distribution.to_csv(
    distribution_file,
    index=False
)


# 3. Cost reconciliation check

cost_check_max_abs = float(

    results_df[
        "Cost_Check_Diff"
    ]

    .abs()
    .max()
)


# 4. Run summary

summary = {

    "solver_status":
        pulp.LpStatus[
            model.status
        ],

    "objective_value":
        float(
            pulp.value(
                model.objective
            )
        ),

    "flight_count":
        int(
            len(results_df)
        ),

    "aircraft_types":
        A,

    "fleet_size_by_type": {

        a: int(
            fleet_size[a]
        )

        for a in A
    },

    "assigned_flights_by_type": {

        row["Aircraft_Type"]:
            int(
                row["Assigned_Flights"]
            )

        for _, row
        in fleet_distribution.iterrows()
    },

    "total_operating_cost":
        float(
            results_df[
                "Operating_Cost"
            ].sum()
        ),

    "total_spill_cost":
        float(
            results_df[
                "Spill_Cost"
            ].sum()
        ),

    "total_assignment_cost":
        float(
            results_df[
                "Total_Assignment_Cost"
            ].sum()
        ),

    "cost_check_max_abs":
        cost_check_max_abs,

    "cost_check_passed":
        bool(
            cost_check_max_abs
            < 1e-6
        )
}


summary_file = (
    output_dir
    / "envoy_FAM_run_summary.json"
)


summary_file.write_text(

    json.dumps(
        summary,
        indent=2
    ),

    encoding="utf-8"
)


# Use filenames in console output.
# Write a compact JSON summary alongside the assignment results.

print(
    "Solver status:",
    summary["solver_status"]
)

print(
    "Objective value:",
    summary["objective_value"]
)

print(
    "Saved assignment results: "
    "envoy_FAM_assignment_results.csv"
)

print(
    "Saved fleet distribution: "
    "envoy_FAM_fleet_distribution.csv"
)

print(
    "Saved run summary: "
    "envoy_FAM_run_summary.json"
)

print(
    "Maximum cost reconciliation difference:",
    cost_check_max_abs
)

print(
    "\nFirst rows:"
)

print(
    results_df.head()
)

