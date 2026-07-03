# CLAUDE.md - web-simulator branch

This branch is the browser demonstrator for the ORIGINAL shepherding library: the model
of El-Fiqi et al., "The Limits of Reactive Shepherding Approaches for Swarm Guidance",
IEEE Access vol. 8, 2020, DOI 10.1109/ACCESS.2020.3037325. The library is compiled
UNCHANGED to WebAssembly; parameters are set interactively on the page instead of via
Config.xml, and the Regulated-vs-Strombom comparison of the paper's Fig. 5 is a live
toggle.

## Branch map (one repository, three lines)
- `master`: the original library. Physics is frozen reference material.
- `adversarial-patrolling`: the IEEE SMC 2024 adversarial extension line.
- `web-simulator` (this branch): master + the M0.5 headless port + the wasm frontend
  and simulator page. Merges FROM master only; intended to merge INTO master by PR
  when the owner approves.

## Hard rules
- Do not modify any file under `ShepherdingLibC/` or the portable sim core
  (`Sim.cpp`, `SupportingCalc.cpp`, `CLI.cpp`). The web build is a frontend:
  additions live in `ShepherdingSimC_V1/wasm_bindings.cpp` and `docs/simulator/`.
- The T0 regression must hold: a fixed-seed run of the shipped `InputFiles/Config.xml`
  reproduces the hash in `tests/baseline/T0_sha256.txt` (CI enforces this).
- The Visual Studio solution and SDL2 path stay untouched and buildable on Windows.
- No em dashes in prose or comments. Seed every run; keep results reproducible.
- Do not add Co-Authored-By or other AI attribution trailers to commits in this
  repository; attribution policy is decided by the repository owner.

## Layout (additions on this branch)
- `ShepherdingSimC_V1/wasm_bindings.cpp`: C-ABI exports (sim_create/step/positions...);
  frees per-step behaviour lists and per-run agents so browser memory stays flat.
- `docs/simulator/`: the interactive page + compiled `shepherd_sim_web.{js,wasm}`.
  After rebuilding wasm, copy the two artefacts here (CI warns when stale).
- `tools/native_battery.py`, `tools/wasm_battery.js`: identical validation batteries
  for native and wasm builds.
- `docs/web_simulator_validation.md`: the validation report (read before changing
  battery assumptions).
- `.github/workflows/web-simulator-ci.yml`: native build + T0 + both battery smokes.

## Commands
```
cmake -S . -B build-native -DCMAKE_BUILD_TYPE=Release && cmake --build build-native -j
python3 tools/native_battery.py build-native/shepherd_sim proposed 10

source ~/emsdk/emsdk_env.sh
emcmake cmake -S . -B build-wasm -DCMAKE_BUILD_TYPE=Release && cmake --build build-wasm -j
node tools/wasm_battery.js build-wasm/shepherd_sim_web.js t0
python3 -m http.server 8080 --directory docs   # open /simulator/
```

## Known facts that guide changes here
- Validation status: proposed model reproduces the paper (10/10 completion on all
  patterns, ~80-90 step means on P1-P3 vs the paper's ~100). The Strombom baseline's
  published completion (~10-40%) is bracketed by the two stalling-distance
  interpretations (3*Ra=1.2 gives 72%, the shipped config's 6 gives 2%); the exact
  paper value is pending the owner's original run configuration.
- `R_beta_pi` (dog sensing range) postdates the paper; the shipped config's 20 makes
  the dog start blind in Table 2 geometry, which hits a latent 0/0 in
  `UpdateSheepDogAgentLCM` and produces a permanent NaN position. The simulator and
  batteries default to 65 (paper-era, effectively unlimited). Do not "fix" the 0/0 in
  library code on this branch; it is flagged for the owner's future library work.
- Same seed does not bit-match across MSVC / libstdc++ / libc++ (uniform_*_distribution
  internals differ); validation is statistical, matching how the paper reports.

## Private material (never commit)
`Student Work/`, `local_review/` are gitignored and must stay untracked.
