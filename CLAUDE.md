# CLAUDE.md - master (the original shepherding library)

This branch is the original C++ Shepherding Library: the reactive shepherding model of
El-Fiqi et al., "The Limits of Reactive Shepherding Approaches for Swarm Guidance",
IEEE Access vol. 8, pp. 214658-214671, 2020, DOI 10.1109/ACCESS.2020.3037325.
Upstream: https://github.com/husseinaabbass/Shepherding.

Master is the reference line. Its physics is frozen: sheep/dog force computation, the
regulated-force machinery, neighbourhood logic, fN, and the initialisation patterns
change only by an explicit decision of the repository owner.

## What this branch contains
- `ShepherdingLibC/` : the physics library (portable C++). Sheep and sheepdog agents,
  behaviours (driving, collecting, cohesion, regulated repulsion), patterns P1-P6.
- `ShepherdingSimC_V1/` : the simulation app. `main`, the MSXML6 config loader, and the
  SDL2 visualisation (Windows).
- `InputFiles/Config.xml` : configuration; ships as the regulated "our model" variant.
  It largely mirrors Table 2 of the paper. Note two post-paper additions in the config:
  `R_beta_pi` (sheepdog limited sensing) and the shipped `StallingDistance=6`.
- `ClassLibraryProjects.sln` : Visual Studio solution; the primary build. Run
  `ShepherdingSimC_V1.exe ../InputFiles/Config.xml`.
- `docs/base_model_notes.md` : a precise description of the physics with file and
  function references (force summation and normalisation, step conventions, regulated
  repulsion, fN, neighbourhood, Pattern P6).
- `REQUIREMENTS.md`, `SETUP.md`, `CMakeLists.txt` : task documents for the extension
  lines below; the starter CMakeLists becomes buildable once the headless port lands
  (see web-simulator).

## Branch map (one repository, three lines)
- `master` (this branch): the original library.
- `adversarial-patrolling`: the IEEE SMC 2024 adversarial patrolling extension
  (AOI defence, intercepting/patrolling behaviours, look-ahead controller). All
  extension features are behind config flags; with flags off it reproduces master
  bit for bit (regression-tested).
- `web-simulator`: browser demonstrator of THIS original model (the library compiled
  unchanged to WebAssembly, interactive parameters, Fig. 5 model comparison).

Improvements flow one way, master -> extension branches. Nothing merges into master
without the owner's review.

## Conventions
- No em dashes in prose or comments.
- Seed every run; keep results reproducible.
- Do not add Co-Authored-By or other AI attribution trailers to commits in this
  repository; attribution policy is decided by the repository owner.
- Never commit `Student Work/`, `local_review/`, or other private review material.
