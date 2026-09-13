# Data sources and repository policy

The research workflow was built from public aviation data and processed files. The GitHub copy is intentionally curated rather than a byte-for-byte mirror.

## Included

- processed Envoy Air January 2023 schedule tables;
- FAA-enriched schedule used by the validation;
- processed T-100 demand and DB1B route-fare tables;
- financial inputs and aircraft-type cost-per-mile table;
- assignment-cost matrix and repaired initial positions;
- FAM output, run summary and validation diagnostics;
- Python scripts and the technical report.

## Not included

- the 1.6 GB raw DB1B market extract;
- raw BTS On-Time extracts and duplicate Excel copies;
- the large FAA `MASTER`, `DEREG`, `DEALER` and related source dumps;
- duplicate ZIP archives and generated Excel exports;
- the original ICAS paper PDF.

These files are either too large for a practical GitHub repository, redundant with the included processed tables, or third-party/source material that should be obtained directly from its publisher or data provider.

## Expected local layout for a full rebuild

The preprocessing scripts expect the original folder names:

```text
<project-root>/
├── DB1B/Origin_and_Destination_Survey_DB1BMarket_2023_1.csv
├── financial/T_F41SCHEDULE_P52.csv
├── financial/T_T100D_SEGMENT_US_CARRIER_ONLY.csv
├── on_time_data/On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2023_1.csv
├── ReleasableAircraft/MASTER.txt
├── ReleasableAircraft/ACFTREF.txt
└── T100/T_T100D_SEGMENT_US_CARRIER_ONLY.csv
```

For a model-only run, the committed processed files are sufficient: `RouteInputs/envoy_jan2023_initial_assignment_costs.csv` and `initial_conditions/envoy_initial_aircraft_positions_feasible.csv` are the key solver inputs.
