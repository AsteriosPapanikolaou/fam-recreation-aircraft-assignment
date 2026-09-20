# Methodology and Findings: Envoy Air Fleet Assignment Model Recreation

## 1. Introduction

This project recreates the conventional-aircraft Fleet Assignment Model (FAM) described in the ICAS 2024 paper *"Optimizing Fleet Assignment Decisions for Regional Airlines with Hybrid Electric Aircraft Uptake"* by Chan, Deng, Tran, Wu, Ikeda, Cinar, and Li. The paper develops a cost-estimation and fleet-assignment framework for evaluating how conventional regional jets and future hybrid-electric aircraft could be assigned across a real regional airline schedule. The present recreation focuses on the conventional baseline model rather than the hybrid-electric scenarios.

The objective of the project was to implement a working integer-programming FAM using Python, PuLP, and the CBC MILP solver, using the Envoy Air January 2023 flight schedule as the operational test case. In practical terms, the model assigns one aircraft type to every scheduled flight while preserving aircraft availability over a time-space network. The assignment decision is cost-driven: each possible flight-aircraft pairing receives a cost, and the optimization model selects the least-cost feasible assignment across the full monthly network.

Fleet assignment is a central problem in airline operations because the choice of aircraft type affects operating cost, passenger spill, network feasibility, and downstream schedule robustness. Even when the fleet size is sufficient in aggregate, an airline schedule can become infeasible if aircraft are initially positioned at the wrong airports or if the time ordering of arrivals and departures is not respected. For this reason, the recreation did not only implement the final optimization model; it also required substantial preprocessing, cost construction, initial-condition reconstruction, and infeasibility debugging.

Throughout this document, a distinction is made between three categories of information:

- **Paper-based elements:** model structure, cost definitions, datasets, and benchmark results described in the Chan et al. paper.
- **Implemented elements:** the specific Python/PuLP implementation developed in this project.
- **Project assumptions or approximations:** choices introduced because the full internal data or exact paper preprocessing pipeline was not available.

## 2. Dataset Preparation and Input Generation

The main operational dataset used in the recreation is the Envoy Air January 2023 schedule. After preprocessing, the model-ready schedule contains 18,849 flight records across 135 airports. These values are consistent with the scale reported in the paper, which describes 18,849 domestic Envoy Air flights over January 1-31, 2023 and a network of 135 airports.

The implementation constructs the following primary sets:

```math
F = \text{set of scheduled flights}
```

```math
A = \{\text{ERJ145}, \text{ERJ170}, \text{ERJ175}\}
```

```math
P = \text{set of airports appearing as origins or destinations}
```

Each schedule row is assigned a unique flight identifier of the form `F00001`, `F00002`, and so on. This is an implementation choice, because airline flight numbers repeat across days and may not uniquely identify a flight in a monthly schedule. The unique `FLIGHT_ID` therefore becomes the index $f \in F$ used by the optimization model.

### Time Indexing

The paper discretizes the January 2023 planning horizon into 15-minute time intervals. The implementation follows the same modeling idea by converting each flight's scheduled departure and arrival time into a common reference timezone and then flooring each timestamp to a 15-minute index. This produces the columns:

- `DEP_TIME_INDEX_COMMON`
- `ARR_TIME_INDEX_COMMON`

The processed project data has valid time ordering: no flight in the final cost matrix has `ARR_TIME_INDEX_COMMON <= DEP_TIME_INDEX_COMMON`. The resulting time-space network uses these indices to define when aircraft leave and enter each airport.

An important implementation detail is that the final FAM does not create inventory variables for every possible airport-time pair. Instead, it uses a compressed time-space network containing only active airport-time nodes: time points where at least one arrival or departure occurs at an airport, plus the initial time node. This preserves the logic of the paper's time-space formulation while reducing the number of inventory variables.

### Assignment Cost Generation

The assignment cost parameter is:

```math
c_{f,a}
```

where $f$ is a flight and $a$ is an aircraft type. Following the paper, the total assignment cost is represented as:

```math
c_{f,a} = o_{f,a} + s_{f,a}
```

where $o_{f,a}$ is the operating cost of assigning aircraft type $a$ to flight $f$, and $s_{f,a}$ is the spill cost associated with capacity-constrained passenger demand.

In the implementation, operating cost is calculated using an aircraft-specific cost-per-mile value from Envoy Air Q1 2023 operating expense and mileage data:

```math
o_{f,a} = \text{Distance}_f \times \text{CostPerMile}_a
```

The calculated project values are approximately:

- ERJ145: 10.6036 USD/mile
- ERJ170: 8.4874 USD/mile
- ERJ175: 8.0565 USD/mile

Spill cost is calculated using the same conceptual formula as the paper:

```math
s_{f,a} = \max(D_f - C_a, 0) \times R_f
```

where $D_f$ is average passenger demand for the route, $C_a$ is the seating capacity of aircraft type $a$, and $R_f$ is the average fare for the origin-destination route. The capacities used in the implementation are:

- ERJ145: 50 seats
- ERJ170: 65 seats
- ERJ175: 76 seats

Demand inputs are based on T-100 route-level data, while fare inputs are based on DB1B route fare data. The project route input file contains 530 T-100 route records. The final cost matrix contains 18,849 flight rows and cost columns for all three aircraft types.

### Fare Imputation Limitation

The paper estimates demand and fares using a longer historical data window. For spill cost, it uses multi-year historical T-100 passenger/departure data and DB1B fare data, excluding the COVID-affected years 2020 and 2021. In the current recreation, the demand and fare pipeline is narrower: demand is derived from January 2023 T-100 route data, while fares are derived from Q1 2023 DB1B route data. This means the formula for spill cost is structurally the same as the paper, but the numerical estimates of $D_f$ and $R_f$ are not identical.

In addition, some January 2023 route fares were missing from the available DB1B-derived route file. To avoid leaving undefined cost coefficients in the optimization model, the implementation temporarily imputes missing fares for routes used in the January schedule.

The imputation logic is:

1. Use the reverse route fare if the reverse direction has an original DB1B fare.
2. Otherwise, use the median fare of similar routes with nearby distance and shared origin or destination.
3. If needed, fall back to nearby-distance routes in the broader network.

This affected 66 flight records in the final cost matrix, corresponding to four directed routes: AGS-CLT, CLT-GSP, DCA-MSP, and GSP-CLT. This is a project-specific approximation and should be treated as a limitation. It helps complete the cost matrix, but it is not equivalent to the full fare-estimation pipeline described in the paper.

## 3. Initial Aircraft Position Reconstruction

The FAM requires an initial aircraft distribution:

```math
y_{a,p,0}
```

which represents the number of aircraft of type $a$ initially located at airport $p$ at the beginning of the planning horizon.

The paper notes that the model assumes initial conditions are available. In a real airline setting, these could come from the previous finalized schedule or internal aircraft-routing data. In this recreation, the exact initial aircraft locations were not directly available. Therefore, a proxy reconstruction was developed from observed tail-number activity in the processed schedule.

For each tail number, the implementation identifies the earliest non-cancelled observed departure in the January schedule. The origin airport of that earliest departure is used as the proxy initial airport for that physical aircraft. This produces a tail-level table and then an aggregate aircraft-type/airport table:

```math
y^{proxy}_{a,p}
```

This proxy method is operationally reasonable for reconstructing a starting state from public schedule observations, but it is not guaranteed to reproduce the true historical initial aircraft positions. It assumes that the first observed departure airport in the month is the aircraft's starting location for the model horizon. That assumption can fail when the available data starts after aircraft have already been repositioned, when flights are cancelled, or when the observed schedule does not fully capture pre-horizon aircraft movements.

The fleet validation from the reconstructed tail-level data gives:

- ERJ145: 28 aircraft
- ERJ170: 8 aircraft
- ERJ175: 101 aircraft
- Total: 137 aircraft

This matches the implementation's processed fleet. The paper text contains a minor inconsistency: one part describes 137 aircraft including 101 ERJ175s, while a later model-description passage refers to 103 ERJ175s. The project uses the 101 ERJ175 aircraft observed in the processed schedule and FAA/tail-number mapping.

## 4. Fleet Assignment Model Formulation

The implemented FAM follows the paper's integer linear programming structure. The model assigns aircraft types to flights while enforcing coverage, aircraft range feasibility, airport-time flow balance, initial aircraft positions, and inventory precedence.

### Decision Variables

The primary assignment variable is:

```math
x_{f,a} \in \{0,1\}
```

where:

```math
x_{f,a} =
\begin{cases}
1, & \text{if flight } f \text{ is assigned aircraft type } a \\
0, & \text{otherwise}
\end{cases}
```

The model also uses two aircraft inventory variables at each active airport-time node:

```math
y^-_{a,p,t}
```

and:

```math
y^+_{a,p,t}
```

The variable $y^-_{a,p,t}$ represents the number of aircraft of type $a$ available at airport $p$ immediately before processing events at time $t$. The variable $y^+_{a,p,t}$ represents the number of aircraft of type $a$ remaining at airport $p$ immediately after processing arrivals and departures at that same time node.

This distinction is useful because arrivals and departures can occur at the same airport-time node. The model can express the conservation of aircraft before and after the events at that node without losing track of event ordering.

### Objective Function

The objective minimizes total assignment cost:

```math
\min \sum_{f \in F} \sum_{a \in A} c_{f,a} x_{f,a}
```

This is the implemented version of the paper's cost-minimization objective. It does not maximize revenue directly; passenger revenue enters indirectly through spill cost, which penalizes assigning aircraft with insufficient capacity to high-demand routes.

### Flight Coverage

Each flight must receive exactly one aircraft type:

```math
\sum_{a \in A} x_{f,a} = 1 \quad \forall f \in F
```

This constraint ensures that no flight is unassigned and no flight is assigned multiple aircraft types.

### Aircraft Range Constraint

The paper includes a range feasibility constraint. In the implementation, range-infeasible assignments are fixed to zero:

```math
x_{f,a} = 0 \quad \text{if } d_f > r_a
```

where $d_f$ is the route distance and $r_a$ is the maximum range of aircraft type $a$. Since the paper does not provide all numerical range values used in the implementation, public aircraft range specifications are used and converted from nautical miles to statute miles to match the BTS distance units.

## 5. Flow Balance Formulation

The core of the FAM is the time-space network flow balance. For each aircraft type, airport, and active time node, the model enforces:

```math
y^-_{a,p,t}
+
\sum_{f \in Arr(p,t)} x_{f,a}
=
y^+_{a,p,t}
+
\sum_{f \in Dep(p,t)} x_{f,a}
```

The interpretation is:

```math
\text{aircraft available before events}
+
\text{arriving aircraft}
=
\text{aircraft remaining after events}
+
\text{departing aircraft}
```

This equation prevents the model from using aircraft that are not physically available at an airport. If two aircraft depart from an airport early in the horizon, the model must have enough initial inventory or prior arrivals to support those departures.

The implementation creates arrival and departure event lookups from the schedule. Conceptually, the preprocessing logic counts or stores events such as:

```python
arrivals[destination, arr_t] += 1
departures[origin, dep_t] += 1
```

In the final FAM script, the event dictionaries store flight IDs rather than simple counts. For example, if flight $f$ arrives at airport $p$ at time $t$, then $f$ is included in `arrivals[(p,t)]`. If it departs from airport $p$ at time $t$, then $f$ is included in `departures[(p,t)]`. The optimization model then sums the corresponding $x_{f,a}$ variables over those arrival and departure sets.

The initial condition constraint is:

```math
y^-_{a,p,0} = y_{a,p,0}
```

This anchors the time-space network to the reconstructed initial aircraft positions.

The precedence constraint connects consecutive active time nodes at each airport:

```math
y^-_{a,p,t_i} = y^+_{a,p,t_{i-1}}
```

where $t_{i-1}$ is the previous active time node at airport $p$. This is the compressed-network equivalent of carrying aircraft inventory forward through time.

## 6. Initial Infeasibility Investigation

The first version of the FAM using the proxy initial aircraft positions was infeasible. This did not immediately imply that the fleet was too small. In a time-space FAM, infeasibility can arise either because there are too few aircraft overall or because available aircraft are incorrectly positioned at the start of the horizon.

The diagnostic process first checked the total aircraft requirement implied by cumulative airport flows. The project context records:

- Current initial aircraft: 137
- Minimum required aircraft by schedule: 118

Therefore, the problem was not an aggregate shortage of aircraft. The total reconstructed fleet was larger than the minimum number of aircraft required by the schedule's departure-arrival pattern.

The next diagnostic examined airport-level initial inventory requirements. Before repair, two airports were identified as having deficits:

- LEX: proxy initial = 1, required initial = 2
- PHX: proxy initial = 0, required initial = 1

The LEX example illustrates the operational meaning of the diagnostic. If LEX starts with only one aircraft but has two early departures before sufficient arrivals occur, then the cumulative inventory becomes negative:

```math
1 - 1 - 1 = -1
```

That violates the nonnegative aircraft inventory logic of the FAM. In practical terms, the schedule asks LEX to send out more aircraft than are initially available there.

This diagnosis shows that the original proxy $y^{proxy}_{a,p}$ was not fully compatible with the time-space network, even though its total fleet count was correct.

## 7. Manual Feasibility Repair

A temporary manual feasibility repair was used as a debugging step. Its purpose was not to create a final rigorous reconstruction of initial positions, but to test whether the infeasibility could be resolved by changing the initial placement while preserving fleet totals.

The project context records the manual relocation logic as:

- ERJ145: ORD -> PHX
- ERJ175: MIA -> MGM

The ORD -> PHX relocation is directly interpretable from the airport deficit diagnostic: PHX had zero initial aircraft and required one. ORD had surplus initial aircraft, so moving one ERJ145 from ORD to PHX was a plausible manual fix.

The MIA -> MGM relocation requires more caution in the report. The original diagnostic identified LEX and PHX as deficits, not MGM. Therefore, it would be incorrect to state that the diagnostic found a missing aircraft at MGM. The MGM movement was a heuristic debugging relocation that helped test whether changing the initial placement could make the larger FAM feasible. It should be described as a temporary engineering intervention, not as a mathematically derived conclusion about MGM.

This distinction is important for academic reporting. The manual repair demonstrated that the infeasibility was associated with the initial placement reconstruction, but it did not provide a formally justified final initial-condition method.

## 8. Optimization-Based Initial Position Repair

To replace manual trial-and-error, a small minimum-change MILP was implemented to repair the initial aircraft distribution. The goal was to find a new initial distribution $y^{new}_{a,p}$ that remains as close as possible to the proxy distribution $y^{proxy}_{a,p}$, while preserving aircraft counts by type and satisfying airport-level minimum initial inventory requirements.

The repair model minimizes the L1 deviation:

```math
\min \sum_{a \in A} \sum_{p \in P}
\left| y^{new}_{a,p} - y^{proxy}_{a,p} \right|
```

Because absolute values are not directly linear, the implementation introduces positive and negative deviation variables:

```math
y^{new}_{a,p} - y^{proxy}_{a,p}
= d^+_{a,p} - d^-_{a,p}
```

and minimizes:

```math
\sum_{a,p} (d^+_{a,p} + d^-_{a,p})
```

The fleet preservation constraints are:

```math
\sum_{p \in P} y^{new}_{a,p} = Fleet_a
\quad \forall a \in A
```

These constraints prevent the repair model from creating or deleting aircraft. The final repaired fleet remains:

- ERJ145: 28
- ERJ170: 8
- ERJ175: 101
- Total: 137

The airport feasibility constraints are:

```math
\sum_{a \in A} y^{new}_{a,p} \ge Required_p
\quad \forall p \in P
```

where $Required_p$ is computed from the most negative cumulative arrival-departure balance at airport $p$. Operationally, this requires each airport to start with enough aircraft to survive its early departure pressure before incoming aircraft replenish inventory.

The optimization repair found a minimum total L1 deviation of 4, equivalent to two aircraft relocations. The final changes from the proxy distribution are:

- ERJ145 at ORD: 8 -> 7
- ERJ145 at PHX: 0 -> 1
- ERJ175 at MIA: 3 -> 2
- ERJ175 at MGM: 0 -> 1

This exactly preserves aircraft counts by type. As with the manual repair, the MGM placement should be interpreted carefully. The repair model is an aggregate initial-position repair, not a full historical aircraft-route reconstruction. It finds the closest feasible aggregate initial distribution under the selected constraints; it does not prove that an ERJ175 was historically located at MGM.

## 9. Final FAM Results

After replacing the infeasible proxy initial positions with the repaired initial positions, the project context records the final FAM solver status as:

```math
\text{Optimal}
```

with objective value:

```math
79.1 \text{ million USD}
```

The committed run summary records the following assignment counts:

- ERJ145: 514 flights
- ERJ170: 975 flights
- ERJ175: 17,360 flights

These counts sum to 18,849 flights, matching the full schedule size.

The paper reports a conventional baseline objective of approximately 73.1 million USD. The recreated model's objective is therefore higher by approximately 6.0 million USD, or about 8.2 percent:

```math
\frac{79.1 - 73.1}{73.1} \approx 8.2\%
```

This difference is plausible given the known differences between the paper pipeline and the recreation. The paper discusses both an initial average cost-per-mile matrix and a more detailed operating-cost estimation approach using fuel burn and labor assumptions. The recreation currently uses a cost-per-mile operating-cost approximation plus spill costs. In addition, the recreation uses project-specific fare imputation for missing DB1B routes, reconstructs initial positions from first observed tail departures, and uses a processed fleet count of 101 ERJ175 aircraft rather than the 103 ERJ175 count appearing in one part of the paper.

The comparison should therefore be presented as a benchmark validation, not as an exact reproduction. The recreated model has the same structural logic and dataset scale, but it does not fully replicate every proprietary, historical, or aircraft-performance input used in the paper. Based on the project debugging context, the initial-position repair itself appears to be a relatively small contributor to the objective gap; the larger expected drivers are the operating-cost matrix and the spill-cost inputs.

## 10. Limitations and Future Work

The first limitation is the reconstruction of initial aircraft positions. The proxy method based on first observed tail departures is transparent and auditable, but it does not necessarily equal the true initial aircraft distribution at the start of January 2023. The repair model improves feasibility, but it remains a minimum-change aggregate correction rather than a full historical aircraft-routing reconstruction. A stronger future version would solve a repair problem with the full time-space flow balance embedded directly, forcing the repair to satisfy the same temporal logic as the final FAM.

The second limitation is fare and demand calibration. The paper estimates demand and fares from a longer historical BTS data window, excluding COVID-affected years. The project recreation currently uses January 2023 demand and Q1 2023 fare inputs, then applies temporary fare imputation where needed. This allows the FAM to run with complete cost coefficients, but the resulting spill costs may differ materially from the paper's spill-cost matrix.

The third limitation is operating-cost fidelity. The current implementation uses aircraft-level cost per mile multiplied by route distance. This follows the paper's initial cost-matrix idea, but the paper also discusses a more detailed cost estimation method involving fuel burn modeling and labor cost. A more complete recreation would implement the detailed fuel/labor operating-cost matrix before comparing objectives against the 73.10 million USD benchmark.

The fourth limitation is that the current project focuses on the conventional baseline FAM. The paper's broader contribution is the integration of hybrid-electric aircraft scenarios, including HEA assignment costs, charging cost, battery-related assumptions, and mixed-fleet scenario analysis. Extending the current implementation to hybrid-electric or hydrogen aircraft would require additional aircraft technology assumptions, energy-cost modeling, range and charging constraints, and potentially airport infrastructure constraints.

Future work should therefore prioritize:

- improving initial aircraft position reconstruction with full time-space consistency,
- implementing the paper's detailed operating-cost methodology,
- replacing temporary fare imputation with a broader historical DB1B/T-100 pipeline,
- saving final assignment tables and solver logs for reproducibility,
- extending the model to hybrid-electric or hydrogen aircraft transition scenarios,
- adding validation reports that compare assignment counts, objective components, and route-level aircraft choices against paper benchmarks.

## Conclusion

This project successfully recreates the core conventional Fleet Assignment Model structure from the ICAS 2024 paper using public or processed Envoy Air January 2023 data. The implementation constructs the flight, aircraft, airport, time, cost, and initial-condition inputs required for a time-space FAM; identifies and repairs an initial-condition infeasibility; and solves the resulting assignment model to optimality according to the project-reported final run.

The most important technical result is not only the final objective value, but the debugging path that made the model feasible. The initial infeasibility was traced to the reconstructed starting aircraft locations rather than to a shortage of aircraft. A minimum-change MILP repair then produced a feasible initial distribution while preserving fleet composition. This makes the final FAM solution a credible reproduction of the paper's conventional baseline structure, while also highlighting where the recreation still differs from the full paper methodology.
