# Script order

The scripts are intentionally kept close to the research workflow. Run them from the repository root, or set `FAM_RECREATION_ROOT` to the root of another local data copy.

## Full preprocessing chain

1. `data_clean_on_time.py` — reduce the BTS On-Time extract to the schedule fields used by the project.
2. `schedule_preparation_with_central_time.py` — normalize airport local times to Central Time.
3. `15_min_time_local_time.py` — create 15-minute time indices.
4. `FAA_matching_with_BTS_tail_number.py` — enrich the schedule with FAA aircraft-type metadata.
5. `clean_schedule.py` — create the model-ready schedule table.
6. `Τ100data.py` — prepare Envoy T-100 demand inputs.
7. `D1B1.py` — filter and clean the DB1B market extract.
8. `avg_fare_calc.py` — calculate passenger-weighted route fares.
9. `process_p52.py` — prepare P-5.2 operating expenses.
10. `cost_per_mile.py` — calculate aircraft-type cost per mile.
11. `route_inputs_ready.py` — combine demand and fare inputs.
12. `build_initial_cost_matrix.py` — calculate operating, spill and total assignment costs.
13. `build_initial_positions.py` — create the tail-level proxy fleet position table.
14. `build_feaible_initial_positions.py` — solve the minimum-change feasibility repair.
15. `solve_FAm.py` — solve the time-space fleet assignment MILP.
16. `validation_with_real_data.py` — compare FAM assignments with observed aircraft types.

The spelling of `build_feaible_initial_positions.py` and the Greek-character filename `Τ100data.py` are preserved from the working project for traceability.
