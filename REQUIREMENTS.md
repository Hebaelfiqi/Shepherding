# REQUIREMENTS: Extend the C++ Shepherding Library to implement "Adversarial Patrolling Using a Shepherding Approach"

Target repository: https://github.com/Hebaelfiqi/Shepherding (the working fork).
Canonical upstream: https://github.com/husseinaabbass/Shepherding.
Paper: Zhou, El-Fiqi, Hussein, "Adversarial Patrolling Using a Shepherding Approach", IEEE SMC 2024.
Author of both the library and the paper is available to review decisions.

Verified repository layout (as of clone):
- `ClassLibraryProjects.sln` (Visual Studio solution, two projects).
- `ShepherdingLibC/` : the physics library. Plain portable C++ (no SDL, no COM). The only
  Windows dependencies are `stdafx.h` (pulls in `windows.h`), `stdafx.cpp`, `dllmain.cpp`, and
  `Properties/AssemblyInfo.cpp`. Core files: `Agents`, `Behaviors`, `Environment`, `Flock`,
  `Modules`, `SheepAgent`, `SheepDogAgent`, `Terrain`, `Time`, `Traits`, `Utilities`,
  `Vector2.h`, `ShepherdingLibC.cpp`.
- `ShepherdingSimC_V1/` : the simulation app. `ShepherdingSimC_V1.cpp` holds `main`, parses the
  XML config with MSXML6 via COM (`#import <msxml6.dll>`, `CoInitialize`, `IXMLDOM...`), and
  includes SDL2. `Visualization.cpp` is SDL2-only. `Sim.cpp`, `SupportingCalc.cpp`, `CLI.cpp`
  are portable core logic (no SDL, no COM; `CLI.cpp`/`Sim.cpp` reference `pch.h` only).
- `InputFiles/Config.xml` : the configuration. Ships as the "our model" regulated variant
  (`ForceRegulated=1`, `DrivingPositionEq=1`, `CollectingPositionEq=1`, `fNequation=1`,
  `SheepNeignborhoodSelection=1`). Field width 50. Goal at (25, 50).
- `executables/` : prebuilt Windows binaries and SDL2 DLLs (Windows only, ignore for Linux).

This is a build-and-test task for Claude Code. Read this whole file first, then work through
the milestones in order. Do not start coding until Milestone M0 (build the baseline and confirm
the base model) is complete.

---

## 0. Ground rules

1. **Extend, do not rewrite.** Reuse the existing agents, forces, neighbourhood logic,
   regulated-force machinery, initialisation patterns, and the XML config loader. Add only the
   missing pieces listed in Section 3. Do not re-derive or replace the base Strombom physics.
2. **Same library, same environment.** Keep the existing build system, file layout, and
   dependencies. Add new source files next to the existing ones; do not restructure the project.
3. **Regression-safe.** Every new feature goes behind a config flag (see Section 4). With the
   adversarial flags off, the library must behave exactly as before (verified in M0/T0).
4. **The base model is already the regulated variant.** `Config.xml` ships with
   `ForceRegulated=1`. This is correct and load-bearing: the paper's bounded standoff depends on
   the exponentially decaying repulsion. Do not switch it off. Confirm it is active before
   changing anything else.
5. **Honesty over matching.** The paper does not publish the exact metric-combination formula in
   the look-ahead, nor the exact 27 initial conditions. Implement the natural choices in this
   spec, keep them parameterised, and if a metric cannot be matched, document which assumption is
   responsible rather than tuning until a single number lines up. See Section 5 and Section 6.3.
6. **No em dashes in any prose or comments you write.**

---

## 1. Environment and build (Milestone M0, do this first)

Pick ONE of two build environments. Both are supported; choose per Section 1a/1b.

### 1a. Windows + Visual Studio (least effort, most faithful)
Open `ClassLibraryProjects.sln`, restore SDL2 (already vendored under `executables/`), build
both projects, and run `ShepherdingSimC_V1.exe ../InputFiles/Config.xml`. Nothing needs porting.
This is the environment the library was written for. If you have Windows access, prefer it.

### 1b. Linux headless (this Ubuntu machine): a real but mechanical port is required (Milestone M0.5)
The library core is portable, but the simulation app has two Windows-only dependencies that must
be removed for a Linux build. Do the following as **Milestone M0.5** before any adversarial work,
behind a clean, reviewable commit:

1. **Neutralise the precompiled-header Windows includes.** Guard the Windows include in
   `ShepherdingLibC/stdafx.h` and `ShepherdingSimC_V1/pch.h` under `#ifdef _WIN32` so the core
   compiles with g++/clang. Do not otherwise change them.
2. **Replace the MSXML6 COM config parser with a portable one.** In `ShepherdingSimC_V1.cpp`, the
   functions that load `Config.xml` and `VisualizationOptions.xml` use `#import <msxml6.dll>`,
   `CoInitialize`, and `IXMLDOM*`. Vendor a small portable XML library (tinyxml2, single .cpp/.h,
   MIT) under `third_party/tinyxml2/` and reimplement config loading against it. Keep the exact
   same config keys and the exact same global variables the loader fills. This is about 40 lines
   of MSXML node-walking to port; keep behaviour identical.
3. **Provide a headless entry point.** Add `ShepherdingSimC_V1/main_headless.cpp` that loads the
   config (via the portable loader), runs the simulation loop (reuse `Sim.cpp` /
   `SupportingCalc.cpp` unchanged), and writes CSV output, with NO SDL and NO COM. Exclude
   `Visualization.cpp` and the original `ShepherdingSimC_V1.cpp` from the headless target.
4. **Add CMake alongside the .sln (do not delete the VS files).** A starter `CMakeLists.txt` is
   provided in this bundle. It builds `libshepherding` (static, from the core `.cpp` files, minus
   `dllmain.cpp` and `Properties/AssemblyInfo.cpp`) and a headless `shepherd_sim` executable.
   Fill in the two TODO file lists once the portable loader and headless main exist.
5. Install and document the toolchain (`build-essential`, `cmake`; SDL2 is not needed for
   headless). Build, then run the shipped `Config.xml` headless to confirm the baseline works.
   Capture the per-step CSV as the regression baseline for T0.

Files you will read and, where noted, edit (verified names):
`ShepherdingLibC/{Behaviors,SheepAgent,SheepDogAgent,Flock,Utilities,Environment,Agents}.cpp`,
`InputFiles/Config.xml`, `ShepherdingSimC_V1/{Sim,SupportingCalc,CLI,ShepherdingSimC_V1}.cpp`.

---

## 2. Confirm the base model before changing it (still M0)

Read the source and write a one-page `docs/base_model_notes.md` stating, with file and function
references, exactly how the current code:

- sums the sheep force terms, normalises the sheep force to a unit vector, and steps the sheep at
  speed 1;
- computes the sheepdog behaviours (Driving, Collecting), and how it steps the dog at speed
  `S_t_beta_j` (confirm whether the dog force is renormalised before stepping; this matters for
  the behaviour blend in Section 3.5);
- applies regulated repulsion (`ForceRegulated=1`): the attacker-attacker term
  `exp(-decay * d / ra) / sqrt(count)` and the attacker-defender term
  `S_t_beta_j * exp(-decay * d / R3)`;
- computes `fN = ra * sqrt(2N)`;
- builds the distance-based neighbourhood (`SheepNeignborhoodSelection=1`, radius `Rs_pi_pi`);
- initialises the flock, including Pattern P6 ("corners only": 5x5 grid, four corner cells).

Do not proceed to Section 3 until this document is written. It is the contract for what you are
allowed to reuse.

---

## 3. Functional requirements: the missing pieces

Everything here is an addition. Cross-check each equation against Appendix A.

### 3.1 Area of Interest (AOI)
Add an AOI point at the centre of the top third of the field: `(field_w/2, field_h * 5/6)`, i.e.
`(25, 41.667)` for a 50x50 field. Load its coordinates from config (Section 4), defaulting to the
computed centre.

### 3.2 Sheep force: add the AOI attraction term and adversarial weights
In the sheep force sum, add one new term: `W_pi_I * unit(p_i -> AOI)`. Do not touch the existing
terms. Set the adversarial weights (from config, see Section 4):
`W_pi_upsilon=0.5, W_pi_Lambda=1.0, W_pi_beta=2.0, W_pi_pi=2.0, W_e_pi=0.0, W_pi_I=0.25`.
Precedence to preserve: `W_pi_beta >= W_pi_pi > W_pi_Lambda > W_pi_upsilon > W_pi_I > W_e_pi`.
After summing, normalise and step at sheep speed 1, exactly as the base code already does.

### 3.3 Sheepdog: add the Intercepting behaviour
New behaviour returning a unit force. The threat is the attacker closest to the AOI. The target is
a point between the AOI and that attacker, at a fixed stand-off `intercept_dist` from the AOI:
`T = AOI + unit(AOI -> threat) * intercept_dist; F_intercept = unit(dog -> T)`.

### 3.4 Sheepdog: add the Patrolling behaviour (non-deterministic)
New behaviour returning a unit force. Maintain a patrol phase `phi` on the dog. Each step:
`phi += patrol_step + Uniform(-patrol_noise, +patrol_noise)`,
`T = AOI + patrol_radius * (cos phi, sin phi)`, `F_patrol = unit(dog -> T)`.

### 3.5 Behaviour combinations (Table II)
Add the ten combinations as weight tuples over (Driving, Collecting, Intercepting, Patrolling):
BC1 (1,0,0,0), BC2 (0,1,0,0), BC3 (0,0,1,0), BC4 (0,0,0,1), BC5 (.5,.5,0,0), BC6 (.5,0,.5,0),
BC7 (.5,0,0,.5), BC8 (0,.5,.5,0), BC9 (0,.5,0,.5), BC10 (0,0,.5,.5).
The blended dog force is `sum_i w_i * F_i` over the four behaviour unit vectors. Step the dog
using the same convention the base code uses for the dog (from your M0 notes: renormalise-or-not,
then multiply by `S_t_beta_j`). Keep Driving and Collecting exactly as the library computes them.
The driving behaviour must herd the swarm away from the AOI (the dog positions between the AOI and
the swarm). Record how you set the driving goal for this in `docs/decisions.md`.

### 3.6 Look-ahead greedy controller
Add a controller that runs once per real timestep. For each of the 10 BCs:
1. compute the blended dog force for that BC and take a **virtual** dog step;
2. let all sheep take one **virtual** reaction step against that virtual dog;
3. evaluate three metrics on the resulting virtual state (Appendix A.6):
   M1 = distance GCM to AOI (want large), M2 = circular std of attacker-to-AOI angles (want small),
   M3 = angle between (AOI to GCM) and (AOI to dog) (want small).
Min-max scale each metric across the 10 candidates to [0,1], compute
`desirability = w_M1*scale(M1) + w_M2*(1-scale(M2)) + w_M3*(1-scale(M3))` with default weights
`(1,1,1)`, pick the argmax BC, and execute that BC for the real step. The virtual steps must not
mutate real state and must not consume the real random stream (use a separate RNG substream so
patrol jitter does not couple across candidates).

### 3.7 Experiment harness
Add an experiment mode that runs the 27 conditions x 200 timesteps. The 27 conditions are 3
starting positions x 3 bounding-box widths x 3 bounding-box heights. Attackers initialise far from
the AOI (lower field) using Pattern P6. The dog initialises uniformly in a 5x5 square next to the
AOI. Because the exact 27 values are not published, put your reconstructed values in config and
document them in `docs/decisions.md`. Seed each run deterministically (`base_seed + run_index`).

### 3.8 Metrics and reporting
Per run and per step, log the Table III metrics and the mission-success indicators (Appendix A,
Appendix B). At the end, write:
- `results/results.csv` (or json): per-condition and pooled mean/std of each Table III metric, the
  four headline percentages, and behaviour usage;
- `results/REPORT.md`: the Table III comparison against the paper, the percentages, behaviour
  usage, and an honest discussion (Section 6.3);
- figures: GCM-to-AOI distance over time (Fig 5 analogue), the AOI-to-GCM vs AOI-to-dog angle over
  time (Fig 6 analogue), and behaviour usage. Generate these either from the SDL2 build or by
  writing per-step CSV and plotting with a small script (`tools/plot.py`); either is acceptable.

---

## 4. Config additions (backward compatible)

Add these keys to `Config.xml` (or the config struct/loader). All optional, all defaulting so that
when `AdversarialMode=0` the library reproduces its current behaviour bit for bit.

```
AdversarialMode        0/1     (master switch for everything below; default 0)
AOI_x, AOI_y           float   (default: centre of top third)
W_pi_I                 0.25    (AOI attraction weight)
AdversarialWeights     0/1     (if 1, apply the Section 3.2 weights)
Intercept_dist         float   (intercepting stand-off from AOI)
Patrol_radius          float   (patrol circle radius)
Patrol_step            float   (nominal phase advance per step)
Patrol_noise           float   (uniform jitter half-width on phase)
LookAheadController    0/1     (enable the greedy selector)
MetricWeight_M1/M2/M3  1,1,1   (desirability weights)
Experiment_conditions  27
Experiment_steps       200
Experiment_base_seed   int
```

Do not change the meaning of any existing key. Keep `ForceRegulated=1`.

---

## 5. Known unknowns (do not guess silently)

Two parts of the method are not fully specified in the paper. Implement the stated defaults, keep
them swappable, and log the choice:

1. **The metric-combination formula** in Section 3.6. Default to the equal-weight scaled sum.
   Because it is the single most likely cause of any residual mismatch, expose `MetricWeight_M1/2/3`
   and keep the combining function in one small, clearly commented place so it can be swapped.
2. **The 27 initial conditions** in Section 3.7. Default to the reconstructed grid, in config,
   documented. If you later obtain the originals, only config changes.

Record both in `docs/decisions.md` with the exact values used.

---

## 6. Test plan

Add a test target (reuse whatever test setup exists, or add a minimal assert-based harness under
`tests/`). All tests must be runnable with one command and must print pass/fail.

### 6.1 Build and regression
- **T0 baseline**: the library builds and a shipped example config runs. With `AdversarialMode=0`,
  a fixed-seed run of the original shepherding scenario produces the same trajectory hash as before
  your changes (capture a reference hash in M0, assert equality after each milestone).

### 6.2 Unit tests (each new equation in isolation, with numeric checks)
- **U1 AOI attraction**: for a sheep at a known offset from the AOI, the added term equals
  `unit(sheep -> AOI)` within 1e-9.
- **U2 Regulated repulsion active**: the attacker-defender repulsion magnitude decreases
  monotonically with distance and matches `S_t_beta_j * exp(-decay * d / R3)` within 1e-9.
- **U3 Intercepting**: for a chosen threat attacker, the target lies on the segment AOI to threat
  at distance `intercept_dist` from the AOI, and the force points from the dog toward it.
- **U4 Patrolling**: the target lies on the circle of radius `patrol_radius` about the AOI, and the
  phase advances by `patrol_step` within the noise band across successive calls.
- **U5 BC table**: the ten weight tuples equal Table II exactly.
- **U6 Metrics**: on a hand-built state (for example, attackers colinear below the AOI), M1, M2, M3
  equal their analytic values within 1e-9.
- **U7 Selection**: given synthetic (M1,M2,M3) arrays for ten candidates, the scaler and argmax
  return the analytically correct BC.
- **U8 Determinism**: identical seed gives identical trajectories; different seeds differ; virtual
  look-ahead steps do not perturb the real RNG stream.

### 6.3 Integration and reproduction
- **I1**: a full 27 x 200 experiment completes and writes the results and report.
- **I2 reproduction tolerances** (robust regime; these are ranges, not exact targets, for the
  reasons in Section 5):
  - mean GCM-to-AOI distance in [10, 18]      (paper 13.53)
  - sigma(R), std of attacker-to-AOI distances, in [1.0, 3.5]   (paper 1.66)
  - swarm fully clustered >= 80%              (paper 89%)
  - defender between swarm and AOI >= 55%     (paper 64%)
  - mean defender-vs-swarm angle (theta_beta) <= 0.6   (paper 0.24)
  - Fig 5 shape: the mean GCM distance falls from above 30 to a bounded band and stays bounded
    (final-quarter mean < 25, i.e. no runaway).
  - Fig 6: M3 < pi/2 for at least 90% of steps (dog stays on the swarm side of the AOI).
  - Driving is among the top two behaviours by usage.
- **I3 honesty check**: if any Table III metric or headline percentage cannot be met at the same
  time as the others, the report must say so, state which regime matches which metric, name the
  responsible assumption (Section 5), and must not tune one number at the expense of silently
  breaking another. Overclaiming is a test failure.

---

## 7. Acceptance criteria

1. Baseline regression (T0) passes after every milestone.
2. All unit tests U1 to U8 pass.
3. I1 completes; I2 tolerances are met; I3 report is present and honest.
4. Adversarial features are entirely behind config flags; default config reproduces the original
   library.
5. `docs/base_model_notes.md` and `docs/decisions.md` exist and are accurate.

---

## 8. Milestones (work in this order, commit after each)

- **M0** Detect the build system, choose Windows or Linux (Section 1), and (Windows) build the
  baseline, or (Linux) confirm what needs porting. Capture a regression baseline, write
  `docs/base_model_notes.md`. (Section 1, 2)
- **M0.5** (Linux only) Port to a headless CMake build: guard the Windows PCH includes, replace
  the MSXML6 config loader with tinyxml2, add `main_headless.cpp`, wire up `CMakeLists.txt`.
  Build and run the shipped `Config.xml` headless. Baseline CSV must match the Windows run for the
  same seed (or, if no Windows run is available, be recorded as the Linux reference). (Section 1b)
- **M1** AOI + sheep AOI-attraction + adversarial weights, behind flags. Sanity: with no dog,
  sheep drift toward the AOI. Tests U1, T0.
- **M2** Intercepting + Patrolling behaviours. Tests U3, U4.
- **M3** Behaviour-combination table and blended dog step. Test U5.
- **M4** Metrics + look-ahead controller. Tests U6, U7, U8.
- **M5** Experiment harness (27 x 200) + logging. Test I1.
- **M6** Reproduction run; tune only the documented knobs (Section 5, and intercept/patrol/guard
  radii) to reach the I2 regime. Test I2.
- **M7** Report + figures + honest discussion. Test I3.

---

## Appendix A: equations (authoritative, use these if the PDF is unavailable)

Notation: `p_i` attacker i position, `d` dog position, `A` AOI, `unit(x->y)=(y-x)/||y-x||`,
`N=10`, `r_a=Ra_pi_pi`, `Rs=Rs_pi_pi`, `mu=ModulationDecayFactor`, `S_b=S_t_beta_j`,
`R3` and `R_pi_beta` as in config.

A.1 Sheep force for attacker i (add only the last term; keep the rest as the library computes):
```
F_i =  W_v * h_prev_i
     + W_L * unit(p_i -> LCM_i)                                  (local centre of mass, radius Rs)
     + W_b * [ unit(d -> p_i) * S_b * exp(-mu * ||p_i-d|| / R3) ]  if ||p_i-d|| < R_pi_beta   (regulated)
     + W_p * sum_j [ unit(p_j -> p_i) * exp(-mu * ||p_i-p_j|| / r_a) / sqrt(n_close) ]  over j within r_a  (regulated)
     + W_e * jitter                                              (W_e = 0 in adversarial)
     + W_I * unit(p_i -> A)                                      (NEW)
p_i <- p_i + unit(F_i) * 1        (sheep speed 1, library convention)
```

A.2 Driving and Collecting: unchanged from the library. Driving must herd the swarm away from the
AOI (dog between AOI and swarm). Record the exact goal/attractor you pass to the existing driving
routine in `docs/decisions.md`.

A.3 Intercepting (new):
```
threat = argmin_i ||p_i - A||
T_int  = A + unit(A -> threat) * intercept_dist
F_int  = unit(d -> T_int)
```

A.4 Patrolling (new, non-deterministic):
```
phi   <- phi + patrol_step + Uniform(-patrol_noise, +patrol_noise)
T_pat  = A + patrol_radius * (cos phi, sin phi)
F_pat  = unit(d -> T_pat)
```

A.5 Behaviour blend and dog step, for BC weights (w1,w2,w3,w4):
```
F_dog = w1*F_drive + w2*F_collect + w3*F_int + w4*F_pat
d <- d + step_dog(F_dog) * S_b        (step_dog = the library's own convention from M0 notes)
```

A.6 Metrics on a state:
```
GCM = mean_i p_i
M1  = ||GCM - A||
theta_i = atan2(A.y - p_i.y, A.x - p_i.x)
R   = || (1/N) * sum_i (cos theta_i, sin theta_i) ||
M2  = sqrt( max(0, -2 * ln R) )                       (circular standard deviation)
M3  = acos( clamp( ((GCM-A) . (d-A)) / (||GCM-A|| * ||d-A||), -1, 1) )   in [0, pi]
```

A.7 Look-ahead selection:
```
for k in 1..10:
    d_v      = d + step_dog(F_dog(BC_k)) * S_b            (virtual, does not mutate real state)
    p_v      = one virtual sheep reaction step against d_v
    (M1_k, M2_k, M3_k) = metrics(p_v, d_v)
scale(x)_k = (x_k - min_k x) / (max_k x - min_k x), or 0 if the range is 0
desir_k    = wM1*scale(M1)_k + wM2*(1 - scale(M2)_k) + wM3*(1 - scale(M3)_k)   (default wM=1)
k*         = argmax_k desir_k ; execute BC_k* as the real step
```

A.8 Clustering:
```
fN = r_a * sqrt(2N)
clustered  <=> for all i, ||p_i - GCM|| <= fN
Omega       = { i : ||p_i - GCM|| > fN }        (unclustered set)
```

---

## Appendix B: paper target values (for the report comparison)

Table III, mean (std), pooled over runs and timesteps:
```
mu(R_lambda)  GCM-to-AOI distance          13.53 (8.09)
sigma(theta)  attacker-to-AOI angle std     0.41 (0.46)
theta_beta    defender-vs-swarm angle       0.24 (1.48)
sigma(R)      attacker-to-AOI distance std  1.66 (2.32)
mu(Omega)     unclustered-to-AOI distance   0.03 (0.23)
theta_Omega   unclustered-vs-swarm angle    3.78e-5 (1.26e-4)
```
Headline percentages and qualitative claims:
```
an attacker within 5 units of the AOI       20%
all attackers beyond 20 units               25%
defender between swarm and AOI              64%
swarm fully clustered                       89%
Driving is the dominant behaviour.
Figure 5: GCM distance drops from far away to a bounded oscillating standoff.
Figure 6: the defender stays on the swarm side of the AOI (angle below pi/2).
```

A validated Python reference implementation of this exact method (separate from your C++ code)
reaches, in its primary regime: mean distance 13.41, sigma(R) 1.45, clustered 86.6%,
defender-between 97.6%, theta_beta 0.19, with Figures 5 and 6 reproduced. Use these as a sanity
band for the C++ port. Note that no single parameter set in that reference reproduced every Table
III row plus every percentage at once; expect the same two-regime behaviour and report it honestly.

---

## Quick start for Claude Code

Paste to begin:
"Read REQUIREMENTS.md in full. Do Milestone M0 only: detect the build system, build the existing
library unchanged, run a shipped example, capture a regression baseline, and write
docs/base_model_notes.md. Stop and show me your notes before touching any equations."
