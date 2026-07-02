# Base model notes (Milestone M0)

Contract for what the adversarial extension may reuse. All statements verified against the
source on this date; file and line references are to the current commit. This is the regulated
"our model" variant as shipped in `InputFiles/Config.xml` (`ForceRegulated=1`,
`DrivingPositionEq=1`, `CollectingPositionEq=1`, `fNequation=1`, `SheepNeignborhoodSelection=1`,
`CircularPathPlanningON=1`, `StallingON=0`, single dog `M=1`).

## 1. Sheep force: summation, normalisation, step

`SheepAgent::calculateSheepPositiont1()` (`ShepherdingLibC/SheepAgent.cpp:16`):

- The behaviour list is rebuilt every step by `UpdateSheepBehaviors()`
  (`ShepherdingLibC/Modules.cpp:8`) with exactly six behaviours: Jittering,
  AttractionBehavior, CollisionAvoidanceFriends, CollisionAvoidanceOpponents,
  CollisionAvoidanceStaticObstacles, FollowingPreviousDirectionBehavior.
- Each behaviour returns a force vector via `GetForce()`; the total is
  `newForce = sum_b (F_b * Weight_b)` (`SheepAgent.cpp:62`). Weights are set in the behaviour
  constructors from the `Environment` singleton (`ShepherdingLibC/Behaviors.cpp`):
  W_e_pi_i (jitter), W_pi_Lambda (attraction), W_pi_pi (sheep-sheep repulsion),
  W_pi_beta (dog repulsion), 3 (static obstacles, hard-coded), W_pi_upsilon (previous direction).
- The summed force is normalised to a unit vector: `newForce.normalize()`
  (`SheepAgent.cpp:66`, comment says "for Strombom model only" but it is always executed).
- Step: `position_t1 = position_t + newForce * S_t_pi_i` (`SheepAgent.cpp:68`).
  Sheep speed `S_t_pi_i` defaults to 1 as an in-class initialiser
  (`ShepherdingLibC/SheepAgent.h:34`) and is never overwritten; the sheep steps at speed 1.
- `FollowingPreviousDirectionBehavior::GetForce()` returns the previous total force `F_t`
  (`Behaviors.cpp:600`), which is the previous normalised direction (h_prev in the paper).
- Two-phase update: `SheepFlock::CalcNewLoc()` computes `position_t1` for all sheep against
  positions at time t, then `SheepFlock::Move()` commits (`ShepherdingLibC/Flock.cpp:158,181`).
  Sheep are updated (CalcNewLoc) before the dog each timestep (`ShepherdingSimC_V1/Sim.cpp:199`).

Implication for M1: the AOI term is one more entry in the weighted sum, added before the
normalisation, exactly like the existing terms.

## 2. Sheepdog behaviours and step convention

`SheepDogAgent::calculateSheepDogPositiont1()` (`ShepherdingLibC/SheepDogAgent.cpp:90`):

- First updates its detected-sheep memory (`UpdateDetectedSheepList`, sensing radius
  `R_beta_pi`, `SheepDogAgent.cpp:15`) and its LCM over all detected sheep
  (`UpdateSheepDogAgentLCM`, `SheepDogAgent.cpp:73`). The dog operates on last-seen sheep
  locations, not ground truth.
- Behaviour list is rebuilt each step by `UpdateSheepDogBehaviors()` (`Modules.cpp:20`).
  Single-dog mode (M=1, mode 0): Jittering, Driving, Collecting,
  CollisionAvoidanceStaticObstacles.
- Total force `newForce = sum_b (F_b * Weight_b)`; Driving and Collecting have Weight 1.
- **The dog force is NOT renormalised before stepping**:
  `position_t1 = position_t + newForce * S_t_beta_j` (`SheepDogAgent.cpp:196`).
  This is the convention the Section 3.5 behaviour blend must copy: blend the unit behaviour
  forces with the BC weights, then multiply the raw sum by `S_t_beta_j`.
- Stalling (`stallingON`): would zero the speed near sheep, but the shipped config has
  `StallingON=0`, so speed is always `S_t_beta_j` (2.0 in config).

### Driving (`Behaviors.cpp:440`)
Active only when the flock is clustered (no detected sheep further than `fN` from the dog LCM,
via `SenseSheepOutOfFlockUsingLocalInformation`, `ShepherdingLibC/Utilities.cpp:211`).
With `DrivingPositionEq=1`:
`P_drive = Lambda_t - unit(PG - Lambda_t) * (R1 + R2)` with `R1 = fN` (`Behaviors.cpp:487`),
i.e. the point `fN + R2` behind the flock LCM on the line away from the goal `PG`.
Returned force is the unit vector from the dog to that point. Returns zero force when not
clustered (dogs pick Collecting instead).

### Collecting (`Behaviors.cpp:563`)
Active only when out-of-flock sheep exist. Targets the detected sheep furthest from the LCM.
With `CollectingPositionEq=1`:
`P_collect = sheep - unit(Lambda_t - sheep) * R2` (`Behaviors.cpp:586`),
i.e. `R2` behind the stray sheep away from the LCM. Unit force toward it. Driving and
Collecting are mutually exclusive by construction (clustered test).

### Circular path planning (`Sim.cpp:419` and `Sim.cpp:288`)
With `CircularPathPlanningON=1`, after the dog's `position_t1` is computed,
`checkSheepDogNotDisturbingSheep` may overwrite it: if the dog's next position would come
within `max(furthestDetectedSheepDist, R1) + R2 + R3` of its LCM while not near its
driving/collecting angle, the dog is rerouted along that circle. This post-processing is part
of the base dog motion and stays untouched.

## 3. Regulated repulsion (`ForceRegulated=1`)

Modulation kernel: `calc_regulated_force_magnitudeM1(d, minD, maxD, mu) = exp(-mu * d / (maxD - minD))`
(`Utilities.cpp:322`), and `M2 = M1 / sqrt(numAgents)` (`Utilities.cpp:334`).
`mu = ModulationDecayFactor = 2` in config.

- **Sheep-dog (attacker-defender)** in `CollisionAvoidanceOpponents::GetForce()`
  (`Behaviors.cpp:295`): for each dog within `R_pi_beta`:
  `factor = S_t_beta_j * exp(-mu * d / R3)` (minD=R2, maxD=R2+R3, so the denominator is R3;
  `Behaviors.cpp:309`), force `unit(dog -> sheep) * factor`. Matches REQUIREMENTS A.1.
- **Sheep-sheep (attacker-attacker)** in `CollisionAvoidanceFriends::GetForce()`
  (`Behaviors.cpp:131`): first counts sheep within `Ra_pi_pi` (`n_close`), then for each:
  `factor = exp(-mu * d / Ra_pi_pi) / sqrt(n_close)`, force `unit(other -> this) * factor`,
  summed. Matches REQUIREMENTS A.1.

Both decrease monotonically with distance (basis for test U2).

## 4. fN

`Simulation::init()` (`Sim.cpp:142`): with `fNequation=1`, `fN = Ra_pi_pi * sqrt(2N)`;
`R1` is set as an alias of `fN` (`Sim.cpp:151`). With config values (Ra=0.4, N=100),
fN = 0.4 * sqrt(200) = 5.657. Clustering test everywhere is distance-to-LCM (or GCM) > fN.

## 5. Neighbourhood

With `SheepNeignborhoodSelection=1`, `AttractionBehavior::GetForce()` (`Behaviors.cpp:19`)
builds the neighbourhood with `SenseSheepInNeighborhoodBasedOnDist(agent, env, Rs_pi_pi)`
(`Utilities.cpp:109`): all other sheep strictly within `Rs_pi_pi` (3.0 in config). The LCM of
that set (excluding self) is `Lambda_t`; attraction force is `unit(sheep -> Lambda_t)`.

## 6. Initialisation

`Simulation::init()` (`Sim.cpp:96`) seeds a single `std::mt19937 generator(randomNumberSeed)`
and consumes it in this fixed order: (1) dog flock, (2) sheep flock, (3) static obstacles.
This ordering is part of the reproducibility contract.

- **Dog** (`Flock.cpp:203`): uniform real x then y in the config rectangle
  (`SheepDogInitializationStartingX/Y` + ranges), per dog.
- **Sheep** (`Flock.cpp:23`): the init rectangle is divided into a 5x5 grid. A pattern selects
  candidate cells; per sheep, one uniform int draw picks a cell, then uniform real x and y in
  that cell. **Pattern P6 = "corners only"**: cells {0, 4, 20, 24} of the 5x5 grid
  (`Flock.cpp:115`), where cell 0 is (xMin, yMin) and rows advance in +y, i.e. the four
  corner cells of the rectangle.
- **Obstacles** (`Terrain.cpp:6`): `numberOfObstacles = density * area`; config density is 0.0,
  so no obstacles and no RNG draws.

## 7. Simulation loop and outputs

`Simulation::update()` (`Sim.cpp:190`): sheep CalcNewLoc, dog CalcNewLoc, circular-path
correction, optional fence check (paddock off), then Move both. Termination: all sheep within
`GoalRadius` of `PG` (`checkIfGoalFound`, `Sim.cpp:225`) or `maximumSteps` (1000) reached.

Headless path (`CLI`, `ShepherdingSimC_V1/CLI.cpp`): `init` forwards config to
`Simulation::init`; per step `update()` then `streamOut()` writes one CSV row:
`timestep, [per dog: ID, x, y, F_t.x, F_t.y, mode, role/targetSheep], [per sheep: ID, x, y, F_t.x, F_t.y]`.
Note `F_t` for the sheep is the normalised direction; for the dog it is the unnormalised sum.
(The header file written by `WriteOutFiles` lists extra per-sheep force columns that
`streamOut` does not emit; this mismatch is in the original code and is left as is.)

## 8. Randomness and portability caveats (affect the T0 baseline)

- `Jittering::GetForce()` uses C `rand()` (`Behaviors.cpp:240`); `srand` is never called, so
  the C stream starts from its default seed and is deterministic per platform, but the
  sequence is libc-specific.
- `std::uniform_int_distribution` / `std::uniform_real_distribution` are
  implementation-defined; libstdc++ draws differ from MSVC for the same mt19937 stream.
- Therefore the Linux headless baseline cannot bit-match a Windows run. Per REQUIREMENTS
  M0.5, the first Linux run is recorded as the T0 reference for all regression checks.
- `CLI`'s private `fieldStartX/fieldStartY` (`CLI.h:39`) are used uninitialised in
  `CLI::init`. They feed `env.FieldStartX/Y` (used only by the covering feature, inactive),
  the paddock corners (paddock off), and the obstacle rectangle (density 0, no draws), so
  the trajectories are unaffected with the shipped config. Left untouched; the headless main
  reproduces the same call path.

## 9. What the adversarial work may touch

Reuse as-is (do not modify): everything in Sections 1 to 6, the Environment singleton, the
two-phase update, the initialisation patterns, the RNG protocol. New sheep force terms enter
the Section 1 weighted sum behind config flags; new dog behaviours are new `Behavior`
subclasses blended with the Section 2 step convention (no renormalisation, multiply by
`S_t_beta_j`).
