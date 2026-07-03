# CLAUDE.md - adversarial-patrolling branch

This branch is the completed implementation of Zhou, El-Fiqi, Hussein, "Adversarial
Patrolling Using a Shepherding Approach", Proc. IEEE SMC 2024, pp. 839-844,
DOI 10.1109/SMC54092.2024.10832074, built as an extension of the original shepherding
library (see `master`). A defender sheepdog guards an Area of Interest against an
attacker swarm using ten behaviour combinations selected by a one-step look-ahead
controller.

## Branch map (one repository, three lines)
- `master`: the original library (IEEE Access 2020 model). Frozen reference.
- `adversarial-patrolling` (this branch): master + headless Linux port + the
  adversarial extension, results, and replay tooling.
- `web-simulator`: browser demonstrator of the ORIGINAL model.

Merges flow master -> this branch only.

## Hard rules (still binding for any further work here)
- Base physics is untouched and must stay untouched: with `AdversarialMode=0` the
  library reproduces master bit for bit. The `t0_regression` ctest enforces this;
  it must pass after every change.
- Every adversarial feature stays behind the config flags (`AdversarialMode`,
  `AdversarialWeights`, `LookAheadController`, ...). Keep `ForceRegulated=1`: the
  bounded standoff depends on the exponentially decaying repulsion.
- Honesty rule for any reporting: the metrics split across a "standoff" and an
  "engagement" regime; no single parameter set matches every published number at
  once. State plainly which regime a result belongs to. See `results/REPORT.md`.
- No em dashes in prose or comments. Seed every run (`base_seed + run_index`).
- Do not add Co-Authored-By or other AI attribution trailers to commits in this
  repository; attribution policy is decided by the repository owner.

## What this branch adds over master
- `ShepherdingLibC/AdversarialBehaviors.{h,cpp}`: AOIAttraction (sheep), Intercepting,
  Patrolling (defender). Guarded additions in Modules/SheepAgent/Behaviors.
- `ShepherdingSimC_V1/AdversarialController.{h,cpp}`: Table II behaviour combinations,
  metrics M1/M2/M3, min-max scaled desirability (weights `MetricWeight_M1/M2/M3`),
  virtual look-ahead with full state snapshot/restore and dedicated RNG substreams.
- `ShepherdingSimC_V1/Experiment.{h,cpp}`: 27-condition x 200-step harness
  (`--experiment`), Table III logging, per-run position dumps for replay.
- `InputFiles/Config_Adversarial.xml`: tuned configuration (all I2 tolerances pass).
- `results/`: results.csv, per-step logs, figures, and REPORT.md (the honest
  comparison against the paper).
- `docs/decisions.md`: every reconstruction choice for the paper's unpublished pieces.
- `tools/make_replay.py` + `docs/replay/`: interactive trajectory replay (hosted via
  GitHub Pages from this branch's /docs).
- `tests/unit_tests.cpp` (U1-U8) and the T0 regression, wired into ctest and CI.

## Commands
```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
ctest --test-dir build                                          # U1-U8 + T0
./build/shepherd_sim InputFiles/Config_Adversarial.xml          # single adversarial run
./build/shepherd_sim --experiment InputFiles/Config_Adversarial.xml   # 27x200
python3 tools/plot.py results                                   # figures
python3 tools/make_replay.py <positions csv> -o replay.html     # trajectory replay
```

## Private material (never commit)
`Student Work/` and `local_review/` are gitignored and must stay untracked. The
student-submission crosscheck lives ONLY in `local_review/` on the owner's machine;
do not reintroduce it into tracked files or commit messages.
