// Experiment.cpp : 27-condition x 200-step adversarial experiment harness.
//
// The 27 conditions are a documented reconstruction (the paper does not publish them;
// REQUIREMENTS.md Section 5.2, docs/decisions.md): 3 attacker-box anchors x 3 widths x
// 3 heights, attackers low in the field with Pattern P6, the defender uniform in a 5x5
// square next to the AOI. Every run is seeded Experiment_base_seed + run_index.

#include "Experiment.h"
#include "AdversarialController.h"
#include "ConfigLoaderPortable.h"
#include "Sim.h"
#include "Environment.h"
#include "Flock.h"
#include "SheepAgent.h"
#include "SheepDogAgent.h"
#include <cmath>
#include <cstdio>
#include <fstream>
#include <vector>
#include <string>
#include <sys/stat.h>

namespace {

struct StepRecord
{
	int run, t;
	double M1, M2, M3, sigmaR, muOmega, thetaOmega;
	int clustered, anyWithin5, allBeyond20, defenderBetween, chosenBC;
};

// Table III style metrics on the committed (post-Move) real state.
StepRecord measureStep(int run, int t, int chosenBC)
{
	Environment& env = Environment::getInstance();
	StepRecord r{};
	r.run = run; r.t = t; r.chosenBC = chosenBC;

	std::vector<Vector2f> pos(env.sheepFlock->size());
	for (int i = 0; i < env.sheepFlock->size(); i++) pos[i] = (*env.sheepFlock)[i]->position_t;
	Vector2f dogPos = (*env.sheepDogFlock)[0]->position_t;

	AdversarialMetrics m = evaluateMetrics(pos, dogPos);
	r.M1 = m.M1; r.M2 = m.M2; r.M3 = m.M3;

	const double ax = env.AOI.x, ay = env.AOI.y;
	double gx = 0, gy = 0;
	for (auto& p : pos) { gx += p.x; gy += p.y; }
	gx /= pos.size(); gy /= pos.size();

	// sigma(R): std of attacker-to-AOI distances
	double sum = 0, sum2 = 0;
	int within5 = 0, beyond20 = 0;
	for (auto& p : pos)
	{
		double d = std::sqrt((p.x - ax) * (p.x - ax) + (p.y - ay) * (p.y - ay));
		sum += d; sum2 += d * d;
		if (d < 5) within5++;
		if (d > 20) beyond20++;
	}
	double meanD = sum / pos.size();
	r.sigmaR = std::sqrt(std::max(0.0, sum2 / pos.size() - meanD * meanD));
	r.anyWithin5 = (within5 > 0) ? 1 : 0;
	r.allBeyond20 = (beyond20 == (int)pos.size()) ? 1 : 0;

	// Clustering (A.8): all attackers within fN of the GCM; Omega = the stragglers.
	// mu(Omega): mean distance of unclustered attackers to the AOI, 0 when Omega empty.
	// theta(Omega): mean angle at the AOI between an unclustered attacker and the GCM,
	// 0 when Omega empty (docs/decisions.md).
	double v1x = gx - ax, v1y = gy - ay;
	double n1 = std::sqrt(v1x * v1x + v1y * v1y);
	int nOmega = 0;
	double muO = 0, thO = 0;
	for (auto& p : pos)
	{
		double dg = std::sqrt((p.x - gx) * (p.x - gx) + (p.y - gy) * (p.y - gy));
		if (dg > env.fN)
		{
			nOmega++;
			double dA = std::sqrt((p.x - ax) * (p.x - ax) + (p.y - ay) * (p.y - ay));
			muO += dA;
			double v2x = p.x - ax, v2y = p.y - ay;
			double n2 = std::sqrt(v2x * v2x + v2y * v2y);
			if (n1 > 0 && n2 > 0)
			{
				double c = (v1x * v2x + v1y * v2y) / (n1 * n2);
				thO += std::acos(std::min(1.0, std::max(-1.0, c)));
			}
		}
	}
	r.clustered = (nOmega == 0) ? 1 : 0;
	r.muOmega = nOmega ? muO / nOmega : 0.0;
	r.thetaOmega = nOmega ? thO / nOmega : 0.0;
	r.defenderBetween = (r.M3 < M_PI / 2) ? 1 : 0;
	return r;
}

void writeHeader(std::ofstream& f)
{
	f << "run,t,M1_gcm_aoi_dist,M2_angle_std,M3_defender_angle,sigmaR,muOmega,thetaOmega,"
	     "clustered,anyWithin5,allBeyond20,defenderBetween,chosenBC\n";
}

void writeRecord(std::ofstream& f, const StepRecord& r)
{
	f << r.run << "," << r.t << "," << r.M1 << "," << r.M2 << "," << r.M3 << ","
	  << r.sigmaR << "," << r.muOmega << "," << r.thetaOmega << ","
	  << r.clustered << "," << r.anyWithin5 << "," << r.allBeyond20 << ","
	  << r.defenderBetween << "," << (r.chosenBC + 1) << "\n";
}

// One adversarial run against an already-initialised Simulation/Environment.
// positions, when non-null, receives one row per step with the committed agent
// positions and the chosen BC, for trajectory replay tools.
void runLoop(Simulation* sim, int steps, int runIdx, std::ofstream& perStep, std::vector<StepRecord>& all,
	std::ofstream* positions = nullptr)
{
	Environment& env = Environment::getInstance();
	SheepDogAgent* dog = (*env.sheepDogFlock)[0];

	if (positions)
	{
		*positions << "t,dogX,dogY,chosenBC";
		for (int i = 0; i < env.sheepFlock->size(); i++) *positions << ",s" << i << "x,s" << i << "y";
		*positions << "\n";
	}

	for (int t = 1; t <= steps; t++)
	{
		env.currentTime = t;
		env.sheepFlock->CalcNewLoc();               // sheep react to state at t (base order)
		AdversarialStepInfo info = adversarialDogStep(dog);
		env.sheepFlock->Move();
		env.sheepDogFlock->Move();

		StepRecord r = measureStep(runIdx, t, info.chosenBC);
		writeRecord(perStep, r);
		all.push_back(r);

		if (positions)
		{
			*positions << t << "," << dog->position_t.x << "," << dog->position_t.y << "," << (info.chosenBC + 1);
			for (int i = 0; i < env.sheepFlock->size(); i++)
				*positions << "," << (*env.sheepFlock)[i]->position_t.x << "," << (*env.sheepFlock)[i]->position_t.y;
			*positions << "\n";
		}
	}
	(void)sim;
}

Simulation* initRun(int seed, int shX, int shY, int shW, int shH, const std::string& pattern)
{
	Simulation* sim = new Simulation();
	sim->init(seed, N, M, 0, 0, FieldLength, FieldLength,
		R_pi_beta, Ra_pi_pi, Rs_pi_pi, R_beta_beta, R_beta_pi,
		W_pi_pi, W_beta_beta, W_pi_beta, W_pi_Lambda, W_pi_upsilon, W_e_pi_i, W_e_beta_j,
		S_t_beta_j, eta, card_Omega_pi_pi, card_Omega_beta_pi,
		gLocX, gLocY, paddockLength, paddockWidth, false /*paddock off in experiment*/,
		false /*no circular path planning in the adversarial driver*/,
		StallingON, StallingDistance, R2, R3, goalRadius,
		ForceRegulated, fNequation, DrivingPositionEq, CollectingPositionEq,
		SheepNeignborhoodSelection, ModulationDecayFactor,
		shX, shY, shW, shH, pattern,
		(int)Experiment_dogX, (int)Experiment_dogY, (int)Experiment_dogRange, (int)Experiment_dogRange,
		obstaclesDensity, obstaclesRadius);
	applyAdversarialEnvSettings(seed);
	return sim;
}

struct Stat { double mean, sd; };
Stat meanStd(const std::vector<StepRecord>& v, double StepRecord::* f)
{
	double s = 0, s2 = 0;
	for (auto& r : v) { s += r.*f; s2 += (r.*f) * (r.*f); }
	double m = s / v.size();
	return { m, std::sqrt(std::max(0.0, s2 / v.size() - m * m)) };
}
double pct(const std::vector<StepRecord>& v, int StepRecord::* f)
{
	double s = 0;
	for (auto& r : v) s += r.*f;
	return 100.0 * s / v.size();
}

void writeSummary(const std::string& outDir, const std::vector<StepRecord>& all, int conditions)
{
	std::ofstream res(outDir + "/results.csv");
	res << "scope,mu_R_lambda_mean,mu_R_lambda_std,sigma_theta_mean,sigma_theta_std,"
	       "theta_beta_mean,theta_beta_std,sigma_R_mean,sigma_R_std,"
	       "mu_Omega_mean,mu_Omega_std,theta_Omega_mean,theta_Omega_std,"
	       "pct_anyWithin5,pct_allBeyond20,pct_defenderBetween,pct_clustered\n";

	auto emit = [&res](const std::string& scope, const std::vector<StepRecord>& v) {
		Stat a = meanStd(v, &StepRecord::M1), b = meanStd(v, &StepRecord::M2),
		     c = meanStd(v, &StepRecord::M3), d = meanStd(v, &StepRecord::sigmaR),
		     e = meanStd(v, &StepRecord::muOmega), f = meanStd(v, &StepRecord::thetaOmega);
		res << scope << "," << a.mean << "," << a.sd << "," << b.mean << "," << b.sd << ","
		    << c.mean << "," << c.sd << "," << d.mean << "," << d.sd << ","
		    << e.mean << "," << e.sd << "," << f.mean << "," << f.sd << ","
		    << pct(v, &StepRecord::anyWithin5) << "," << pct(v, &StepRecord::allBeyond20) << ","
		    << pct(v, &StepRecord::defenderBetween) << "," << pct(v, &StepRecord::clustered) << "\n";
	};

	for (int c = 0; c < conditions; c++)
	{
		std::vector<StepRecord> v;
		for (auto& r : all) if (r.run == c) v.push_back(r);
		if (!v.empty()) emit("cond" + std::to_string(c), v);
	}
	emit("pooled", all);

	// Behaviour usage: how often each BC was chosen, and each behaviour's summed
	// weight across chosen BCs.
	int bcCount[10] = { 0 };
	double usage[4] = { 0 };
	for (auto& r : all)
	{
		bcCount[r.chosenBC]++;
		for (int j = 0; j < 4; j++) usage[j] += kBehaviorCombinations[r.chosenBC][j];
	}
	std::ofstream use(outDir + "/behaviour_usage.csv");
	use << "BC,count,share_pct\n";
	for (int k = 0; k < 10; k++)
		use << "BC" << (k + 1) << "," << bcCount[k] << "," << 100.0 * bcCount[k] / all.size() << "\n";
	const char* names[4] = { "Driving", "Collecting", "Intercepting", "Patrolling" };
	use << "behaviour,weightSum,share_pct\n";
	double tot = 0; for (int j = 0; j < 4; j++) tot += usage[j];
	for (int j = 0; j < 4; j++)
		use << names[j] << "," << usage[j] << "," << (tot > 0 ? 100.0 * usage[j] / tot : 0) << "\n";
}

} // namespace

int runAdversarialSingle(const std::string& perStepPath)
{
	std::ofstream perStep(perStepPath);
	writeHeader(perStep);
	std::string positionsPath = perStepPath.substr(0, perStepPath.rfind('.')) + "_Positions.csv";
	std::ofstream positions(positionsPath);
	std::vector<StepRecord> all;
	Simulation* sim = initRun(randomNumberSeed,
		sheepInitializationStartingX, sheepInitializationStartingY,
		sheepInitializationXRange, sheepInitializationYRange, sheepInitializationPattern);
	runLoop(sim, MaximumNumSteps, 0, perStep, all, &positions);
	printf("Adversarial single run: %d steps logged to %s and %s\n",
		MaximumNumSteps, perStepPath.c_str(), positionsPath.c_str());
	return 0;
}

int runExperiment(const std::string& outDir)
{
	mkdir(outDir.c_str(), 0755);
	std::ofstream perStep(outDir + "/perstep.csv");
	writeHeader(perStep);
	std::vector<StepRecord> all;

	int conditions = Experiment_conditions;
	for (int c = 0; c < conditions; c++)
	{
		int seed = Experiment_base_seed + c;
		int shX = (int)Experiment_startX[c / 9];
		int shW = (int)Experiment_boxW[(c / 3) % 3];
		int shH = (int)Experiment_boxH[c % 3];
		Simulation* sim = initRun(seed, shX, (int)Experiment_startY, shW, shH, "P6");
		printf("condition %2d: seed=%d sheepBox=(%d,%d,%dx%d) dog=(%d,%d,%dx%d)\n",
			c, seed, shX, (int)Experiment_startY, shW, shH,
			(int)Experiment_dogX, (int)Experiment_dogY, (int)Experiment_dogRange, (int)Experiment_dogRange);
		runLoop(sim, Experiment_steps, c, perStep, all);
	}

	writeSummary(outDir, all, conditions);
	printf("Experiment complete: %d conditions x %d steps -> %s/{perstep,results,behaviour_usage}.csv\n",
		conditions, Experiment_steps, outDir.c_str());
	return 0;
}
