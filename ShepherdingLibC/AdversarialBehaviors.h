// AdversarialBehaviors.h : new behaviours for the adversarial patrolling extension
// (Zhou, El-Fiqi, Hussein, IEEE SMC 2024). Additions only; the base behaviours in
// Behaviors.h are untouched. Everything here is inert unless AdversarialMode=1.

#pragma once
#ifndef BEHAVIORS_EXPORT
#define ADVBEHAVIORS_API __declspec(dllexport)
#else
#define ADVBEHAVIORS_API __declspec(dllimport)
#endif

#include "Behaviors.h"
#include "Vector2.h"

// Sheep attraction to the Area of Interest: W_pi_I * unit(sheep -> AOI).
// Added to the sheep behaviour list only when AdversarialMode=1.
class ADVBEHAVIORS_API AOIAttraction : public Behavior
{
public:
	AOIAttraction(Agent* agent);
	Vector2f GetForce();
	float GetMagnitude();
};

// Sheepdog Intercepting behaviour (REQUIREMENTS.md A.3): the threat is the attacker
// closest to the AOI (ground-truth flock, see docs/decisions.md); the target is the
// point Intercept_dist from the AOI on the segment toward the threat. Unit force.
class ADVBEHAVIORS_API Intercepting : public Behavior
{
public:
	Intercepting(Agent* agent);
	Vector2f GetForce();
	float GetMagnitude();
	Vector2f GetInterceptTarget();   // exposed for unit test U3
};

// Sheepdog Patrolling behaviour (REQUIREMENTS.md A.4): maintains a phase on the dog,
// advances it by Patrol_step plus uniform noise from the dedicated patrolRng substream,
// and steers toward the point at Patrol_radius on the circle about the AOI. Unit force.
class ADVBEHAVIORS_API Patrolling : public Behavior
{
public:
	Patrolling(Agent* agent);
	Vector2f GetForce();             // advances the phase; call once per (virtual or real) step
	float GetMagnitude();
	Vector2f GetPatrolTarget() const; // target for the current phase, no advance (U4)
};
