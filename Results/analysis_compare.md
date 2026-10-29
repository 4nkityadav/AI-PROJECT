# Experimental Analysis — compare

## Comparison Table

| Algorithm       |   Avg Time (s) |   Avg Nodes/Iter |   Avg Hard Violations |   Avg Soft Penalty | Success Rate   |   Min Time |   Max Time | Status   |
|:----------------|---------------:|-----------------:|----------------------:|-------------------:|:---------------|-----------:|-----------:|:---------|
| BT (Heuristics) |         0.011  |               36 |                     0 |                 37 | 1/1            |     0.011  |     0.011  | solved   |
| Min-Conflicts   |         0.0115 |               13 |                    18 |                 15 | 0/1            |     0.0115 |     0.0115 | failed   |

## Heuristic Ablation (Backtracking)

| Configuration     |   Time (s) |   Nodes |   Hard Violations |   Soft Penalty | Status   |
|:------------------|-----------:|--------:|------------------:|---------------:|:---------|
| Plain             |     0.0026 |      37 |                 0 |             31 | solved   |
| MRV only          |     0.0029 |      36 |                 0 |             30 | solved   |
| FC only           |     0.0089 |      36 |                 0 |             26 | solved   |
| MRV+FC            |     0.0107 |      36 |                 0 |             24 | solved   |
| MRV+FC+Degree     |     0.0108 |      36 |                 0 |             24 | solved   |
| MRV+FC+Degree+LCV |     0.2492 |      36 |                 0 |             48 | solved   |
| All + AC3         |     0.2809 |      36 |                 0 |             48 | solved   |

## Analysis (DRAFT — rewrite in your own words)

- **Fastest method**: BT (Heuristics) (0.0110s average)
- **Slowest method**: Min-Conflicts (0.0115s average)
- **Best soft-constraint quality**: Min-Conflicts (penalty=15.0)

### When to use each method:
- **Backtracking (Plain)**: Good for understanding; may be slow on large instances.
- **Backtracking (Heuristics)**: Best for guaranteed solutions on moderate-sized problems.
- **Min-Conflicts**: Fast for finding any valid solution; quality varies across runs.
- **Simulated Annealing**: Good balance of quality and flexibility; tune parameters carefully.
- **Hybrid (BT+SA)**: Best overall quality — guarantees feasibility while optimising soft constraints.
- **Hill Climbing**: Simple but often gets stuck in local minima; useful as a baseline.

*Note: This analysis is auto-generated from experimental data. Rewrite in your own words for the report.*