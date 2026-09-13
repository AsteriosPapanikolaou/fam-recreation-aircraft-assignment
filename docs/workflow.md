# FAM recreation workflow

```mermaid
flowchart TD
    raw[Raw public aviation extracts]
    schedule[Clean and time-index schedule]
    demand[Build T-100 demand]
    fares[Build DB1B route fares]
    costs[Build operating + spill cost matrix]
    fleet[Reconstruct and repair initial positions]
    solve[Solve time-space FAM]
    validate[Validate against observed aircraft types]
    report[Export diagnostics and report]

    raw --> schedule
    raw --> demand
    raw --> fares
    schedule --> costs
    demand --> costs
    fares --> costs
    costs --> fleet
    fleet --> solve
    solve --> validate
    validate --> report
```

The optimization layer uses three aircraft types — ERJ145, ERJ170 and ERJ175 — and a compressed airport/time network containing active event nodes. This keeps the flow-balance formulation faithful to the paper while avoiding inventory variables for every possible airport/time combination.
