# -*- coding: utf-8 -*-
import os
"""
Feasible initial aircraft position reconstruction

@author: Asteris
"""

import pandas as pd
import pulp

from pathlib import Path
from collections import defaultdict
import time


# ============================================================
# PROGRESS FUNCTION
# ============================================================

script_start = time.time()


def stage(message):

    elapsed = time.time() - script_start

    print(
        f"\n[{elapsed:7.2f} s] {message}",
        flush=True
    )


# ============================================================
# 1. PATHS
# ============================================================

stage("STAGE 1 - Setting paths")

base_folder = Path(os.environ.get("FAM_RECREATION_ROOT", Path(__file__).resolve().parents[1]))

flight_file = (
    base_folder
    / "RouteInputs"
    / "envoy_jan2023_initial_assignment_costs.csv"
)

proxy_initial_file = (
    base_folder
    / "initial_conditions"
    / "envoy_initial_aircraft_positions.csv"
)

output_file = (
    base_folder
    / "initial_conditions"
    / "envoy_initial_aircraft_positions_feasible.csv"
)


# ============================================================
# 2. LOAD DATA
# ============================================================

stage("STAGE 2 - Loading data")

flights_df = pd.read_csv(
    flight_file
)

initial_df = pd.read_csv(
    proxy_initial_file
)

print(
    "Flights:",
    len(flights_df)
)

print(
    "Initial-position rows:",
    len(initial_df)
)


# ============================================================
# 3. SETS
# ============================================================

stage("STAGE 3 - Creating sets")

A = [
    "ERJ145",
    "ERJ170",
    "ERJ175"
]

P = sorted(
    set(
        flights_df[
            "Origin"
        ].dropna()
    )
    |
    set(
        flights_df[
            "Dest"
        ].dropna()
    )
)

print(
    "Aircraft types:",
    len(A)
)

print(
    "Airports:",
    len(P)
)


# ============================================================
# 4. READ PROXY y0
# ============================================================

stage("STAGE 4 - Reading proxy initial positions")

y0_proxy = {
    (a, p): 0
    for a in A
    for p in P
}

for _, row in initial_df.iterrows():

    a = row["AIRCRAFT_TYPE"]
    p = row["AIRPORT"]

    if (
        a in A
        and p in P
    ):

        y0_proxy[
            a,
            p
        ] = int(
            row["INITIAL_COUNT"]
        )


# ============================================================
# 5. FLEET SIZE
# ============================================================

fleet_size = {
    a: sum(
        y0_proxy[a, p]
        for p in P
    )
    for a in A
}


print(
    "\nProxy fleet sizes:"
)

for a in A:

    print(
        a,
        fleet_size[a]
    )

print(
    "TOTAL:",
    sum(
        fleet_size.values()
    )
)


# ============================================================
# 6. BUILD AIRPORT EVENT COUNTS
# ============================================================

stage(
    "STAGE 5 - Building airport arrival/departure event counts"
)

arrivals = defaultdict(
    int
)

departures = defaultdict(
    int
)

airport_times = {
    p: {0}
    for p in P
}


for _, row in flights_df.iterrows():

    origin = row["Origin"]
    destination = row["Dest"]

    dep_t = int(
        row["DEP_TIME_INDEX_COMMON"]
    )

    arr_t = int(
        row["ARR_TIME_INDEX_COMMON"]
    )

    departures[
        origin,
        dep_t
    ] += 1

    arrivals[
        destination,
        arr_t
    ] += 1

    airport_times[
        origin
    ].add(
        dep_t
    )

    airport_times[
        destination
    ].add(
        arr_t
    )


for p in P:

    airport_times[p] = sorted(
        airport_times[p]
    )


# ============================================================
# 7. CALCULATE MINIMUM INITIAL AIRCRAFT REQUIRED
# ============================================================

stage(
    "STAGE 6 - Calculating minimum required aircraft per airport"
)

required_initial = {}

requirement_rows = []


for p in P:

    cumulative_flow = 0
    minimum_flow = 0
    critical_time = 0

    for t in airport_times[p]:

        if t == 0:
            continue

        cumulative_flow += (
            arrivals[p, t]
            -
            departures[p, t]
        )

        if cumulative_flow < minimum_flow:

            minimum_flow = cumulative_flow
            critical_time = t


    required = max(
        0,
        -minimum_flow
    )

    required_initial[
        p
    ] = required


    current_initial = sum(
        y0_proxy[a, p]
        for a in A
    )

    requirement_rows.append(
        {
            "AIRPORT": p,
            "PROXY_INITIAL": current_initial,
            "REQUIRED_INITIAL": required,
            "DEFICIT": max(
                0,
                required - current_initial
            ),
            "SURPLUS": max(
                0,
                current_initial - required
            ),
            "CRITICAL_TIME": critical_time
        }
    )


requirements_df = pd.DataFrame(
    requirement_rows
)


print(
    "\nTotal aircraft in proxy:",
    requirements_df[
        "PROXY_INITIAL"
    ].sum()
)

print(
    "Total minimum airport requirement:",
    requirements_df[
        "REQUIRED_INITIAL"
    ].sum()
)


# ============================================================
# 8. SHOW CURRENT DEFICITS
# ============================================================

deficits_before = (
    requirements_df[
        requirements_df[
            "DEFICIT"
        ] > 0
    ]
    .sort_values(
        "DEFICIT",
        ascending=False
    )
)


print(
    "\n==================================="
)

print(
    "DEFICITS BEFORE REPAIR"
)

print(
    "==================================="
)


if len(deficits_before) == 0:

    print(
        "Proxy y0 is already aggregate-feasible."
    )

else:

    print(
        deficits_before.to_string(
            index=False
        )
    )


# ============================================================
# 9. SMALL y0 REPAIR MODEL
# ============================================================

stage(
    "STAGE 7 - Creating SMALL initial-position repair MILP"
)

model = pulp.LpProblem(
    "Minimum_Change_y0_Repair",
    pulp.LpMinimize
)


# ============================================================
# 10. NEW INITIAL AIRCRAFT VARIABLES
# ============================================================

y0_new = pulp.LpVariable.dicts(
    "y0_new",
    [
        (a, p)
        for a in A
        for p in P
    ],
    lowBound=0,
    cat="Integer"
)


# ============================================================
# 11. DEVIATION VARIABLES
# ============================================================

deviation_plus = pulp.LpVariable.dicts(
    "deviation_plus",
    [
        (a, p)
        for a in A
        for p in P
    ],
    lowBound=0,
    cat="Continuous"
)

deviation_minus = pulp.LpVariable.dicts(
    "deviation_minus",
    [
        (a, p)
        for a in A
        for p in P
    ],
    lowBound=0,
    cat="Continuous"
)


# ============================================================
# 12. DEVIATION DEFINITION
# ============================================================

stage(
    "STAGE 8 - Adding deviation constraints"
)

for a in A:

    for p in P:

        model += (
            y0_new[a, p]
            -
            y0_proxy[a, p]
            ==
            deviation_plus[a, p]
            -
            deviation_minus[a, p]
        )


# ============================================================
# 13. PRESERVE EXACT FLEET SIZE BY TYPE
# ============================================================

stage(
    "STAGE 9 - Adding fleet-size constraints"
)

for a in A:

    model += (
        pulp.lpSum(
            y0_new[a, p]
            for p in P
        )
        ==
        fleet_size[a]
    )


# ============================================================
# 14. AIRPORT FEASIBILITY CONSTRAINT
# ============================================================
#
# Total aircraft initially positioned at airport p
# must be at least the minimum required by the
# scheduled cumulative departure/arrival pattern.
#

stage(
    "STAGE 10 - Adding airport feasibility constraints"
)

for p in P:

    model += (
        pulp.lpSum(
            y0_new[a, p]
            for a in A
        )
        >=
        required_initial[p]
    )


# ============================================================
# 15. OBJECTIVE
# ============================================================
#
# Minimize L1 distance from proxy y0.
#
# One aircraft moved from airport A to airport B
# creates:
#
#   -1 at A
#   +1 at B
#
# therefore contributes 2 to this objective.
#

stage(
    "STAGE 11 - Adding minimum-change objective"
)

model += pulp.lpSum(
    deviation_plus[a, p]
    +
    deviation_minus[a, p]

    for a in A
    for p in P
)


# ============================================================
# 16. MODEL SUMMARY
# ============================================================

print(
    "\n==================================="
)

print(
    "SMALL MODEL SUMMARY"
)

print(
    "==================================="
)

print(
    "Variables:",
    len(
        model.variables()
    )
)

print(
    "Constraints:",
    len(
        model.constraints
    )
)


# ============================================================
# 17. SOLVE
# ============================================================

stage(
    "STAGE 12 - Solving small y0 repair model"
)

solver = pulp.PULP_CBC_CMD(
    msg=True
)

solve_start = time.time()

model.solve(
    solver
)

solve_time = (
    time.time()
    -
    solve_start
)


# ============================================================
# 18. STATUS
# ============================================================

print(
    "\n==================================="
)

print(
    "SOLUTION STATUS"
)

print(
    "==================================="
)

print(
    "Status:",
    pulp.LpStatus[
        model.status
    ]
)

print(
    "Solve time:",
    round(
        solve_time,
        3
    ),
    "seconds"
)


if model.status != pulp.LpStatusOptimal:

    raise RuntimeError(
        "Could not construct a feasible initial distribution."
    )


minimum_deviation = pulp.value(
    model.objective
)

print(
    "Minimum total L1 deviation:",
    minimum_deviation
)

print(
    "Equivalent aircraft relocations:",
    minimum_deviation / 2
)


# ============================================================
# 19. EXTRACT SOLUTION
# ============================================================

stage(
    "STAGE 13 - Extracting repaired y0"
)

output_rows = []


for a in A:

    for p in P:

        proxy_value = (
            y0_proxy[
                a,
                p
            ]
        )

        new_value = int(
            round(
                pulp.value(
                    y0_new[
                        a,
                        p
                    ]
                )
            )
        )

        output_rows.append(
            {
                "AIRCRAFT_TYPE": a,
                "AIRPORT": p,
                "INITIAL_COUNT": new_value,
                "PROXY_INITIAL_COUNT": proxy_value,
                "CHANGE_FROM_PROXY": (
                    new_value
                    -
                    proxy_value
                )
            }
        )


feasible_y0_df = pd.DataFrame(
    output_rows
)


# ============================================================
# 20. SHOW ONLY CHANGED POSITIONS
# ============================================================

changes = (
    feasible_y0_df[
        feasible_y0_df[
            "CHANGE_FROM_PROXY"
        ] != 0
    ]
    .sort_values(
        [
            "AIRCRAFT_TYPE",
            "AIRPORT"
        ]
    )
)


print(
    "\n==================================="
)

print(
    "CHANGES FROM PROXY y0"
)

print(
    "==================================="
)


if len(changes) == 0:

    print(
        "No changes."
    )

else:

    print(
        changes.to_string(
            index=False
        )
    )


# ============================================================
# 21. VALIDATE FLEET TOTALS
# ============================================================

print(
    "\n==================================="
)

print(
    "FLEET VALIDATION"
)

print(
    "==================================="
)


final_fleet = (
    feasible_y0_df
    .groupby(
        "AIRCRAFT_TYPE"
    )[
        "INITIAL_COUNT"
    ]
    .sum()
)


print(
    final_fleet
)

print(
    "\nTotal fleet:",
    feasible_y0_df[
        "INITIAL_COUNT"
    ].sum()
)


# ============================================================
# 22. VALIDATE AIRPORT FEASIBILITY
# ============================================================

stage(
    "STAGE 14 - Validating repaired airport inventories"
)

post_repair_rows = []


for p in P:

    new_initial = sum(
        int(
            feasible_y0_df.loc[
                (
                    feasible_y0_df[
                        "AIRCRAFT_TYPE"
                    ] == a
                )
                &
                (
                    feasible_y0_df[
                        "AIRPORT"
                    ] == p
                ),
                "INITIAL_COUNT"
            ].iloc[0]
        )
        for a in A
    )

    post_repair_rows.append(
        {
            "AIRPORT": p,
            "NEW_INITIAL": new_initial,
            "REQUIRED_INITIAL": required_initial[p],
            "DEFICIT": max(
                0,
                required_initial[p]
                -
                new_initial
            )
        }
    )


post_repair_df = pd.DataFrame(
    post_repair_rows
)


remaining_deficits = (
    post_repair_df[
        post_repair_df[
            "DEFICIT"
        ] > 0
    ]
)


print(
    "\nRemaining airport deficits:",
    len(
        remaining_deficits
    )
)


if len(
    remaining_deficits
) > 0:

    print(
        remaining_deficits.to_string(
            index=False
        )
    )

else:

    print(
        "All airport initial-position requirements satisfied."
    )


# ============================================================
# 23. SAVE
# ============================================================

stage(
    "STAGE 15 - Saving repaired y0"
)

feasible_y0_df.to_csv(
    output_file,
    index=False
)


print(
    "\nSaved to:"
)

print(
    output_file
)


# ============================================================
# FINISHED
# ============================================================

stage(
    "SCRIPT FINISHED"
)

print(
    "Total script time:",
    round(
        time.time()
        -
        script_start,
        3
    ),
    "seconds"
)

