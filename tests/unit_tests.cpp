// unit_tests.cpp : minimal assert harness for the adversarial extension
// (REQUIREMENTS.md Section 6.2, tests U1 to U8). Run from the repository root so the
// config paths resolve. Prints one PASS/FAIL line per test and exits nonzero on any
// failure.

#include <cstdio>
#include <cmath>
#include <string>
#include <vector>
#include <random>

#include "Environment.h"
#include "Flock.h"
#include "SheepAgent.h"
#include "SheepDogAgent.h"
#include "Utilities.h"
#include "AdversarialBehaviors.h"
#include "AdversarialController.h"
#include "ConfigLoaderPortable.h"
#include "Sim.h"

static int failures = 0;
static int checks = 0;

#define CHECK_NEAR(name, a, b, tol) do { \
	checks++; \
	double _a = (a), _b = (b); \
	if (std::fabs(_a - _b) > (tol)) { \
		printf("FAIL %s: %.12g vs %.12g (tol %g)\n", name, _a, _b, (double)(tol)); failures++; } \
} while (0)

#define CHECK_TRUE(name, cond) do { \
	checks++; \
	if (!(cond)) { printf("FAIL %s\n", name); failures++; } \
} while (0)

static Environment& env = Environment::getInstance();

// U1: AOI attraction equals unit(sheep -> AOI).
static void testU1()
{
	env.AOI = Vector2f(25.0f, 41.667f);
	env.W_pi_I = 0.25f;

	SheepAgent sheep(25.0f, 10.0f, 1);        // axis-aligned: exact unit vector (0,1)
	AOIAttraction b(&sheep);
	Vector2f f = b.GetForce();
	CHECK_NEAR("U1 axis x", f.x, 0.0, 1e-9);
	CHECK_NEAR("U1 axis y", f.y, 1.0, 1e-9);

	SheepAgent sheep2(22.0f, 37.667f, 2);     // generic offset; expected via same float ops
	AOIAttraction b2(&sheep2);
	Vector2f f2 = b2.GetForce();
	float dx = env.AOI.x - 22.0f, dy = env.AOI.y - 37.667f;
	float len = std::sqrt(dx * dx + dy * dy);
	CHECK_NEAR("U1 generic x", f2.x, dx / len, 1e-9);
	CHECK_NEAR("U1 generic y", f2.y, dy / len, 1e-9);
	printf("U1 AOI attraction: done\n");
}

// U2: regulated attacker-defender repulsion magnitude S_b * exp(-mu d / R3),
// monotonically decreasing with distance.
static void testU2()
{
	const float Sb = 2.0f, mu = 2.0f;
	const float R2v = 4.0f, R3v = 10.0f;
	float prev = 1e30f;
	for (int i = 1; i <= 15; i++)
	{
		float d = (float)i;
		float impl = Sb * calc_regulated_force_magnitudeM1(d, R2v, R2v + R3v, mu);
		float expectFloat = Sb * std::exp(-mu * d / R3v);   // same float ops as the impl
		double expectDouble = 2.0 * std::exp(-2.0 * (double)d / 10.0);
		CHECK_NEAR("U2 float-exact", impl, expectFloat, 1e-9);
		CHECK_NEAR("U2 formula", impl, expectDouble, 1e-6);
		CHECK_TRUE("U2 monotonic", impl < prev);
		prev = impl;
	}
	printf("U2 regulated repulsion: done\n");
}

// U3: intercept target lies on the AOI->threat segment at Intercept_dist from the AOI,
// and the force points from the dog toward it.
static void testU3()
{
	env.AOI = Vector2f(25.0f, 40.0f);
	env.Intercept_dist = 5.0f;

	std::mt19937 gen(1);
	SheepFlock flock(gen, 3, 0, 1, 0, 1, 2, "P1");
	flock[0]->position_t = Vector2f(25.0f, 30.0f);   // closest to AOI (d=10) -> threat
	flock[1]->position_t = Vector2f(10.0f, 10.0f);
	flock[2]->position_t = Vector2f(40.0f, 5.0f);
	env.sheepFlock = &flock;

	SheepDogAgent dog(25.0f, 20.0f, 1, 2.0f, 0);
	Intercepting b(&dog);
	Vector2f target = b.GetInterceptTarget();
	CHECK_NEAR("U3 target x", target.x, 25.0, 1e-9);
	CHECK_NEAR("U3 target y", target.y, 35.0, 1e-9);  // AOI + unit(AOI->threat)*5 = (25,35)
	CHECK_NEAR("U3 target dist from AOI", target.dist(env.AOI), 5.0, 1e-6);

	Vector2f f = b.GetForce();
	CHECK_NEAR("U3 force x", f.x, 0.0, 1e-9);          // unit(dog(25,20) -> (25,35)) = (0,1)
	CHECK_NEAR("U3 force y", f.y, 1.0, 1e-9);
	printf("U3 intercepting: done\n");
}

// U4: patrol target on the circle of Patrol_radius about the AOI; phase advances by
// Patrol_step within the noise band on successive calls.
static void testU4()
{
	env.AOI = Vector2f(25.0f, 40.0f);
	env.Patrol_radius = 7.0f;
	env.Patrol_step = 0.3f;
	env.Patrol_noise = 0.0f;
	env.patrolRng.seed(42);

	SheepDogAgent dog(20.0f, 20.0f, 1, 2.0f, 0);
	Patrolling b(&dog);
	b.GetForce();
	CHECK_NEAR("U4 phase 1", dog.patrolPhi, 0.3, 1e-6);
	Vector2f t1 = b.GetPatrolTarget();
	CHECK_NEAR("U4 on circle", t1.dist(env.AOI), 7.0, 1e-5);
	b.GetForce();
	CHECK_NEAR("U4 phase 2", dog.patrolPhi, 0.6, 1e-6);

	env.Patrol_noise = 0.1f;
	float before = dog.patrolPhi;
	b.GetForce();
	float adv = dog.patrolPhi - before;
	CHECK_TRUE("U4 noise band", adv >= 0.2f - 1e-6f && adv <= 0.4f + 1e-6f);
	printf("U4 patrolling: done\n");
}

// U5: the ten weight tuples equal Table II exactly.
static void testU5()
{
	const float expect[10][4] = {
		{1,0,0,0},{0,1,0,0},{0,0,1,0},{0,0,0,1},{0.5f,0.5f,0,0},
		{0.5f,0,0.5f,0},{0.5f,0,0,0.5f},{0,0.5f,0.5f,0},{0,0.5f,0,0.5f},{0,0,0.5f,0.5f} };
	for (int k = 0; k < 10; k++)
		for (int j = 0; j < 4; j++)
			CHECK_TRUE("U5 table", kBehaviorCombinations[k][j] == expect[k][j]);
	printf("U5 BC table: done\n");
}

// U6: metrics on a hand-built state match analytic values.
static void testU6()
{
	env.AOI = Vector2f(0.0f, 0.0f);
	std::vector<Vector2f> pos = { Vector2f(0,-10), Vector2f(0,-12), Vector2f(0,-14) };
	Vector2f dogPos(5.0f, -12.0f);
	AdversarialMetrics m = evaluateMetrics(pos, dogPos);
	CHECK_NEAR("U6 M1", m.M1, 12.0, 1e-9);                       // GCM (0,-12)
	CHECK_NEAR("U6 M2", m.M2, 0.0, 1e-9);                        // identical angles
	CHECK_NEAR("U6 M3", m.M3, std::acos(144.0 / 156.0), 1e-9);   // angle GCM-AOI-dog

	// square around a point 10 below the AOI: M1 = 10, known circular std
	std::vector<Vector2f> pos2 = { Vector2f(-1,-9), Vector2f(1,-9), Vector2f(-1,-11), Vector2f(1,-11) };
	AdversarialMetrics m2 = evaluateMetrics(pos2, Vector2f(0.0f, -1.0f));
	CHECK_NEAR("U6 M1 square", m2.M1, 10.0, 1e-9);
	double sc = 0, ss = 0;
	for (auto& p : pos2) { double th = std::atan2(0.0 - p.y, 0.0 - p.x); sc += std::cos(th); ss += std::sin(th); }
	double R = std::sqrt(sc * sc + ss * ss) / 4.0;
	CHECK_NEAR("U6 M2 square", m2.M2, std::sqrt(-2.0 * std::log(R)), 1e-9);
	CHECK_NEAR("U6 M3 aligned", m2.M3, 0.0, 1e-9);               // dog on the GCM ray
	printf("U6 metrics: done\n");
}

// U7: scaler and argmax on synthetic candidate arrays.
static void testU7()
{
	MetricWeight_M1 = MetricWeight_M2 = MetricWeight_M3 = 1;
	AdversarialMetrics c[10];

	for (int k = 0; k < 10; k++) c[k] = { (double)k, 0.0, 0.0 };   // M1 rises: argmax = 9
	CHECK_TRUE("U7 max M1", selectBestCombination(c) == 9);

	for (int k = 0; k < 10; k++) c[k] = { 5.0, (k == 2) ? 0.0 : 1.0, 0.0 }; // min M2 at 2
	CHECK_TRUE("U7 min M2", selectBestCombination(c) == 2);

	for (int k = 0; k < 10; k++) c[k] = { 5.0, 1.0, (k == 7) ? 0.2 : 0.9 }; // min M3 at 7
	CHECK_TRUE("U7 min M3", selectBestCombination(c) == 7);

	for (int k = 0; k < 10; k++) c[k] = { 3.0, 3.0, 3.0 };          // zero range: first wins
	CHECK_TRUE("U7 zero range", selectBestCombination(c) == 0);

	// mixed: desirability computed by hand. M1: 0..9 scaled k/9. M2: k%2 (scaled as-is).
	// M3: (9-k)/9 scaled. d = k/9 + (1 - k%2) + (1 - (9-k)/9). k=8: 8/9+1+8/9 = 2.777 max.
	for (int k = 0; k < 10; k++) c[k] = { (double)k, (double)(k % 2), (double)(9 - k) / 9.0 };
	CHECK_TRUE("U7 mixed", selectBestCombination(c) == 8);
	printf("U7 selection: done\n");
}

// U8: identical seed -> identical trajectories; different seeds differ; the virtual
// look-ahead does not perturb the real RNG streams.
static double runShortAdversarial(int seed, int steps)
{
	Simulation* sim = new Simulation();
	sim->init(seed, N, M, 0, 0, FieldLength, FieldLength,
		R_pi_beta, Ra_pi_pi, Rs_pi_pi, R_beta_beta, R_beta_pi,
		W_pi_pi, W_beta_beta, W_pi_beta, W_pi_Lambda, W_pi_upsilon, W_e_pi_i, W_e_beta_j,
		S_t_beta_j, eta, card_Omega_pi_pi, card_Omega_beta_pi,
		gLocX, gLocY, paddockLength, paddockWidth, false, false,
		StallingON, StallingDistance, R2, R3, goalRadius,
		ForceRegulated, fNequation, DrivingPositionEq, CollectingPositionEq,
		SheepNeignborhoodSelection, ModulationDecayFactor,
		sheepInitializationStartingX, sheepInitializationStartingY,
		sheepInitializationXRange, sheepInitializationYRange, sheepInitializationPattern,
		(int)Experiment_dogX, (int)Experiment_dogY, (int)Experiment_dogRange, (int)Experiment_dogRange,
		obstaclesDensity, obstaclesRadius);
	applyAdversarialEnvSettings(seed);

	SheepDogAgent* dog = (*env.sheepDogFlock)[0];
	double hash = 0;
	for (int t = 1; t <= steps; t++)
	{
		env.currentTime = t;
		env.sheepFlock->CalcNewLoc();

		std::mt19937 jitterBefore = env.advJitterRng;   // stream state entering the controller
		adversarialDogStep(dog);
		CHECK_TRUE("U8 jitter stream untouched by look-ahead", env.advJitterRng == jitterBefore);

		env.sheepFlock->Move();
		env.sheepDogFlock->Move();
		for (int i = 0; i < env.sheepFlock->size(); i++)
		{
			hash += (*env.sheepFlock)[i]->position_t.x * (t + 1) + (*env.sheepFlock)[i]->position_t.y;
		}
		hash += dog->position_t.x * 3.1 + dog->position_t.y * 1.7;
	}
	return hash;
}

static void testU8()
{
	loadConfigurationPortable("InputFiles/Config_Adversarial.xml");
	CHECK_TRUE("U8 adversarial config found", AdversarialMode == 1);

	double h1 = runShortAdversarial(123, 25);
	double h2 = runShortAdversarial(123, 25);
	double h3 = runShortAdversarial(321, 25);
	CHECK_TRUE("U8 same seed identical", h1 == h2);
	CHECK_TRUE("U8 different seed differs", h1 != h3);
	printf("U8 determinism: done\n");
}

int main()
{
	testU1();
	testU2();
	testU3();
	testU4();
	testU5();
	testU6();
	testU7();
	testU8();

	if (failures == 0)
	{
		printf("ALL TESTS PASSED (%d checks)\n", checks);
		return 0;
	}
	printf("%d/%d CHECKS FAILED\n", failures, checks);
	return 1;
}
