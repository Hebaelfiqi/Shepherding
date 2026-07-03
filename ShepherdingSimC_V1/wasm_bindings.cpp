// wasm_bindings.cpp : WebAssembly frontend for the shepherding library (web-simulator).
//
// A third frontend beside the Visual Studio/SDL2 build and the headless CLI: the same
// unchanged ShepherdingLibC physics compiled to wasm, driven interactively from a web
// page. Parameters arrive as function arguments instead of Config.xml; positions are
// read from memory each step instead of the CSV. No library file is modified.
//
// Exports (plain C ABI, consumed with cwrap/HEAPF32):
//   sim_create(...)      initialise a run from explicit parameters (replaces the XML)
//   sim_step()           advance one timestep; returns 1 while running, 0 when finished
//   sim_time()           current timestep
//   sim_goal_found()     1 once all sheep are within GoalRadius of the goal
//   sim_num_dogs/sheep() agent counts
//   sim_positions()      float buffer [dog0.x, dog0.y, ..., sheep0.x, sheep0.y, ...]

#include <emscripten.h>
#include <string>
#include <vector>

#include "Sim.h"
#include "Environment.h"
#include "Flock.h"
#include "SheepAgent.h"
#include "SheepDogAgent.h"
#include "Behaviors.h"

static Simulation* sim = nullptr;
static int maxSteps = 2000;
static std::vector<float> posBuf;

// The base loop rebuilds each agent's behaviour list every step without freeing the
// previous one; a native process reclaims everything at exit, but a long-lived browser
// tab must reclaim as it goes. Frontend-side cleanup, identical in spirit to the
// experiment driver on the adversarial branch; the library is untouched.
static void freeBehaviors()
{
	Environment& env = Environment::getInstance();
	if (env.sheepFlock)
		for (int i = 0; i < env.sheepFlock->size(); i++)
		{
			for (Behavior* b : (*env.sheepFlock)[i]->agentBehaviors) delete b;
			(*env.sheepFlock)[i]->agentBehaviors.clear();
		}
	if (env.sheepDogFlock)
		for (int i = 0; i < env.sheepDogFlock->size(); i++)
		{
			for (Behavior* b : (*env.sheepDogFlock)[i]->agentBehaviors) delete b;
			(*env.sheepDogFlock)[i]->agentBehaviors.clear();
		}
}

static void freeAgents()
{
	Environment& env = Environment::getInstance();
	freeBehaviors();
	if (env.sheepFlock)
	{
		for (int i = 0; i < env.sheepFlock->size(); i++) delete (*env.sheepFlock)[i];
		delete env.sheepFlock;
		env.sheepFlock = nullptr;
	}
	if (env.sheepDogFlock)
	{
		for (int i = 0; i < env.sheepDogFlock->size(); i++) delete (*env.sheepDogFlock)[i];
		delete env.sheepDogFlock;
		env.sheepDogFlock = nullptr;
	}
}

extern "C" {

EMSCRIPTEN_KEEPALIVE
void sim_create(
	int seed, int nSheep, int nDogs, int fieldLength,
	float R_pi_beta, float Ra_pi_pi, float Rs_pi_pi, float R_beta_beta, float R_beta_pi,
	float W_pi_pi, float W_beta_beta, float W_pi_beta, float W_pi_Lambda,
	float W_pi_upsilon, float W_e_pi_i, float W_e_beta_j,
	float S_t_beta_j, float eta,
	int card_Omega_pi_pi, int card_Omega_beta_pi,
	int goalX, int goalY, int goalRadius,
	int circularPathPlanningON, int stallingON, float stallingDistance,
	int R2, int R3, int forceRegulated, int fNequation,
	int drivingPositionEq, int collectingPositionEq, int sheepNeighborhoodSelection,
	int modulationDecayFactor,
	int sheepX, int sheepY, int sheepW, int sheepH, int patternId,
	int dogX, int dogY, int dogW, int dogH,
	int maximumSteps)
{
	Environment& env = Environment::getInstance();

	// Fresh run in a persistent process: reclaim the previous run's agents and reset
	// the shared tables the flock constructors append to.
	freeAgents();
	env.SheepDogRoster.clear();
	env.sheepdogsSharedCollectingKnowledge.clear();
	env.sheepdogsSharedDrivingKnowledge.clear();
	env.coveringPoints.clear();
	env.openCoveringTask = false;
	delete sim;

	maxSteps = maximumSteps;
	sim = new Simulation();
	sim->init(seed, nSheep, nDogs, 0, 0, fieldLength, fieldLength,
		R_pi_beta, Ra_pi_pi, Rs_pi_pi, R_beta_beta, R_beta_pi,
		W_pi_pi, W_beta_beta, W_pi_beta, W_pi_Lambda, W_pi_upsilon, W_e_pi_i, W_e_beta_j,
		S_t_beta_j, eta, card_Omega_pi_pi, card_Omega_beta_pi,
		goalX, goalY, 30, 30, false /*paddock off, goal radius mode as in the paper*/,
		circularPathPlanningON != 0, stallingON != 0, stallingDistance,
		R2, R3, goalRadius, forceRegulated, fNequation,
		drivingPositionEq, collectingPositionEq, sheepNeighborhoodSelection,
		modulationDecayFactor,
		sheepX, sheepY, sheepW, sheepH, "P" + std::to_string(patternId),
		dogX, dogY, dogW, dogH,
		0.0f /*no obstacles in the IEEE Access single-dog design*/, 1.0f);
}

EMSCRIPTEN_KEEPALIVE
int sim_step()
{
	if (!sim) return 0;
	if (sim->goalFound || sim->timestep >= maxSteps) return 0;
	sim->update();
	freeBehaviors();      // keep browser memory flat; lists are rebuilt next step
	return (!sim->goalFound && sim->timestep < maxSteps) ? 1 : 0;
}

EMSCRIPTEN_KEEPALIVE int sim_time() { return sim ? sim->timestep : 0; }
EMSCRIPTEN_KEEPALIVE int sim_goal_found() { return (sim && sim->goalFound) ? 1 : 0; }

EMSCRIPTEN_KEEPALIVE int sim_num_dogs()
{
	Environment& env = Environment::getInstance();
	return env.sheepDogFlock ? (int)env.sheepDogFlock->size() : 0;
}

EMSCRIPTEN_KEEPALIVE int sim_num_sheep()
{
	Environment& env = Environment::getInstance();
	return env.sheepFlock ? (int)env.sheepFlock->size() : 0;
}

EMSCRIPTEN_KEEPALIVE
float* sim_positions()
{
	Environment& env = Environment::getInstance();
	posBuf.clear();
	if (env.sheepDogFlock)
		for (int i = 0; i < env.sheepDogFlock->size(); i++)
		{
			posBuf.push_back((*env.sheepDogFlock)[i]->position_t.x);
			posBuf.push_back((*env.sheepDogFlock)[i]->position_t.y);
		}
	if (env.sheepFlock)
		for (int i = 0; i < env.sheepFlock->size(); i++)
		{
			posBuf.push_back((*env.sheepFlock)[i]->position_t.x);
			posBuf.push_back((*env.sheepFlock)[i]->position_t.y);
		}
	return posBuf.data();
}

} // extern "C"
