#include "stdafx.h"
#include "AdversarialBehaviors.h"
#include "Environment.h"
#include "Agents.h"
#include "SheepDogAgent.h"
#include "Flock.h"
#include <cmath>
#include <random>

// The base Behaviors.cpp defines a file-scope env reference; use a local getter here
// to avoid a second global with the same name.
static Environment& advEnv() { return Environment::getInstance(); }

AOIAttraction::AOIAttraction(Agent* agent)
{
	this->agent = agent;
	this->Weight = advEnv().W_pi_I;
	this->behaviorType = "AOIAttraction";
	this->magnitude = 0;
}

Vector2f AOIAttraction::GetForce()
{
	Vector2f force = Vector2f();
	Environment& env = advEnv();
	this->magnitude = this->agent->position_t.dist(env.AOI);
	if (this->magnitude > 0)
	{
		force = (env.AOI - this->agent->position_t) / this->magnitude; // unit(sheep -> AOI)
	}
	return force;
}

float AOIAttraction::GetMagnitude()
{
	return this->magnitude;
}

Intercepting::Intercepting(Agent* agent)
{
	this->agent = agent;
	this->Weight = 1;
	this->behaviorType = "Intercepting";
	this->magnitude = 0;
}

Vector2f Intercepting::GetInterceptTarget()
{
	Environment& env = advEnv();
	// threat = argmin_i ||p_i - AOI|| over the attacker flock
	Vector2f threat = Vector2f();
	float bestDist = -1;
	for (int i = 0; i < env.sheepFlock->size(); i++)
	{
		float d = (*env.sheepFlock)[i]->position_t.dist(env.AOI);
		if (bestDist < 0 || d < bestDist)
		{
			bestDist = d;
			threat = (*env.sheepFlock)[i]->position_t;
		}
	}
	Vector2f target = env.AOI;
	if (bestDist > 0)
	{
		target = env.AOI + (threat - env.AOI) / bestDist * env.Intercept_dist; // A + unit(A->threat)*intercept_dist
	}
	return target;
}

Vector2f Intercepting::GetForce()
{
	Vector2f force = Vector2f();
	Vector2f target = GetInterceptTarget();
	this->magnitude = this->agent->position_t.dist(target);
	if (this->magnitude > 0)
	{
		force = (target - this->agent->position_t) / this->magnitude; // unit(dog -> target)
	}
	return force;
}

float Intercepting::GetMagnitude()
{
	return this->magnitude;
}

Patrolling::Patrolling(Agent* agent)
{
	this->agent = agent;
	this->Weight = 1;
	this->behaviorType = "Patrolling";
	this->magnitude = 0;
}

Vector2f Patrolling::GetPatrolTarget() const
{
	Environment& env = advEnv();
	// Agent has no virtual functions, so follow the codebase idiom of dispatching on
	// the agentType string instead of dynamic_cast.
	SheepDogAgent* dog = (this->agent->agentType == "SheepDogAgent") ? static_cast<SheepDogAgent*>(this->agent) : nullptr;
	float phi = dog ? dog->patrolPhi : 0;
	return env.AOI + Vector2f(std::cos(phi), std::sin(phi)) * env.Patrol_radius;
}

Vector2f Patrolling::GetForce()
{
	Environment& env = advEnv();
	SheepDogAgent* dog = (this->agent->agentType == "SheepDogAgent") ? static_cast<SheepDogAgent*>(this->agent) : nullptr;
	if (dog)
	{
		std::uniform_real_distribution<float> noise(-env.Patrol_noise, env.Patrol_noise);
		dog->patrolPhi += env.Patrol_step + noise(env.patrolRng);
	}
	Vector2f target = GetPatrolTarget();
	Vector2f force = Vector2f();
	this->magnitude = this->agent->position_t.dist(target);
	if (this->magnitude > 0)
	{
		force = (target - this->agent->position_t) / this->magnitude; // unit(dog -> target)
	}
	return force;
}

float Patrolling::GetMagnitude()
{
	return this->magnitude;
}
