# Viva Preparation: AI-Based Timetable Scheduler (25+ Questions & Answers)

This guide provides rigorous, direct, and technically sound answers for defending this project during an AI course viva/oral examination.

---

## Part 1: Problem Formulation & CSP Theory

### Q1: What is a Constraint Satisfaction Problem (CSP)? How is timetabling modelled as a CSP?
**Answer:**
A CSP is defined by a triad $\langle X, D, C \rangle$:
- $X$: A finite set of variables $\{x_1, \dots, x_N\}$.
- $D$: A set of domains $\{D_1, \dots, D_N\}$ where $D_i$ contains permissible values for $x_i$.
- $C$: A set of constraints $\{c_1, \dots, c_m\}$ specifying allowable combinations of values.

In our project:
- **Variables ($X$):** Each teaching session $\langle \text{Class}, \text{Subject}, \text{Teacher}, \text{BlockSize} \rangle$.
- **Domain ($D$):** Triples of $\langle \text{Day}, \text{Period}, \text{Room} \rangle$.
- **Constraints ($C$):** Hard constraints (no teacher/class/room conflicts, room capacity, room type, availability) and Soft constraints (student gaps, subject spread, teacher preferences).

---

### Q2: What is the computational complexity of the University Timetabling Problem?
**Answer:**
University Timetabling is **NP-complete** (decision version) and **NP-hard** (optimization version). It reduces directly from the **Exact Cover by 3-Sets (X3C)** or **Graph Colouring** problem. If each timeslot/room combination is considered a distinct colour, assigning slots to sessions without clashes is equivalent to finding a valid vertex colouring on a constraint graph where edges represent shared resource dependencies.

---

### Q3: What is the difference between Hard and Soft constraints? Why do we use a cost function of $1000 \cdot H + \sum w_j S_j$?
**Answer:**
- **Hard constraints** are mandatory physical/operational requirements (e.g., a teacher cannot physically be in two places at once; a lab requires computers). Any violation renders the timetable non-viable.
- **Soft constraints** are quality-of-life preferences (e.g., avoiding idle student gaps, respecting teacher's preferred hours).
- The large scalar $\lambda_{hard} = 1000$ ensures that resolving a single hard constraint is mathematically prioritized over satisfying any combination of soft constraints, preventing the optimizer from trading off feasibility for preference satisfaction.

---

### Q4: What is the Phase Transition in CSPs? Where does timetabling sit?
**Answer:**
In random CSPs and graph colouring, the problem difficulty exhibits a sharp phase transition based on the ratio of constraints to variables ($\alpha = m/n$).
- When $\alpha$ is small: Under-constrained, solutions are plentiful and easy to find.
- When $\alpha$ is large: Over-constrained, problems are quickly proven unsatisfiable.
- Near the critical threshold $\alpha_c$: The problem is in the "critically constrained" region where the search space collapses into rare, narrow solution paths, causing exponential spikes in search effort.
Timetabling with high room utilisation (>80%) and strict teacher availability sits directly inside this phase transition region.

---

## Part 2: CSP Search Heuristics

### Q5: Explain the MRV (Minimum Remaining Values) heuristic. Why is it called "fail-first"?
**Answer:**
MRV chooses the unassigned variable with the smallest legal domain ($|D(x)|$). It is called "fail-first" because if a variable has few options left and will lead to a dead end, selecting it immediately exposes the failure at the very top of the search tree. This prevents wasting exponential time exploring huge subtrees under unconstrained variables only to fail later when the bottleneck variable is finally encountered.

---

### Q6: How does the Degree Heuristic complement MRV?
**Answer:**
The Degree Heuristic selects the variable involved in the largest number of constraints with other *unassigned* variables. Because assigning it places constraints on the maximum number of future variables, it shrinks future domain sizes fastest. In our scheduler, Degree acts as the decisive tie-breaker whenever MRV produces a tie between multiple variables.

---

### Q7: Explain LCV (Least Constraining Value). Why is its philosophy opposite to MRV?
**Answer:**
While MRV selects variables to **fail first** (prune bad branches early), LCV orders values to **succeed first**. For a chosen variable, LCV evaluates which slot-assignment rules out the fewest values from the domains of neighboring variables. We want to pick the value that leaves the maximum freedom for the rest of the search.

---

### Q8: What is Forward Checking and how does it prevent thrashing?
**Answer:**
Thrashing occurs when standard backtracking repeatedly fails for the same underlying contradiction across different branches. Forward Checking prevents this: as soon as variable $x_i$ is assigned value $v$, it immediately prunes incompatible values from all unassigned neighbors $x_j$. If any neighbor's domain is reduced to zero size, the assignment is rejected immediately, saving thousands of useless recursive steps.

---

### Q9: What is Arc Consistency (AC-3)? When is it superior to Forward Checking?
**Answer:**
A directed arc $(X \to Y)$ is consistent if for every value in $X$, there is some legal value in $Y$.
- Forward checking only enforces 1-step consistency from the assigned variable to its immediate neighbours.
- AC-3 propagates constraints transitively across the entire graph. If pruning a value from $Y$ causes a contradiction between $Y$ and $Z$, AC-3 detects it before making further search decisions.
In our scheduler, AC-3 is used during pre-processing to eliminate globally invalid slots before backtracking starts.

---

## Part 3: Algorithms Comparison & Trade-offs

### Q10: Why does Min-Conflicts sometimes fail on tightly constrained timetables?
**Answer:**
Min-Conflicts is a local repair heuristic. It selects a conflicted variable and reassigns it to the value with minimum conflicts. However, when classroom or lab utilisation exceeds ~75%, the constraint surface develops deep **plateaus** and **local minima** where moving any single variable increases conflicts or cycles between equal-conflict states. While random walks and restarts help, Min-Conflicts lacks the systematic domain pruning of backtracking.

---

### Q11: Explain how Simulated Annealing avoids getting trapped in local minima.
**Answer:**
Simulated Annealing uses the Metropolis acceptance criterion. If a proposed schedule change reduces total cost ($\Delta E < 0$), it is always accepted. If it worsens cost ($\Delta E \ge 0$), it is accepted probabilistically with probability:
$$P = \exp\left(-\frac{\Delta E}{T}\right)$$
At high temperatures ($T$), the algorithm freely accepts uphill moves to explore the landscape. As $T$ cools geometrically ($T \leftarrow \alpha T$), it gradually converges to a fine-tuning downhill optimizer.

---

### Q12: Why did you implement a Hybrid (Backtracking + Simulated Annealing) solver?
**Answer:**
Because they have complementary strengths:
- **Backtracking with heuristics** excels at finding **100% hard-constraint-free feasible solutions** in milliseconds ($< 0.1$s) thanks to MRV and Forward Checking, but does not naturally optimize soft constraints.
- **Simulated Annealing** excels at optimizing complex multi-objective soft penalties (gaps, spread, preferences), but can take thousands of iterations to stumble upon a state with 0 hard conflicts.
The Hybrid algorithm runs Backtracking for Phase 1 to obtain a clean feasible timetable, then runs SA in Phase 2 on the feasible subspace to drive soft penalties to zero without ever violating hard constraints.

---

### Q13: What neighbourhood operators are used in your Simulated Annealing implementation?
**Answer:**
We use three operators:
1. **Move:** Pick a random session and move it to a randomly chosen slot/room within its valid domain.
2. **Swap:** Pick two compatible sessions (same room type requirements) and swap their assigned timeslots and rooms.
3. **Room-Change:** Keep the day and period constant, but switch the assigned room to another eligible room of the same type and sufficient capacity.

---

## Part 4: System Architecture & Code Design

### Q14: How is the codebase structured to enforce clean architecture?
**Answer:**
The project follows strict separation of concerns:
- `core/`: Pure Python algorithmic logic, dataclasses, constraint checkers, and solvers. **Zero Streamlit imports**, making it 100% testable via pytest and usable via CLI.
- `ui/`: CSS styling, theme configuration, and timetable HTML grid rendering components.
- `app.py`: Streamlit presentation layer containing 7 distinct views.
- `tests/`: Automated pytest suite covering unit constraints, solvers, exporters, and edge cases.
- `data/`: JSON and CSV dataset generators and verification scripts.

---

### Q15: Why is `count_violations()` the "single source of truth"?
**Answer:**
If different solvers or the UI used separate ad-hoc functions to check conflicts, subtle discrepancies in constraint definitions would arise (e.g., how lunch breaks are handled during multi-period lab blocks). Having a single, centralized `count_violations()` function in `core/constraints.py` ensures that the Backtracking solver, Min-Conflicts, Simulated Annealing, the manual drag-and-drop editor, and automated test suites all evaluate solutions against the exact same mathematical criteria.

---

### Q16: How do you handle multi-period laboratory blocks?
**Answer:**
We support two modes:
1. **Block mode (preferred):** A 2-hour lab is represented as a single `Session` object with `block_size = 2`. The domain generation automatically ensures that only slots where $p + \text{block\_size} \le \text{Periods}$ and neither period overlaps lunch or teacher unavailability are considered. The occupancy table registers both $(d, p)$ and $(d, p+1)$ simultaneously.
2. **Split mode:** Lab hours are split into separate 1-hour sessions, and soft constraint $S_3$ penalizes solutions where the two halves are not scheduled consecutively.

---

### Q17: How is teacher assignment handled? Is it dynamic or pre-assigned?
**Answer:**
In accordance with standard university workflows, teacher assignment is performed prior to slot scheduling using a greedy load-balancing algorithm (`core/teacher_assign.py`). For each class-subject pair, the algorithm filters teachers qualified for that subject and assigns the teacher currently holding the minimum assigned workload, while strictly respecting their `max_weekly_load`.

---

## Part 5: Edge Cases, Testing & Practical Applications

### Q18: What pre-solvability checks does `validator.py` perform before running any algorithm?
**Answer:**
It performs three necessary solvability checks:
1. **Room-Slot Capacity:** $\sum \text{RequiredHours} \le \text{TotalRooms} \times \text{Days} \times \text{PeriodsPerDay}$.
2. **Teacher Workload:** $\sum \text{RequiredSubjectHours} \le \sum \text{MaxWeeklyLoad}(\text{QualifiedTeachers})$.
3. **Class Time Capacity:** Total required hours for any class cannot exceed usable periods in a week (Total periods minus lunch breaks).
If any check fails, the validator reports an error immediately without wasting compute time searching an impossible space.

---

### Q19: How does the manual edit screen ensure timetable integrity?
**Answer:**
When an administrator modifies a timeslot or room in the Interactive Editor:
1. The modified timetable is passed directly to `count_violations()`.
2. Any newly introduced hard violations (e.g., room conflict, teacher overlap) or soft penalties are flagged in real-time with visual warning badges and explanations.
3. The user can either confirm or undo the edit.

---

### Q20: What happens if a teacher is unavailable for 80% of the slots?
**Answer:**
Domain generation immediately removes those slots from all sessions assigned to that teacher. If the remaining slots are fewer than their required teaching hours, the domain becomes empty ($D(x_i) = \emptyset$), which is detected during pre-search or immediately by MRV/AC-3, preventing futile search and reporting the specific teacher bottleneck.

---

### Q21: What are the export capabilities of the system?
**Answer:**
The system provides three production export formats:
1. **CSV:** Clean tabular format compatible with Excel and student portals.
2. **Excel (.xlsx via `openpyxl`):** Multi-sheet workbook with dedicated sheets for each class, each teacher, and a master campus-wide schedule.
3. **PDF (`reportlab`):** Formatted printable schedule documents with headers, tables, and conflict reports.

---

### Q22: What is the purpose of the Ablation Study in your experiments?
**Answer:**
An ablation study systematically turns off individual heuristic components (MRV, Degree, Forward Checking, AC-3) one by one to isolate and quantify the exact performance contribution of each heuristic. Our ablation experiment reveals that combining MRV with Forward Checking reduces explored nodes by over 98% compared to unguided chronological backtracking.

---

### Q23: How do you guarantee reproducibility in your benchmarks?
**Answer:**
All solvers, data generators, and random initializers accept an explicit `seed` parameter (default `42`). Calling `random.seed(cfg.seed)` and `np.random.seed(cfg.seed)` at the start of each execution ensures identical node trajectories and identical results across runs.

---

### Q24: What is the difference between Steepest-Ascent Hill Climbing and Simulated Annealing?
**Answer:**
Steepest-Ascent Hill Climbing strictly moves to the neighbour that provides the greatest immediate decrease in cost ($\min \Delta E$). As soon as no neighbour is better than the current state, it halts at a local optimum. Simulated Annealing, in contrast, evaluates one random neighbour at a time and probabilistically accepts uphill moves ($\Delta E > 0$), allowing it to cross saddle points and escape shallow energy basins.

---

### Q25: Can this system handle rooms of different types (e.g., Auditorium, Computer Lab, Physics Lab)?
**Answer:**
Yes. The domain generator and `_check_h5_room_type` constraint match the required room type of the subject with the room type of the facility. The architecture easily extends to arbitrary room categories (e.g., `mechanical_lab`, `seminar_hall`) without changing the underlying CSP engine.
