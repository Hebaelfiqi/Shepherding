# T0 regression baseline (Milestone M0.5)

Reference output of the unmodified base model, headless Linux build.

- Command: `./build/shepherd_sim Config.xml` run in a directory containing a copy of the
  shipped `InputFiles/Config.xml` (seed 0, N=100, M=1, regulated "our model" variant).
- Result: task completed at timestep 79, all sheep at goal (`T0_CompletionTime.txt`).
- `T0_Config_OutPutData.csv`: full per-step trajectory CSV; sha256 in `T0_sha256.txt`.
- Toolchain: g++ 13.3.0, libstdc++ (Ubuntu 24.04), cmake 3.28.3, tinyxml2 10.0.0.
- Determinism verified: two consecutive runs produced identical sha256.

No Windows/MSVC run was available, so per REQUIREMENTS.md M0.5 this Linux run is the
recorded reference. It cannot bit-match a Windows build because `std::uniform_*`
distributions and the C `rand()` stream (jitter force) are implementation-specific.

T0 check after any change: rebuild, rerun the command above with seed 0, and compare
sha256 against `T0_sha256.txt`. With `AdversarialMode=0` (from M1 onward) the hash must
be identical.
