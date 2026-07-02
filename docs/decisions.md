# Decisions log: adversarial patrolling extension

Every choice the paper (Zhou, El-Fiqi, Hussein, IEEE SMC 2024) or REQUIREMENTS.md left
open, with the exact values used. Config keys live in `InputFiles/Config_Adversarial.xml`;
code references are to the current commit.

## 1. Metric-combination formula (unpublished, REQUIREMENTS Section 5.1)

Implemented the stated default in `selectBestCombination()`
(`ShepherdingSimC_V1/AdversarialController.cpp`), kept in one small function so it can
be swapped:

- min-max scale each of M1, M2, M3 across the 10 candidates (scale = 0 when the range
  is 0);
- `desirability = wM1*scale(M1) + wM2*(1-scale(M2)) + wM3*(1-scale(M3))`;
- argmax, first maximum wins (ties therefore favour lower-numbered BCs, i.e. Driving).

Final weights after the M6 sweep: **wM1 = 0, wM2 = 3, wM3 = 1**
(`MetricWeight_M1/M2/M3`). The equal-weight default (1,1,1) produced a defender that
chased the swarm outward indefinitely (pooled mean distance 24 to 28, all-beyond-20 for
62 to 88 percent of steps) because one-step M1 differences, however tiny, are amplified
to the full [0,1] range by the min-max scaling, so distance-increasing BCs win almost
every step. Down-weighting M1 to 0 and favouring swarm compactness (M2) restores the
bounded standoff the paper reports. This weight choice is the single largest lever on
the results and the most likely locus of any residual mismatch with Table III.

## 2. The 27 initial conditions (unpublished, REQUIREMENTS Section 5.2)

Reconstruction: 3 attacker-box anchors x 3 box widths x 3 box heights, all attacker
boxes anchored low in the 50x50 field (far from the AOI), Pattern P6 (corners only)
inside the box, defender uniform in a 5x5 square just below the AOI.

- anchors (x, y): (2, 2), (15, 2), (28, 2)   [`Experiment_startX`, `Experiment_startY`]
- widths: 10, 15, 20                          [`Experiment_boxW`]
- heights: 10, 15, 20                         [`Experiment_boxH`]
- condition index c = 0..26 maps to (anchor c/9, width (c/3)%3, height c%3)
- defender square: x in [23, 28], y in [34, 39]  [`Experiment_dog*`]; AOI (25, 41.667)
- seeds: `Experiment_base_seed` (1000) + condition index

## 3. Adversarial driving goal

The library's Driving positions the dog `fN + R2` behind the flock LCM on the line away
from the goal `env.PG`. To herd the swarm away from the AOI, the controller sets
`env.PG = 2*Lambda_t - AOI` (the AOI mirrored about the dog's LCM estimate) every step
before evaluating Driving. The driving position then lies between the AOI and the
swarm, as the paper requires. `Driving`/`Collecting` themselves are untouched.

## 4. Threat selection for Intercepting

`threat = argmin_i ||p_i - AOI||` over the ground-truth flock, per REQUIREMENTS A.3.
The dog's own sensing memory (`R_beta_pi`-limited, last-seen locations) is used for
Driving and Collecting exactly as in the base model, but the intercept threat is global
knowledge; the paper does not state a sensing restriction for it.

## 5. Patrol phase and RNG protocol

- Patrol phase advances once per real timestep (one uniform draw from `patrolRng`);
  the resulting patrol force is shared by all 10 look-ahead candidates, so patrol
  jitter cannot couple across candidates (REQUIREMENTS 3.6).
- Sheep jitter in adversarial mode draws from `advJitterRng` (mt19937) instead of the
  global `rand()` stream, because mt19937 state can be snapshot and restored around
  virtual steps while `rand()` state cannot. With `AdversarialMode=0` the original
  `rand()` path executes, preserving the T0 baseline bit for bit. (The adversarial
  weights set W_e_pi = 0, so the jitter values are inert anyway; only stream hygiene
  matters.)
- Substream seeds: `advJitterRng` = 1000003 + 7*seed, `patrolRng` = 2000003 + 13*seed.
- Virtual look-ahead: sheep {position_t1, F_t, Lambda_t} and the jitter stream are
  snapshot before, and restored after, the 10 candidate evaluations; every candidate
  sees identical jitter draws. Verified by U8.

## 6. The adversarial dog force is the pure Table II blend

`F_dog = sum_j w_j F_j` over (Driving, Collecting, Intercepting, Patrolling) only; the
base dog's Jittering, obstacle-avoidance and dog-dog collision terms are not added
(single dog, no obstacles in the experiment; the paper's Eq. for the defender lists
only the four behaviours). Step convention confirmed from the base model (M0 notes):
the blend is NOT renormalised, and is multiplied by `S_t_beta_j`.

## 7. Simulation loop differences in adversarial mode

- Goal-based termination is bypassed: runs last exactly `Experiment_steps` (200) steps.
- The circular path-planning correction (`CircularPathPlanningON`) is not applied to
  the adversarial dog; the driver commits the blended step directly.
- Update order per step matches the base `Simulation::update`: sheep CalcNewLoc first
  (against the dog at time t), then the dog controller, then both Move.
- When the dog has never detected any sheep, Driving and Collecting return zero force
  (the base code would compute a 0/0 LCM); Intercepting and Patrolling still act.

## 8. Attacker agent ranges for the adversarial scenario

`Ra_pi_pi = 2`, `Rs_pi_pi = 20` (the Strombom values quoted in the config's own
comments), not the shipped herding values (0.4, 3). With N=10 and Ra=0.4 the cluster
test radius fN = 1.79 units and the cohesion range 3 units are so tight that the P6
corner groups never merge (clustered 6.5 percent of steps vs the paper's 89). With the
Strombom values fN = 8.94 and clustering reaches 98.9 percent. All other physics values
are the shipped regulated-variant ones (R2=4, R3=10, mu=2, S_b=2, ForceRegulated=1).

## 9. Guard radii

`Intercept_dist = 0.5`, `Patrol_radius = 0.5` after the M6 sweep. The swarm's standoff
sits at the repulsion-attraction balance ~13.9 units from the DOG
(W_pi_beta*S_b*exp(-mu d/R3) = W_pi_I), so the GCM-to-AOI distance is roughly
13.9 plus the dog's distance from the AOI; small guard radii keep the defender near the
AOI when not driving, which is what bounds the pooled mean distance.

## 10. Omega (unclustered) metric definitions

Table III's mu(Omega) and theta(Omega) are not formally defined in the requirements.
Implemented: mu(Omega) = mean AOI distance over unclustered attackers (those further
than fN from the GCM), 0 when the set is empty; theta(Omega) = mean angle at the AOI
between an unclustered attacker and the GCM, 0 when empty. The paper's near-zero values
(0.03, 3.78e-5) are consistent with a rarely-populated Omega set under either plausible
definition.
