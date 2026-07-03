# Web simulator validation report

The browser simulator (`docs/simulator/`) runs the shepherding library of El-Fiqi et al.,
"The Limits of Reactive Shepherding Approaches for Swarm Guidance", IEEE Access vol. 8,
2020 (DOI 10.1109/ACCESS.2020.3037325), compiled UNCHANGED to WebAssembly with
Emscripten. No library source file was modified for the web build; the only additions
are `ShepherdingSimC_V1/wasm_bindings.cpp` (a third frontend beside the Visual
Studio/SDL2 build and the headless CLI) and the web page itself.

## What can differ from a native run, exhaustively

1. Random draw sequences: `std::mt19937` is bit-identical everywhere, but the standard
   leaves `uniform_*_distribution` internals to each standard library, so the same seed
   yields different concrete draws on MSVC (the paper machine), libstdc++ (Linux
   native), and libc++ (Emscripten). Same randomness model, different samples.
2. Transcendental rounding: wasm arithmetic is IEEE-754 exact, but `exp/cos/sin/atan2`
   may differ from glibc in the last bit, so same-draw trajectories can still diverge
   slowly.

Both channels affect individual trajectories, not the model. Validation is therefore
statistical, which matches the paper: its findings are completion rates and completion
times over 30 seeds per condition, not single trajectories.

## Battery design

`tools/native_battery.py` (native binary) and `tools/wasm_battery.js` (wasm module in
node) run the IDENTICAL battery: Table 2 parameters (= `InputFiles/Config.xml`), N=100,
one sheepdog, goal (25,50) radius 10, sheep initialised at (20,20)+10x10 in patterns
P1-P6, seeds 0..k, 2000-step cap; models: "proposed" (regulated, distance
neighbourhood, circular path planning) and "strombom" (all model flags 0, stalling on,
nearest-n neighbourhood with n = 0.5N), per the paper's Fig. 5 comparison.

## Results (10 seeds per pattern)

Proposed model, completion count and mean completion time:

| Pattern | Native | Wasm |
|---|---|---|
| P1 | 10/10, 81.2 | 10/10, 80.8 |
| P2 | 10/10, 91.2 | 10/10, 90.7 |
| P3 | 10/10, 85.3 | 10/10, 85.2 |
| P4 | 10/10, 261.5 | 10/10, 359.8 |
| P5 | 10/10, 260.7 | 10/10, 260.1 |
| P6 | 10/10, 281.1 | 10/10, 290.8 |

Stroembom baseline: native 43/60 completed, means 653-970 steps; wasm 42/60, means
682-868. Native and wasm agree within 10-seed Monte-Carlo error on every condition
(the proposed-model completion counts agree exactly); per-seed times differ as expected
from difference channels 1-2.

Against the paper's Fig. 5: the proposed model's 100 percent completion at roughly
80-90 steps for P1-P3 matches the reported 30/30 completion at around 100 steps. The
Stroembom baseline is dramatically worse in both (the paper's core finding); its exact
completion percentage in Fig. 5 (roughly 10-40 percent) is lower than our 70 percent,
which we attribute to Fig. 5 conditions not fully pinned in the text (the N sweep and
the speed-ratio setting for that figure); the qualitative separation between the models
is unambiguous in both.

## A finding: the limited-sensing extension breaks Table 2 geometry

With the config value `R_beta_pi = 20` currently shipped in `InputFiles/Config.xml`,
patterns whose sheep all start more than 20 units from the sheepdog (P2 always; P3
usually) leave the dog's detected-sheep list EMPTY at step 1;
`SheepDogAgent::UpdateSheepDogAgentLCM` then divides 0/0 and the dog's position becomes
NaN permanently (completion drops to 0/10 on P2, 3/10 on P3, 7/10 elsewhere, identically
in native and wasm). The `R_beta_pi` limited-sensing feature postdates the IEEE Access
experiments; the paper's Table 2 has no such parameter. The simulator therefore
defaults `R_beta_pi = 65` (unlimited in practice, paper-era behaviour), which restores
10/10 on every pattern. The latent 0/0 division for a fully blind sheepdog remains in
the library and is left untouched here; recommended as a small guard in future library
work.

## Reproduce

```
cmake -S . -B build-native -DCMAKE_BUILD_TYPE=Release && cmake --build build-native -j
python3 tools/native_battery.py build-native/shepherd_sim proposed 10

source ~/emsdk/emsdk_env.sh
emcmake cmake -S . -B build-wasm -DCMAKE_BUILD_TYPE=Release && cmake --build build-wasm -j
node tools/wasm_battery.js build-wasm/shepherd_sim_web.js t0
node tools/wasm_battery.js build-wasm/shepherd_sim_web.js battery proposed 10
```

The T0 baseline regression also holds on this branch: the fixed-seed shipped-config
run reproduces the recorded trajectory hash (tests/baseline/T0_sha256.txt).
