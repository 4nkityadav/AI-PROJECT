# Mathematical CSP Formulation: AI Timetable Scheduler

## 1. Overview & Problem Definition

The University Timetable Scheduling Problem is modelled as a **Constraint Satisfaction Problem (CSP)** with an **Optimisation Objective (CSOP)**. 

The goal is to assign every teaching session to a specific timeslot and room such that all **Hard Constraints ($H_1 - H_9$)** are strictly satisfied, while minimising the penalty incurred from **Soft Constraints ($S_1 - S_5$)**.

---

## 2. Variables ($X$)

Let $S$ be the set of all weekly lecture and laboratory sessions to be scheduled:
$$X = \{x_1, x_2, \dots, x_N\}$$

Each variable $x_i$ represents an indivisible or block teaching session characterized by a tuple:
$$x_i = \langle c_i, s_i, t_i, b_i, k_i \rangle$$

where:
- $c_i \in C$: Class/batch (e.g., `CS-2A`, `EC-2B`)
- $s_i \in S$: Subject code (e.g., `CS201`, `CS202L`)
- $t_i \in T$: Assigned faculty member (pre-assigned via greedy load-balancing)
- $b_i \in \mathbb{Z}^+$: Block duration in periods ($b_i = 1$ for theory, $b_i = 2$ for lab blocks)
- $k_i \in \mathbb{N}$: Distinct session index for the same $(c_i, s_i)$ pair

---

## 3. Domains ($D$)

The scheduling horizon is defined over:
- Days: $Days = \{0, 1, \dots, D-1\}$ (e.g., 5 days: Monday–Friday)
- Periods: $Periods = \{0, 1, \dots, P-1\}$ (e.g., 6 periods per day)
- Rooms: $Rooms = R_{class} \cup R_{lab}$

Each variable $x_i$ is assigned a value $v_i$:
$$v_i = \langle d_i, p_i, r_i \rangle \in D(x_i)$$

where $d_i \in Days$, $p_i \in Periods$, and $r_i \in Rooms$.

For a session of duration $b_i$, occupying start slot $(d_i, p_i)$ means occupying the consecutive timeslots:
$$\text{Slots}(x_i, v_i) = \{(d_i, p_i + \delta) \mid 0 \le \delta < b_i\}$$

### Domain Pruning Rules (Pre-filtering)
A value $\langle d, p, r \rangle$ is pruned from $D(x_i)$ prior to search if:
1. **Period boundary overflow**: $p + b_i > P$
2. **Fixed breaks**: $\exists \delta \in [0, b_i - 1]$ such that $p + \delta \in \text{Breaks}$
3. **Class lunch break**: $\exists \delta \in [0, b_i - 1]$ such that $p + \delta = \text{Lunch}(c_i)$
4. **Room type mismatch**:
   $$\text{Type}(s_i) = \text{lab} \iff \text{Type}(r) = \text{lab}$$
5. **Room capacity inadequacy**: $\text{Capacity}(r) < \text{Strength}(c_i)$
6. **Teacher unavailability**: $\exists \delta \in [0, b_i - 1]$ such that $(d, p + \delta) \in \text{Unavailable}(t_i)$

---

## 4. Hard Constraints ($H_1 - H_9$)

A solution is **feasible** if and only if:
$$\sum_{k=1}^9 \text{Violations}(H_k) = 0$$

### $H_1$: Teacher Clash Prevention
No teacher can instruct multiple sessions during the same timeslot:
$$\forall x_i \neq x_j \text{ with } t_i = t_j: \quad \text{Slots}(x_i, v_i) \cap \text{Slots}(x_j, v_j) = \emptyset$$

### $H_2$: Class/Batch Clash Prevention
No student class can attend multiple sessions simultaneously:
$$\forall x_i \neq x_j \text{ with } c_i = c_j: \quad \text{Slots}(x_i, v_i) \cap \text{Slots}(x_j, v_j) = \emptyset$$

### $H_3$: Room Clash Prevention
No room can host more than one session concurrently:
$$\forall x_i \neq x_j \text{ with } r_i = r_j: \quad \text{Slots}(x_i, v_i) \cap \text{Slots}(x_j, v_j) = \emptyset$$

### $H_4$: Room Capacity Compliance
The room assigned to a session must accommodate the enrolled class size:
$$\forall x_i: \quad \text{Capacity}(r_i) \ge \text{Strength}(c_i)$$

### $H_5$: Room Type Compatibility
Laboratory courses require laboratory rooms with equipment; theory courses require lecture classrooms:
$$\forall x_i: \quad \text{Type}(r_i) = \begin{cases} \text{lab} & \text{if } \text{Type}(s_i) = \text{lab} \\ \text{classroom} & \text{otherwise} \end{cases}$$

### $H_6$: Faculty Availability Adherence
No session may be scheduled when the assigned faculty member is marked unavailable:
$$\forall x_i: \quad \text{Slots}(x_i, v_i) \cap \text{Unavailable}(t_i) = \emptyset$$

### $H_7$: Required Weekly Hours Fulfillment
Every subject $s$ for class $c$ must be scheduled for exactly its required weekly contact hours $W_{c, s}$:
$$\forall c \in C, \forall s \in \text{Subjects}(c): \quad \sum_{x_i \in X \mid c_i = c \land s_i = s} b_i = W_{c, s}$$

### $H_8$: Maximum Faculty Workload
A teacher's total weekly teaching commitment must not exceed their designated maximum load $L_{\max}(t)$:
$$\forall t \in T: \quad \sum_{x_i \in X \mid t_i = t} b_i \le L_{\max}(t)$$

### $H_9$: Class Lunch & Recess Protection
No session may overlap with the designated lunch break slot of class $c$:
$$\forall x_i: \quad \text{Lunch}(c_i) \notin \{p_i, p_i + 1, \dots, p_i + b_i - 1\}$$

---

## 5. Soft Constraints ($S_1 - S_5$) & Penalty Function

Soft constraints express educational and logistical preferences. Each violation incurs a designated penalty:

### $S_1$: Student Idle Gap Minimisation
Free periods between classes in a single day disrupt student focus.
$$\text{Cost}(S_1) = \sum_{c \in C} \sum_{d \in Days} \text{Gaps}(c, d)$$
where $\text{Gaps}(c, d)$ counts unassigned periods situated between the first and last lecture of class $c$ on day $d$ (excluding scheduled lunch and institutional breaks). Default weight: $w_1 = 2.0$.

### $S_2$: Subject Daily Dispersion
Students learn better when contact hours for a subject are distributed across multiple days rather than stacked.
$$\text{Cost}(S_2) = \sum_{c \in C} \sum_{s \in \text{Theory}} \sum_{d \in Days} \max(0, \text{Count}(c, s, d) - 1)$$
Default weight: $w_2 = 1.0$.

### $S_3$: Laboratory Continuity
When laboratories are scheduled as split single periods, consecutive slot placement is preferred:
$$\text{Cost}(S_3) = \sum \text{NonConsecutiveLabPairs}$$
Default weight: $w_3 = 3.0$ (when in split mode; in block mode, continuity is enforced structurally).

### $S_4$: Faculty Preferred Slot Compliance
Faculty preferences for avoiding specific periods (e.g., early morning 8 AM or late afternoon):
$$\text{Cost}(S_4) = \sum_{x_i \in X} \sum_{\delta = 0}^{b_i - 1} \mathbf{1}[(p_i + \delta) \in \text{AvoidPeriods}(t_i)]$$
Default weight: $w_4 = 1.5$.

### $S_5$: Daily Teaching Load Smoothing
Avoid scheduling heavy peaks where a class has $>5$ hours on one day and $<2$ on another.
$$\text{Cost}(S_5) = \sum_{c \in C} \sum_{d \in Days} \max(0, \text{Hours}(c, d) - \text{TargetDailyHours})$$
Default weight: $w_5 = 1.0$.

---

## 6. Global Objective Function

The global objective function combines hard violation penalties and weighted soft penalties:

$$\min_{V \in \mathcal{D}} \quad \mathcal{F}(V) = \lambda_{hard} \cdot \sum_{k=1}^9 \text{Count}(H_k) + \sum_{j=1}^5 w_j \cdot \text{Cost}(S_j)$$

where:
- $\lambda_{hard} = 1000$ (Heavy penalty ensuring any hard violation dominates all soft criteria)
- $w_j \in [1.0, 3.0]$ (User-tuneable weights via UI or configuration)
- A solution is admissible iff $\mathcal{F}(V) < \lambda_{hard}$.
