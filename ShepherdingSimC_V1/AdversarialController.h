// AdversarialController.h : app-side driver for the adversarial patrolling extension.
// Applies the adversarial config to the Environment singleton, computes the four dog
// behaviour forces, blends them per Table II, and runs the one-step look-ahead greedy
// selection (REQUIREMENTS.md Sections 3.2 to 3.6). All of it is inert unless
// AdversarialMode=1.

#pragma once
#include <string>
#include <vector>
#include "Vector2.h"

class SheepDogAgent;

// Copy the parsed adversarial config keys into the Environment singleton and seed the
// dedicated RNG substreams from the run seed. Call once per run, after Simulation::init
// (which owns the base fields) and before the first update.
void applyAdversarialEnvSettings(int runSeed);

// The three look-ahead metrics evaluated on a (sheep positions, dog position) state
// (REQUIREMENTS.md A.6). Positions are passed explicitly so the same code serves both
// virtual candidate states and real post-step logging.
struct AdversarialMetrics
{
	double M1;   // ||GCM - AOI||, want large
	double M2;   // circular std of attacker-to-AOI angles, want small
	double M3;   // angle between (AOI->GCM) and (AOI->dog), want small
};
AdversarialMetrics evaluateMetrics(const std::vector<Vector2f>& sheepPositions, Vector2f dogPosition);

// Table II behaviour-combination weights over (Driving, Collecting, Intercepting,
// Patrolling); kBehaviorCombinations[k][j], k = 0..9 for BC1..BC10.
extern const float kBehaviorCombinations[10][4];

// Min-max scale + equal-weight combination + argmax over the 10 candidates
// (REQUIREMENTS.md A.7). Exposed for unit test U7. Uses MetricWeight_M1/M2/M3.
int selectBestCombination(const AdversarialMetrics candidates[10]);

// Per-step record of what the controller did, for logging.
struct AdversarialStepInfo
{
	int chosenBC = 0;                 // 0-based index into kBehaviorCombinations
	AdversarialMetrics realMetrics;   // metrics on the committed state (after Move)
	Vector2f dogForce;                // executed blended force
};

// Compute and commit one adversarial dog step (sets dog->position_t1). Must be called
// after the sheep flock CalcNewLoc for this timestep and before Move. Returns the
// chosen BC and diagnostics.
AdversarialStepInfo adversarialDogStep(SheepDogAgent* dog);
