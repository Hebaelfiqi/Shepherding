// AdversarialController.cpp : behaviour blend and one-step look-ahead greedy controller
// (REQUIREMENTS.md Sections 3.5, 3.6, Appendix A). App-side; the base physics in
// ShepherdingLibC is reused unchanged.

#include "AdversarialController.h"
#include "ConfigLoaderPortable.h"
#include "Environment.h"
#include "Flock.h"
#include "SheepAgent.h"
#include "SheepDogAgent.h"
#include "Behaviors.h"
#include "AdversarialBehaviors.h"
#include <cmath>
#include <vector>
#include <algorithm>

// Table II: weight tuples over (Driving, Collecting, Intercepting, Patrolling).
const float kBehaviorCombinations[10][4] = {
	{ 1.0f, 0.0f, 0.0f, 0.0f },   // BC1
	{ 0.0f, 1.0f, 0.0f, 0.0f },   // BC2
	{ 0.0f, 0.0f, 1.0f, 0.0f },   // BC3
	{ 0.0f, 0.0f, 0.0f, 1.0f },   // BC4
	{ 0.5f, 0.5f, 0.0f, 0.0f },   // BC5
	{ 0.5f, 0.0f, 0.5f, 0.0f },   // BC6
	{ 0.5f, 0.0f, 0.0f, 0.5f },   // BC7
	{ 0.0f, 0.5f, 0.5f, 0.0f },   // BC8
	{ 0.0f, 0.5f, 0.0f, 0.5f },   // BC9
	{ 0.0f, 0.0f, 0.5f, 0.5f },   // BC10
};

void applyAdversarialEnvSettings(int runSeed)
{
	Environment& env = Environment::getInstance();
	env.AdversarialMode = AdversarialMode;
	if (AdversarialMode != 1) return;

	env.AOI = Vector2f(AOI_x, AOI_y);
	env.W_pi_I = W_pi_I;
	env.Intercept_dist = Intercept_dist;
	env.Patrol_radius = Patrol_radius;
	env.Patrol_step = Patrol_step;
	env.Patrol_noise = Patrol_noise;

	// Substream seeds derived from the run seed with distinct offsets so streams are
	// decorrelated but fully reproducible per run.
	env.advJitterRng.seed(1000003u + 7u * (unsigned)runSeed);
	env.patrolRng.seed(2000003u + 13u * (unsigned)runSeed);

	if (AdversarialWeights == 1)
	{
		// Section 3.2 adversarial sheep weights. Precedence:
		// W_pi_beta >= W_pi_pi > W_pi_Lambda > W_pi_upsilon > W_pi_I > W_e_pi.
		env.W_pi_upsilon = 0.5f;
		env.W_pi_Lambda = 1.0f;
		env.W_pi_beta = 2.0f;
		env.W_pi_pi = 2.0f;
		env.W_e_pi_i = 0.0f;
	}
}

AdversarialMetrics evaluateMetrics(const std::vector<Vector2f>& sheepPositions, Vector2f dogPosition)
{
	// Double precision internally (A.6); inputs are float positions.
	Environment& env = Environment::getInstance();
	const double ax = env.AOI.x, ay = env.AOI.y;
	const size_t n = sheepPositions.size();

	AdversarialMetrics m{ 0, 0, 0 };
	if (n == 0) return m;

	double gx = 0, gy = 0, sc = 0, ss = 0;
	for (size_t i = 0; i < n; i++)
	{
		gx += sheepPositions[i].x;
		gy += sheepPositions[i].y;
		double th = std::atan2(ay - sheepPositions[i].y, ax - sheepPositions[i].x);
		sc += std::cos(th);
		ss += std::sin(th);
	}
	gx /= n; gy /= n;

	// M1: GCM to AOI distance
	m.M1 = std::sqrt((gx - ax) * (gx - ax) + (gy - ay) * (gy - ay));

	// M2: circular standard deviation of attacker-to-AOI angles
	double R = std::sqrt((sc / n) * (sc / n) + (ss / n) * (ss / n));
	R = std::min(1.0, std::max(R, 1e-12));
	m.M2 = std::sqrt(std::max(0.0, -2.0 * std::log(R)));

	// M3: angle at the AOI between the GCM and the dog
	double v1x = gx - ax, v1y = gy - ay;
	double v2x = dogPosition.x - ax, v2y = dogPosition.y - ay;
	double n1 = std::sqrt(v1x * v1x + v1y * v1y), n2 = std::sqrt(v2x * v2x + v2y * v2y);
	if (n1 > 0 && n2 > 0)
	{
		double c = (v1x * v2x + v1y * v2y) / (n1 * n2);
		m.M3 = std::acos(std::min(1.0, std::max(-1.0, c)));
	}
	return m;
}

// KNOWN UNKNOWN (REQUIREMENTS.md Section 5.1): the paper does not publish the exact
// metric-combination formula. This is the stated default: min-max scale each metric
// across the 10 candidates (0 when the range is 0), then
//   desirability = wM1*scale(M1) + wM2*(1-scale(M2)) + wM3*(1-scale(M3))
// with configurable weights MetricWeight_M1/M2/M3 (default 1,1,1). Swap here if the
// original formula becomes available.
int selectBestCombination(const AdversarialMetrics candidates[10])
{
	auto scaled = [](const double v[10], double out[10]) {
		double lo = v[0], hi = v[0];
		for (int k = 1; k < 10; k++) { lo = std::min(lo, v[k]); hi = std::max(hi, v[k]); }
		for (int k = 0; k < 10; k++) out[k] = (hi > lo) ? (v[k] - lo) / (hi - lo) : 0.0;
	};
	double m1[10], m2[10], m3[10], s1[10], s2[10], s3[10];
	for (int k = 0; k < 10; k++) { m1[k] = candidates[k].M1; m2[k] = candidates[k].M2; m3[k] = candidates[k].M3; }
	scaled(m1, s1); scaled(m2, s2); scaled(m3, s3);

	int best = 0;
	double bestDesir = -1;
	for (int k = 0; k < 10; k++)
	{
		double d = MetricWeight_M1 * s1[k] + MetricWeight_M2 * (1.0 - s2[k]) + MetricWeight_M3 * (1.0 - s3[k]);
		if (d > bestDesir) { bestDesir = d; best = k; }
	}
	return best;
}

// Free the behaviour objects a CalcNewLoc pass allocated on each sheep. The base code
// rebuilds (and leaks) these every step; the look-ahead multiplies the passes by 10,
// so the driver reclaims them to keep the 27-run experiment memory-flat.
static void freeSheepBehaviors()
{
	Environment& env = Environment::getInstance();
	for (int i = 0; i < env.sheepFlock->size(); i++)
	{
		SheepAgent* s = (*env.sheepFlock)[i];
		for (Behavior* b : s->agentBehaviors) delete b;
		s->agentBehaviors.clear();
	}
}

AdversarialStepInfo adversarialDogStep(SheepDogAgent* dog)
{
	Environment& env = Environment::getInstance();
	AdversarialStepInfo info;

	// Sensing update, exactly as the base calculateSheepDogPositiont1 does first.
	dog->UpdateDetectedSheepList();
	bool haveDetected = dog->get_DetectedSheep().size() > 0;
	if (haveDetected) dog->UpdateSheepDogAgentLCM(); // guard: base code would divide 0/0

	// Adversarial driving goal (docs/decisions.md): mirror the AOI about the dog's LCM
	// estimate of the swarm, so the unchanged Driving routine places the dog between
	// the AOI and the swarm and herds the swarm away from the AOI.
	if (haveDetected)
	{
		env.PG = dog->Lambda_t * 2.0 - env.AOI;
	}

	// The four behaviour unit forces, computed once on the real state; only the blend
	// weights differ across candidates. Driving/Collecting need detected sheep.
	Vector2f F[4];
	if (haveDetected)
	{
		Driving driving(dog);
		F[0] = driving.GetForce();
		Collecting collecting(dog);
		F[1] = collecting.GetForce();
	}
	Intercepting intercepting(dog);
	F[2] = intercepting.GetForce();
	Patrolling patrolling(dog);
	F[3] = patrolling.GetForce(); // advances the real patrol phase once per real step;
	                              // the same F_pat is used by all candidates so patrol
	                              // jitter cannot couple across them (Section 3.6)

	auto blend = [&](int k) {
		Vector2f f = Vector2f();
		for (int j = 0; j < 4; j++)
		{
			f = f + F[j] * kBehaviorCombinations[k][j];
		}
		return f;
	};

	int chosen = 0;
	if (LookAheadController == 1)
	{
		// Snapshot everything the virtual sheep steps will touch. The real sheep
		// CalcNewLoc for this timestep has already run, so position_t1 / F_t / Lambda_t
		// hold the real reaction that Move() will commit; restore them afterwards.
		struct SheepSnap { Vector2f p1, F, L; };
		std::vector<SheepSnap> snap(env.sheepFlock->size());
		for (int i = 0; i < env.sheepFlock->size(); i++)
		{
			SheepAgent* s = (*env.sheepFlock)[i];
			snap[i] = { s->position_t1, s->F_t, s->Lambda_t };
		}
		Vector2f dogRealPos = dog->position_t;
		std::mt19937 jitterSnap = env.advJitterRng; // virtual steps must not consume the real stream

		AdversarialMetrics candidates[10];
		std::vector<Vector2f> vpos(env.sheepFlock->size());
		for (int k = 0; k < 10; k++)
		{
			Vector2f dv = dogRealPos + blend(k) * env.S_t_beta_j; // virtual dog step (A.5 convention)
			dog->position_t = dv;
			env.advJitterRng = jitterSnap;       // identical jitter draws for every candidate
			env.sheepFlock->CalcNewLoc();        // one virtual sheep reaction step against dv
			for (int i = 0; i < env.sheepFlock->size(); i++)
			{
				vpos[i] = (*env.sheepFlock)[i]->position_t1;
			}
			candidates[k] = evaluateMetrics(vpos, dv);
			dog->position_t = dogRealPos;
			freeSheepBehaviors();
		}

		// Restore the real state and stream.
		env.advJitterRng = jitterSnap;
		for (int i = 0; i < env.sheepFlock->size(); i++)
		{
			SheepAgent* s = (*env.sheepFlock)[i];
			s->position_t1 = snap[i].p1;
			s->F_t = snap[i].F;
			s->Lambda_t = snap[i].L;
		}

		chosen = selectBestCombination(candidates);
	}

	// Execute the chosen BC as the real dog step, using the library convention from
	// docs/base_model_notes.md Section 2: raw blended force, NOT renormalised, times
	// S_t_beta_j.
	Vector2f Fdog = blend(chosen);
	dog->F_t = Fdog;
	dog->position_t1 = dog->position_t + Fdog * env.S_t_beta_j;

	info.chosenBC = chosen;
	info.dogForce = Fdog;
	return info;
}
