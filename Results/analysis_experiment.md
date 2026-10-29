# Experimental Analysis — experiment

## Comparison Table

| Algorithm           |   Avg Time (s) |   Avg Nodes/Iter |   Avg Hard Violations |   Avg Soft Penalty | Success Rate   |   Min Time |   Max Time | Status   |
|:--------------------|---------------:|-----------------:|----------------------:|-------------------:|:---------------|-----------:|-----------:|:---------|
| BT (Plain)          |         0.0318 |               59 |                     0 |               60   | 1/1            |     0.0318 |     0.0318 | solved   |
| BT (Heuristics)     |         0.1864 |               59 |                     0 |               60   | 1/1            |     0.1864 |     0.1864 | solved   |
| Min-Conflicts       |         0.0366 |                1 |                     0 |               66   | 10/10          |     0.0332 |     0.0391 | mixed    |
| Simulated Annealing |        30.0282 |            21395 |                     0 |                9.4 | 10/10          |    30.0013 |    30.0565 | mixed    |
| Hybrid (BT+SA)      |         7.7179 |            21304 |                     0 |                0   | 10/10          |     6.7181 |     8.5833 | mixed    |
| Hill Climbing       |         6.7768 |               72 |                     0 |               59.6 | 10/10          |     6.3414 |     7.4408 | mixed    |

## Heuristic Ablation (Backtracking)

| Configuration     |   Time (s) |   Nodes |   Hard Violations | Soft Penalty   | Status   |
|:------------------|-----------:|--------:|------------------:|:---------------|:---------|
| Plain             |     0.0382 |      59 |                 0 | 63.0           | solved   |
| MRV only          |     0.0393 |      59 |                 0 | 42.0           | solved   |
| FC only           |     0.203  |      59 |                 0 | 46.0           | solved   |
| MRV+FC            |     0.2145 |      59 |                 0 | 63.0           | solved   |
| MRV+FC+Degree     |     0.217  |      59 |                 0 | 63.0           | solved   |
| MRV+FC+Degree+LCV |    11.3224 |    1175 |                -1 | N/A            | timeout  |
| All + AC3         |    10.4354 |    1039 |                -1 | N/A            | timeout  |

## Analysis (DRAFT — rewrite in your own words)

- **Fastest method**: BT (Plain) (0.0318s average)
- **Slowest method**: Simulated Annealing (30.0282s average)
- **Best soft-constraint quality**: Hybrid (BT+SA) (penalty=0.0)

### When to use each method:
- **Backtracking (Plain)**: Good for understanding; may be slow on large instances.
- **Backtracking (Heuristics)**: Best for guaranteed solutions on moderate-sized problems.
- **Min-Conflicts**: Fast for finding any valid solution; quality varies across runs.
- **Simulated Annealing**: Good balance of quality and flexibility; tune parameters carefully.
- **Hybrid (BT+SA)**: Best overall quality — guarantees feasibility while optimising soft constraints.
- **Hill Climbing**: Simple but often gets stuck in local minima; useful as a baseline.

*Note: This analysis is auto-generated from experimental data. Rewrite in your own words for the report.*