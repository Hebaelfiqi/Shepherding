// ConfigLoaderPortable.h : portable (tinyxml2) replacement for the MSXML6/COM config
// loading in ShepherdingSimC_V1.cpp, for the headless Linux build (Milestone M0.5).
//
// It fills the exact same global variables from the exact same config keys, using the
// same positional parsing (k-th <config> element, i-th element child) as the original
// loadDOMConfiguration / loadDOMGraphics. The globals below mirror the definitions at
// the top of ShepherdingSimC_V1.cpp, which is excluded from the headless target.

#pragma once
#include <string>

extern int randomNumberSeed;
extern int screenWidthPixels, screenHeightPixels;
extern int MaximumNumSteps;
extern bool visualizationON;
extern bool CircularPathPlanningON;
extern int R3;
extern int R2;
extern int DrivingPositionEq;
extern int CollectingPositionEq;
extern int SheepNeignborhoodSelection;
extern int ModulationDecayFactor;
extern int fNequation;
extern int ForceRegulated;
extern bool StallingON;
extern float StallingDistance;

extern int FieldLength;
extern int simScreenWidth;
extern int simSpeed;
extern int goalRadius;
extern int WindowMarginSize;

extern int gLocX;
extern int gLocY;

extern int sheepInitializationStartingX, sheepInitializationStartingY, sheepInitializationXRange, sheepInitializationYRange;
extern std::string sheepInitializationPattern;
extern int sheepDogInitializationStartingX, sheepDogInitializationStartingY, sheepDogInitializationXRange, sheepDogInitializationYRange;

extern int N;
extern int M;
extern bool paddockON;
extern int paddockLength;
extern int paddockWidth;
extern float R_pi_beta;
extern float Ra_pi_pi;
extern float Rs_pi_pi;
extern float R_beta_beta;
extern float R_beta_pi;
extern int card_Omega_pi_pi;
extern int card_Omega_beta_pi;
extern float W_pi_pi;
extern float W_beta_beta;
extern float W_pi_beta;
extern float W_pi_Lambda;
extern float W_pi_upsilon;
extern float W_e_pi_i;
extern float W_e_beta_j;
extern float S_t_beta_j;
extern float eta;
extern float obstaclesRadius;
extern float obstaclesDensity;

extern bool CollisionAvoidanceOpponentsForceON;
extern bool CollisionAvoidanceFriendsForceON;
extern bool AttractionBehaviorForceON;
extern bool CollisionAvoidanceStaticObstaclesForceON;
extern bool JitteringForceON;
extern bool scaleForceVisualization;

// Portable counterparts of loadDOMConfiguration / loadDOMGraphics. Return true on a
// successful parse; on failure they print a message and leave the defaults in place
// (mirroring the original, which continued with defaults after a COM parse error).
bool loadConfigurationPortable(const std::string& filename);
bool loadGraphicsPortable(const std::string& filename);
