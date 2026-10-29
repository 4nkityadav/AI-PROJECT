# Comparative Algorithm Analysis: Timetable Scheduling

## 1. Overview of Implemented Solvers

The Timetable Scheduler incorporates five distinct algorithmic paradigms, allowing direct experimental comparisons between systematic tree search, local search, metaheuristics, and hybrid approaches.

```
                         ┌────────────────────────────────────────────────────────┐
                         │              AI Timetable Solver Paradigms             │
                         └──────────────────────────┬─────────────────────────────┘
                                                    │
                 ┌──────────────────────────────────┴───────────────────────────────────┐
                 ▼                                                                      ▼
      Systematic Search (Tree)                                            Local Search / Metaheuristics
      ├── Backtracking (Plain)                                           ├── Min-Conflicts
      └── Backtracking (MRV + Deg + FC + AC-3)                           ├── Simulated Annealing
                                                                         ├── Hill Climbing (Steepest Ascent)
                                                                         └── Hybrid (BT Feasibility + SA Optimization)
```

---

## 2. Theoretical Comparison Table

| Attribute | Backtracking (Plain) | Backtracking (Heuristic) | Min-Conflicts | Hill Climbing | Simulated Annealing | Hybrid (BT + SA) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Search Paradigm** | Depth-First Tree Search | Informed CSP Search | Local Repair Search | Gradient Descent | Probabilistic Metaheuristic | Two-Phase (Exact + Meta) |
| **Completeness** | Complete (given $\infty$ time) | Complete | Incomplete | Incomplete | Incomplete (probabilistically complete) | Complete for feasibility |
| **Optimality (Soft)** | No (stops at 1st valid) | No (feasibility focus) | Weak | Local optimum only | Near-optimal (escapes local minima) | **High (Near-optimal)** |
| **Time Complexity** | $O(d^n)$ worst-case | $O(d^n)$ (pruned $10^3\times$) | $O(\text{iter} \cdot n \cdot d)$ | $O(\text{restarts} \cdot \text{steps} \cdot n \cdot d)$ | $O(\text{steps} \cdot \Delta E)$ | $O(\text{BT}) + O(\text{SA})$ |
| **Space Complexity**| $O(n \cdot d)$ | $O(n \cdot d)$ | $O(n)$ | $O(n)$ | $O(n)$ | $O(n \cdot d)$ |
| **Best Used For** | Theoretical baseline | **Fast Feasible Timetables** | Loosely constrained CSPs | Quick heuristic baseline | Fine-tuning soft penalties | **Production Timetabling** |

---

## 3. Detailed Algorithmic Breakdown

### 3.1 Systematic Backtracking CSP (`core/backtracking.py`)
- **How it works:** Assigns variables one at a time. If an assignment violates any constraint, it immediately undoes the choice (backtracks).
- **Heuristics:** Combines MRV (variable ordering), Degree (tie-breaking), LCV (value ordering), Forward Checking (pruning), and AC-3 (arc consistency).
- **Strengths:** 100% guarantee of finding a zero-hard-violation solution if one exists (complete). Runs in milliseconds on well-formulated instances.
- **Weaknesses:** Highly sensitive to variable ordering without heuristics; treats soft constraints as secondary unless extended into Branch-and-Bound.

---

### 3.2 Min-Conflicts Local Search (`core/min_conflicts.py`)
- **How it works:**
  1. Starts with a complete initial assignment (even if conflicted).
  2. At each iteration, selects a variable $x_i$ currently involved in at least one conflict.
  3. Reassigns $x_i$ to the value $v \in D(x_i)$ that minimizes total hard conflicts.
  4. Includes a random-walk probability ($p = 0.05$) and periodic random restarts to break out of cycles.
- **Strengths:** Extremely memory efficient ($O(n)$); solves loosely constrained problems in linear time ($O(n)$).
- **Weaknesses:** Vulnerable to plateaus and tight cyclic bottlenecks in heavily constrained timetables where no single variable change can reduce conflicts.

---

### 3.3 Steepest-Ascent Hill Climbing with Random Restarts (`core/hill_climbing.py`)
- **How it works:**
  1. Evaluates all valid 1-step neighbourhood moves (moving a session to another valid slot or swapping two sessions of the same type).
  2. Greedily selects the neighbour that yields the largest cost reduction: $\min \Delta \text{Cost}$.
  3. Terminates at a local optimum ($\Delta \text{Cost} \ge 0$).
  4. Automatically executes random restarts from different seeds if hard violations persist.
- **Strengths:** Fast convergence to local optima; simple to implement and inspect.
- **Weaknesses:** Cannot escape ridges, local minima, or plateaus without full restarts.

---

### 3.4 Simulated Annealing (`core/annealing.py`)
- **How it works:** Inspired by metallurgy annealing, it explores the search space by accepting both cost-improving moves and, probabilistically, cost-worsening moves:
  $$P(\text{accept}) = \begin{cases} 1.0 & \text{if } \Delta E < 0 \\ \exp\left(-\frac{\Delta E}{T}\right) & \text{if } \Delta E \ge 0 \end{cases}$$
- **Cooling Schedule:** Starts at $T_0 = 100.0$, cools geometrically $T_{k+1} = \alpha \cdot T_k$ with $\alpha = 0.995$.
- **Neighbourhood Operators:**
  1. `Move`: Reassign one session to a different valid slot/room.
  2. `Swap`: Swap timeslots between two compatible sessions.
  3. `Room-Only Change`: Keep time constant and reassign room.
- **Strengths:** Robustly escapes local minima; simultaneously optimizes both hard constraints and complex soft preferences.
- **Weaknesses:** Takes more iterations (10–15 seconds) compared to backtracking.

---

### 3.5 Hybrid Solver (`core/hybrid.py`)
- **How it works:** A two-stage pipeline combining the unique advantages of systematic search and metaheuristics:
  - **Phase 1 (Backtracking with Heuristics):** Rapidly finds a **100% hard-constraint-free** feasible timetable in $< 0.1$s.
  - **Phase 2 (Simulated Annealing on Feasible Subspace):** Takes the feasible timetable as starting state and runs SA with high penalty on hard violations ($\lambda_{hard} = 1000$), exploring neighbourhood moves that preserve feasibility while driving soft penalties down to zero.
- **Outcome:** Produces timetables with **0 Hard Violations** AND **optimal or near-zero Soft Penalties** (e.g., zero student gaps, zero teacher preference clashes).
