# Reproduction report: Adversarial Patrolling Using a Shepherding Approach (IEEE SMC 2024)

C++ Shepherding Library extension, 27 conditions x 200 timesteps, single defender,
N = 10 attackers, AOI at (25, 41.667) in a 50x50 field. Config:
`InputFiles/Config_Adversarial.xml`. Reproduce with:

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
./build/shepherd_sim --experiment InputFiles/Config_Adversarial.xml
python3 tools/plot.py results
```

All 27 runs are seeded (base seed 1000 + condition index) and deterministic; the full
per-step log is `results/perstep.csv`.

## Table III comparison (pooled over runs and timesteps, mean (std))

| Metric | Paper | Python reference (primary regime) | This C++ port | Match |
|---|---|---|---|---|
| mu(R_lambda), GCM-to-AOI distance | 13.53 (8.09) | 13.41 | 17.87 (5.02) | partial: bounded standoff reproduced, band sits ~4 units further out; pooled value passes the I2 range [10, 18] |
| sigma(theta), attacker-to-AOI angle std | 0.41 (0.46) | - | 0.064 (0.019) | no: our swarm stays one compact cluster on a single bearing (see discussion) |
| theta_beta, defender-vs-swarm angle | 0.24 (1.48) | 0.19 | 0.192 (0.432) | yes (matches the reference almost exactly) |
| sigma(R), attacker-to-AOI distance std | 1.66 (2.32) | 1.45 | 1.06 (0.58) | yes (I2 range [1.0, 3.5]) |
| mu(Omega), unclustered-to-AOI distance | 0.03 (0.23) | - | 0.37 (3.59) | close to zero as in the paper; nonzero mass comes from the initial P6 corner phase |
| theta(Omega), unclustered-vs-swarm angle | 3.78e-5 (1.26e-4) | - | 0.0024 (0.024) | same character (near zero) |

## Headline percentages

| Indicator | Paper | Python reference | This C++ port | Match |
|---|---|---|---|---|
| an attacker within 5 units of the AOI | 20% | not matched either | 0% | no: the defender is never breached |
| all attackers beyond 20 units | 25% | - | 13.9% | same order; sensitive to the standoff band |
| defender between swarm and AOI | 64% | 97.6% | 97.3% | matches the reference, not the paper |
| swarm fully clustered | 89% | 86.6% | 98.9% | yes (>= 80% target) |

Sanity band check (CLAUDE.md, from the validated Python reference): mean distance 13.4,
sigma(R) 1.45, clustered 87%, defender-between 98%, theta_beta 0.19. The C++ port lands
on the reference for theta_beta (0.192 vs 0.19), defender-between (97.3 vs 97.6) and
clustered (98.9 vs 86.6, same pass side), is close on sigma(R) (1.06 vs 1.45), and is
above it on mean distance (17.9 vs 13.4).

## I2 tolerance checklist (all pass)

- mean GCM-to-AOI distance 17.87 in [10, 18]: PASS
- sigma(R) 1.06 in [1.0, 3.5]: PASS
- swarm fully clustered 98.9% >= 80%: PASS
- defender between swarm and AOI 97.3% >= 55%: PASS
- theta_beta 0.192 <= 0.6: PASS
- Fig 5 shape: mean distance falls from ~35 to a bounded band; final-quarter mean
  15.84 < 25 (no runaway): PASS
- Fig 6: M3 < pi/2 for 97.3% of steps >= 90%: PASS
- Driving among the top two behaviours by usage: PASS (top, 36.2%)

## Behaviour usage (weighted share of chosen BCs)

Driving 36.2%, Collecting 30.1%, Intercepting 19.2%, Patrolling 14.5%. Driving is the
dominant behaviour, as the paper reports. Most-chosen single combinations: BC1 pure
driving (22.4%), BC8 collect+intercept (17.9%), BC5 drive+collect (11.6%).

## Figures

- `fig5_gcm_distance.svg`: mean/min/max GCM-to-AOI distance over the 27 conditions.
  Falls from ~35 to a bounded oscillating band around 14-16 by t~80 and stays bounded,
  matching the Fig 5 shape.
- `fig6_defender_angle.svg`: mean and max defender-side angle M3; the mean stays far
  below pi/2 throughout (defender on the swarm side of the AOI), matching Fig 6.
- `behaviour_usage.svg`: behaviour usage bars.

## Honest discussion (I3)

**What reproduces.** The qualitative claims of the paper reproduce fully: the defender
holds the swarm in a bounded standoff away from the AOI (Fig 5 shape, no runaway), it
stays between the swarm and the AOI essentially always (Fig 6, M3 << pi/2), the swarm
stays clustered, and Driving is the dominant behaviour of the look-ahead controller.
Five of the eight I2/Table III quantities land on or near the validated Python
reference values.

**What does not, and which assumption is responsible.**

1. *Mean distance 17.9 vs 13.53.* The standoff distance is set by the
   repulsion-attraction balance (~13.9 units from the defender) plus the defender's
   own distance from the AOI. Our defender spends ~1/3 of its time at the driving
   position (12.9 units out on the swarm side), which lifts the pooled band by ~4
   units. The responsible assumption is the unpublished metric-combination formula
   (decisions.md Section 1): the min-max scaled sum with any positive M1 weight makes
   distance-increasing choices win nearly every step, and even with wM1 = 0 the
   Driving/Collecting share keeps the band near 18 rather than 14. We report the
   passing-tolerance configuration rather than tuning further, because pushing the
   mean down would silently break the Driving-dominant usage requirement.
2. *sigma(theta) 0.064 vs 0.41 and any-attacker-within-5 0% vs 20%.* Both paper values
   require episodes where attackers spread around the AOI or slip past the defender.
   Our controller (and the Python reference, whose defender-between was 97.6% vs the
   paper's 64%) produces a defender that is essentially never out of position, so no
   breaches occur and the swarm stays on one bearing. This is the two-regime split
   REQUIREMENTS.md predicts: a "standoff" regime (matched here) and an "engagement"
   regime with breaches and spread that no single parameter set reproduces
   simultaneously. For reference, an engagement-leaning configuration from the M6
   sweep (equal metric weights, guard radius 5) gives all-beyond-20 = 88.5% and mean
   distance 28: the indicators move in the paper's direction only by trading away the
   mean-distance and beyond-20 matches, confirming the split.
3. *Defender-between 97.3% vs the paper's 64%.* Same cause as (2), and shared with the
   reference implementation. We do not tune this number down: making the defender
   deliberately worse (e.g. huge patrol radius) would match 64% only by breaking Fig 6
   and theta_beta.

**Not overclaiming.** No single parameter set matched every Table III row plus every
headline percentage at once, exactly as the Python reference found. The shipped
configuration is the standoff regime, which satisfies all I2 tolerances; the numbers
above state plainly where it departs from Table III and why.

## Provenance

- Base physics untouched and regression-locked: with `AdversarialMode=0` the T0
  baseline hash is bit-for-bit identical (ctest `t0_regression`).
- Unit tests U1-U8 pass (ctest `unit_tests`).
- Toolchain: g++ 13.3.0, Ubuntu 24.04, cmake 3.28, tinyxml2 10.0.0.
