# Experimental Analysis — small

## Comparison Table

| Algorithm           |   Avg Time (s) |   Avg Nodes/Iter |   Avg Hard Violations |   Avg Soft Penalty | Success Rate   |   Min Time |   Max Time | Status   |
|:--------------------|---------------:|-----------------:|----------------------:|-------------------:|:---------------|-----------:|-----------:|:---------|
| BT (Plain)          |         0.0027 |               36 |                     0 |                 32 | 1/1            |     0.0027 |     0.0027 | solved   |
| BT (Heuristics)     |         0.0112 |               36 |                     0 |                 37 | 1/1            |     0.0112 |     0.0112 | solved   |
| Min-Conflicts       |         0.0113 |               13 |                    18 |                 15 | 0/1            |     0.0113 |     0.0113 | failed   |
| Simulated Annealing |        13.0668 |            72650 |                     0 |                  0 | 1/1            |    13.0668 |    13.0668 | solved   |
| Hybrid (BT+SA)      |        15.6241 |            85036 |                     0 |                  0 | 1/1            |    15.6241 |    15.6241 | solved   |
| Hill Climbing       |         0.893  |               62 |                     0 |                 22 | 1/1            |     0.893  |     0.893  | solved   |

## Heuristic Ablation (Backtracking)

| Configuration     |   Time (s) |   Nodes |   Hard Violations |   Soft Penalty | Status   |
|:------------------|-----------:|--------:|------------------:|---------------:|:---------|
| Plain             |     0.0032 |      37 |                 0 |             31 | solved   |
| MRV only          |     0.0031 |      36 |                 0 |             30 | solved   |
| FC only           |     0.01   |      36 |                 0 |             26 | solved   |
| MRV+FC            |     0.0122 |      36 |                 0 |             24 | solved   |
| MRV+FC+Degree     |     0.0124 |      36 |                 0 |             24 | solved   |
| MRV+FC+Degree+LCV |     0.2748 |      36 |                 0 |             48 | solved   |
| All + AC3         |     0.3213 |      36 |                 0 |             48 | solved   |

## Analysis (DRAFT — rewrite in your own words)

- **Fastest method**: BT (Plain) (0.0027s average)
- **Slowest method**: Hybrid (BT+SA) (15.6241s average)
- **Best soft-constraint quality**: Simulated Annealing (penalty=0.0)

### When to use each method:
- **Backtracking (Plain)**: Good for understanding; may be slow on large instances.
- **Backtracking (Heuristics)**: Best for guaranteed solutions on moderate-sized problems.
- **Min-Conflicts**: Fast for finding any valid solution; quality varies across runs.
- **Simulated Annealing**: Good balance of quality and flexibility; tune parameters carefully.
- **Hybrid (BT+SA)**: Best overall quality — guarantees feasibility while optimising soft constraints.
- **Hill Climbing**: Simple but often gets stuck in local minima; useful as a baseline.

*Note: This analysis is auto-generated from experimental data. Rewrite in your own words for the report.*