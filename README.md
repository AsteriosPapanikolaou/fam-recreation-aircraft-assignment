# Envoy Air Fleet Assignment Model Recreation

Recreation of the conventional Fleet Assignment Model (FAM) described in the ICAS 2024 paper *Optimizing Fleet Assignment Decisions for Regional Airlines with Hybrid Electric Aircraft Uptake*. The implementation uses Envoy Air's January 2023 schedule, a time-space network, aircraft-type assignment costs, and PuLP/CBC mixed-integer optimization.

> This repository is a research recreation and benchmark implementation. It is not an exact reproduction of every proprietary, historical, or aircraft-performance input used in the paper.

## What this project does

The model assigns each scheduled flight to one of three regional aircraft types:

| Aircraft | Role in the recreation |
| --- | --- |
| ERJ145 | 50-seat regional jet |
| ERJ170 | 65-seat regional jet |
| ERJ175 | 76-seat regional jet |

The optimization minimizes total assignment cost while enforcing:

- one aircraft type per flight,
- aircraft range feasibility,
- airport/time-space flow balance,
- initial aircraft positions,
- continuity of aircraft inventory between active time nodes.

## Workflow

```mermaid
flowchart LR
    A[Public BTS, T-100, DB1B and FAA data] --> B[Clean schedule and financial inputs]
    B --> C[Convert local times to common 15-minute indices]
    C --> D[Build route demand and fare inputs]
    D --> E[Build aircraft assignment cost matrix]
    E --> F[Reconstruct and repair initial fleet positions]
    F --> G[Solve FAM with PuLP + CBC]
    G --> H[Export assignments, fleet mix and run summary]
    H --> I[Validate against FAA-enriched observed aircraft types]
    I --> J[CSV/JSON diagnostics and technical report]
```

## Snapshot of the current run

The committed result snapshot contains:

- **18,849** scheduled flights;
- **Optimal** CBC solution;
- objective value **$79,096,176.93**;
- fleet of **137 aircraft**: 28 ERJ145, 8 ERJ170 and 101 ERJ175;
- eligible aircraft-type match rate of **74.23%** across 18,367 operated flights with an available observed type;
- cost recomputation check passed within numerical tolerance.

The reported objective is higher than the paper's approximately $73.10M conventional benchmark. The difference is expected because this recreation uses project-specific cost-per-mile estimates, a narrower demand/fare window, fare imputation for missing routes, and reconstructed initial positions.

## Quick start

### 1. Create an environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run the model from the repository root

The repository includes the processed cost matrix and feasible initial-position snapshot needed by the solver:

```powershell
python scripts/solve_FAm.py
```

### 3. Re-run validation

```powershell
python scripts/validation_with_real_data.py
```

### 4. Run the full preprocessing chain

Place the raw public source files in the folder layout described in [docs/data-sources.md](docs/data-sources.md), then run the scripts in the order documented in [scripts/README.md](scripts/README.md).

All scripts default to the repository root. To run them against another local copy, set:

```powershell
$env:FAM_RECREATION_ROOT = "C:\path\to\local\fam-recreation-aircraft-assignment"
```

## Repository layout

```text
.
├── DB1B/                    processed route-fare inputs
├── financial/               operating expense and cost-per-mile inputs
├── initial_conditions/      proxy and repaired fleet positions
├── on_time_data/            processed Envoy schedule data
├── RouteInputs/             demand, fare and assignment-cost matrices
├── T100/                    processed route-demand inputs
├── Results/                 FAM outputs and validation diagnostics
├── scripts/                 preprocessing, optimization and validation code
└── docs/                    technical report and data notes
```

## Data and reproducibility notes

Large raw extracts are deliberately not committed: the original working directory is approximately 2.7 GB, while GitHub is not an appropriate distribution channel for multi-gigabyte raw datasets, duplicate spreadsheets, or third-party source dumps. The repository contains a curated processed snapshot so that the final model and validation can be inspected without exposing private local paths.

See [docs/data-sources.md](docs/data-sources.md) for the included/excluded files and the expected source locations.

## Limitations

1. Initial aircraft positions are reconstructed from observed tail activity and then repaired for feasibility; they are not the airline's confidential historical starting state.
2. Demand and fares use a narrower January/Q1 2023 public-data window than the paper's longer historical calibration.
3. Missing fares are imputed for a small number of schedule routes.
4. Operating cost is approximated with aircraft-type cost per mile multiplied by route distance.
5. The implementation covers the conventional baseline FAM, not the paper's hybrid-electric scenarios.

The full discussion is in [docs/technical-report.md](docs/technical-report.md).

## Citation

Please cite the original ICAS 2024 paper when using the model formulation or discussing the benchmark. This repository contains the recreation code and project-specific implementation notes; it does not redistribute the paper PDF.
