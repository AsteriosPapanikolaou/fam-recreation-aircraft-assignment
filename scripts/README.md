# Scripts

The scripts implement the complete data-preparation, optimization and validation workflow. Run them from the repository root, or set `FAM_RECREATION_ROOT` to the root of another local data copy.

## Execution order

1. `clean_ontime_data.py` : reduce the BTS On-Time extract to the schedule fields used by the project.
2. `prepare_common_time_schedule.py` : normalize airport local times to Central Time.
3. `create_time_indices.py` : create 15-minute time indices.
4. `match_faa_aircraft_types.py` : enrich the schedule with FAA aircraft-type metadata.
5. `prepare_model_schedule.py` : create the model-ready schedule table.
6. `process_t100.py` : prepare Envoy T-100 demand inputs.
7. `process_db1b.py` : filter and clean the DB1B market extract.
8. `calculate_route_fares.py` : calculate passenger-weighted route fares.
9. `process_operating_expenses.py` : prepare P-5.2 operating expenses.
10. `calculate_cost_per_mile.py` : calculate aircraft-type cost per mile.
11. `build_route_inputs.py` : combine demand and fare inputs.
12. `build_assignment_cost_matrix.py` : calculate operating, spill and total assignment costs.
13. `build_initial_positions.py` : create the tail-level proxy fleet position table.
14. `build_feasible_initial_positions.py` : solve the minimum-change feasibility repair.
15. `solve_fam.py` : solve the time-space fleet assignment MILP.
16. `validate_assignments.py` : compare FAM assignments with observed aircraft types.

## Common commands

```powershell
python scripts/solve_fam.py
python scripts/validate_assignments.py
```

The model-only run uses the committed processed cost matrix and feasible initial-position table. The full preprocessing chain additionally requires the raw public source files described in [docs/data-sources.md](../docs/data-sources.md).
