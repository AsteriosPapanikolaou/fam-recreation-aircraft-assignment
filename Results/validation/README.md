# Validation outputs

These files compare the FAM aircraft-type assignments with the FAA-enriched observed schedule.

- `assignment_comparison.csv` contains row-level comparison fields.
- `assignment_mismatches.csv` isolates eligible rows where the assigned and observed types differ.
- `assignment_confusion_matrix.csv` summarizes observed-to-assigned aircraft types.
- `fleet_distribution_comparison.csv` compares fleet distributions.
- `mismatches_by_route.csv`, `mismatches_by_date.csv` and `mismatches_by_aircraft_pair.csv` provide diagnostic breakdowns.
- `validation_summary.json` stores the headline validation metrics.
