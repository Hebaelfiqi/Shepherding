# CLAUDE.md

Standing context for extending the C++ Shepherding Library to implement the adversarial
patrolling paper. Read `REQUIREMENTS.md` for the full task; this file is the quick reference.

Repo: https://github.com/Hebaelfiqi/Shepherding  (upstream: husseinaabbass/Shepherding)
Paper: Zhou, El-Fiqi, Hussein, "Adversarial Patrolling Using a Shepherding Approach", IEEE SMC 2024.

## What this repo is
- `ShepherdingLibC/` : the physics library (portable C++). This is the base shepherding model.
- `ShepherdingSimC_V1/` : the simulation app. Holds `main`, the XML config loader, and SDL2
  visualisation.
- `InputFiles/Config.xml` : configuration. Ships as the regulated "our model" variant.
- `ClassLibraryProjects.sln` : Visual Studio solution (Windows).
- `executables/` : prebuilt Windows binaries and SDL2 DLLs (ignore on Linux).

## Two ways to build
- **Windows + Visual Studio**: open `ClassLibraryProjects.sln`, build, run
  `ShepherdingSimC_V1.exe ../InputFiles/Config.xml`. No porting. Most faithful.
- **Linux headless**: requires a one-time port (see REQUIREMENTS.md Milestone M0.5): guard the
  Windows PCH includes under `#ifdef _WIN32`, replace the MSXML6 COM config loader with tinyxml2,
  add `main_headless.cpp`, build via the provided `CMakeLists.txt`. SDL2 is not needed headless.

## Do not touch (base physics)
- Do not change the sheep/dog force computation, the regulated-force machinery, the neighbourhood
  logic, `fN = ra*sqrt(2N)`, or the initialisation patterns. Reuse them.
- Keep `ForceRegulated=1`. The paper's bounded standoff depends on the exponentially decaying
  repulsion. Switching it off makes the swarm run away to infinity (confirmed in a Python
  reference reproduction).
- Every new feature goes behind a config flag (`AdversarialMode`, etc.). With the flags off, the
  library must reproduce its current behaviour bit for bit.

## What to add (only these)
1. AOI point + `W_pi_I * unit(sheep -> AOI)` attraction term on the sheep force.
2. Two new sheepdog behaviours: Intercepting and Patrolling.
3. The ten behaviour combinations (Table II) and the blended dog step.
4. A one-step look-ahead controller: for each of the 10 combinations, virtually step dog + sheep,
   score with three metrics (M1 distance, M2 angular std, M3 defender-side angle), min-max scale,
   pick the argmax. Equations are in REQUIREMENTS.md Appendix A.
5. A 27-condition x 200-step experiment harness that logs Table III metrics and the four headline
   percentages.

## Two genuinely unpublished pieces (do not guess silently)
- The exact metric-combination formula in the look-ahead. Default to the equal-weight scaled sum;
  keep it in one small function with config weights `MetricWeight_M1/M2/M3`.
- The exact 27 initial conditions. Default to a documented reconstruction in config.
Record both in `docs/decisions.md`.

## Honesty rule
No single parameter set reproduced every Table III row plus every headline percentage in the
Python reference; the numbers split across a "standoff" regime and an "engagement" regime. Expect
the same and report it plainly. Overclaiming a full simultaneous match is a test failure
(REQUIREMENTS.md I3). Sanity band from the reference (primary regime): mean distance 13.4,
sigma(R) 1.45, clustered 87%, defender-between 98%, theta_beta 0.19; paper targets are 13.53,
1.66, 89%, 64%, 0.24.

## Commands (Linux headless, after M0.5)
```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/shepherd_sim InputFiles/Config.xml            # single run
./build/shepherd_sim --experiment InputFiles/Config.xml   # 27x200 experiment (add this flag in M5)
ctest --test-dir build                                # unit + regression tests
```

## Conventions
- No em dashes in prose or comments.
- Seed every run (`base_seed + run_index`); keep results reproducible.
- Commit after each milestone (M0, M0.5, M1..M7).
