// ConfigLoaderPortable.cpp : tinyxml2 port of the MSXML6/COM config loading in
// ShepherdingSimC_V1.cpp (Milestone M0.5). Same keys, same globals, same semantics.
//
// The original loader walks the document positionally: "//config[k]/*" selects the k-th
// <config> element in the file and get_item(i) its i-th element child (comments are not
// element children and are skipped, exactly as MSXML did). Boolean flags are compared
// against the exact string "1" (wcscmp), so surrounding whitespace makes a flag false;
// numeric fields are parsed with _wtoi / stof, which skip leading whitespace. Both
// behaviours are reproduced here.

#include "ConfigLoaderPortable.h"
#include "tinyxml2.h"
#include <cstdio>
#include <cstdlib>
#include <string>

// Global variable definitions, mirroring ShepherdingSimC_V1.cpp (same names, same defaults).
int randomNumberSeed = 0;
int screenWidthPixels = 800, screenHeightPixels = 800;
int MaximumNumSteps = 1000;
bool visualizationON = false;
bool CircularPathPlanningON = false;
int R3 = 4;
int R2 = 4;
int DrivingPositionEq = 1;
int CollectingPositionEq = 1;
int SheepNeignborhoodSelection = 1;
int ModulationDecayFactor = 1;
int fNequation = 1;
int ForceRegulated = 1;
bool StallingON = false;
float StallingDistance = 0;

int FieldLength = 100;		//Actual Length and Width of Field
int simScreenWidth = 120;	//Actual Length and Width of window including surrounding the field
int simSpeed = 100;			//wait x visualisation step before calling simulation update
int goalRadius = 10;
int WindowMarginSize = 0;

int gLocX = 0;
int gLocY = 0;

int sheepInitializationStartingX, sheepInitializationStartingY, sheepInitializationXRange, sheepInitializationYRange;
std::string sheepInitializationPattern;
int sheepDogInitializationStartingX, sheepDogInitializationStartingY, sheepDogInitializationXRange, sheepDogInitializationYRange;

int N = 10;					//(1--201)           & Cardinality of Pi
int M = 1;					// (1--20)            & Cardinality of B
bool paddockON = false;
int paddockLength = N + 10;
int paddockWidth = N + 10;
float R_pi_beta = 65;		// (65u)			& pi sensing range for beta
float Ra_pi_pi = 2;			// (2u)				& pi collision avoidance range for pi
float Rs_pi_pi = 20;		// (20u)			& pi sensing range for pi
float R_beta_beta = 10;		// (2u)				& beta sensing range for beta
float R_beta_pi = 65;		//					& beta sensing range for pi
int card_Omega_pi_pi = N - 1;	//maximum N-1
int card_Omega_beta_pi = N;		//maximum N
float W_pi_pi = 2;			// (2)				& pi repulsion strength from pi
float W_beta_beta = 2;
float W_pi_beta = 1;		// (1)				& pi repulsion strength from beta
float W_pi_Lambda = 1.05;	// (1.05)			& pi attraction strength to Lambda
float W_pi_upsilon = 0.5;	// (0.5)			& Strength of pi previous direction
float W_e_pi_i = 0.3;		// (0.3)			& Strength of sheep pi_j angular noise
float W_e_beta_j = 0.3;		// (0.3)			& Strength of shepherd beta_j angular noise
float S_t_beta_j = 2;		//					& Speed of beta at time t
float eta = 0.05;			//(0.05)			& Probability of moving per time step while grazing
float obstaclesRadius = 1;
float obstaclesDensity = 0;

bool CollisionAvoidanceOpponentsForceON = true;
bool CollisionAvoidanceFriendsForceON = true;
bool AttractionBehaviorForceON = true;
bool CollisionAvoidanceStaticObstaclesForceON = true;
bool JitteringForceON = true;
bool scaleForceVisualization = true;

// Adversarial extension defaults (all off / neutral; REQUIREMENTS.md Section 4).
int AdversarialMode = 0;
int AdversarialWeights = 0;
float AOI_x = -1, AOI_y = -1;      // -1: compute centre of top third of the field
float W_pi_I = 0.25f;
float Intercept_dist = 5.0f;
float Patrol_radius = 5.0f;
float Patrol_step = 0.3f;
float Patrol_noise = 0.1f;
int LookAheadController = 1;
float MetricWeight_M1 = 1, MetricWeight_M2 = 1, MetricWeight_M3 = 1;
int Experiment_conditions = 27;
int Experiment_steps = 200;
int Experiment_base_seed = 1000;
float Experiment_startX[3] = { 2, 15, 28 };
float Experiment_startY = 2;
float Experiment_boxW[3] = { 10, 15, 20 };
float Experiment_boxH[3] = { 10, 15, 20 };
float Experiment_dogX = 22.5f, Experiment_dogY = 34, Experiment_dogRange = 5;

namespace {

using tinyxml2::XMLDocument;
using tinyxml2::XMLElement;

// "//config[k]" : the k-th <config> element in the document (1-based, as in XPath).
// All <config> elements sit under the root, so scanning the root's children matches
// the MSXML document-wide search for this file layout.
const XMLElement* selectConfig(const XMLDocument& doc, int k)
{
	const XMLElement* root = doc.RootElement();
	if (!root) return nullptr;
	int count = 0;
	for (const XMLElement* e = root->FirstChildElement("config"); e; e = e->NextSiblingElement("config"))
	{
		count++;
		if (count == k) return e;
	}
	return nullptr;
}

// get_item(i) : the i-th element child (0-based). Comments are not elements.
const XMLElement* item(const XMLElement* config, int i)
{
	if (!config) return nullptr;
	int count = 0;
	for (const XMLElement* e = config->FirstChildElement(); e; e = e->NextSiblingElement())
	{
		if (count == i) return e;
		count++;
	}
	return nullptr;
}

// get_text : the node's text, whitespace preserved (tinyxml2 default mode).
std::string text(const XMLElement* e)
{
	if (!e || !e->GetText()) return std::string();
	return std::string(e->GetText());
}

int toInt(const std::string& s)                 // _wtoi semantics
{
	return std::atoi(s.c_str());
}

float toFloat(const std::string& s)             // std::stof semantics
{
	return std::strtof(s.c_str(), nullptr);
}

bool isOne(const std::string& s)                // wcscmp(value, L"1") == 0 semantics
{
	return s == "1";
}

} // namespace

bool loadConfigurationPortable(const std::string& filename)
{
	XMLDocument doc;
	if (doc.LoadFile(filename.c_str()) != tinyxml2::XML_SUCCESS)
	{
		printf("Failed to load DOM from config.xml. %s\n", doc.ErrorStr());
		return false;
	}
	printf("XML was successfully loaded\n");

	const XMLElement* cfg;

	//Reading Reproducibility configuration
	cfg = selectConfig(doc, 1);
	randomNumberSeed = toInt(text(item(cfg, 0)));

	//Reading Visualisation configuration
	cfg = selectConfig(doc, 2);
	visualizationON = isOne(text(item(cfg, 0)));

	//Reading Field Configuration
	cfg = selectConfig(doc, 3);
	FieldLength = toInt(text(item(cfg, 0)));
	WindowMarginSize = toInt(text(item(cfg, 1)));
	simScreenWidth = FieldLength + 2 * WindowMarginSize;

	//Reading Goal Location
	cfg = selectConfig(doc, 4);
	gLocX = toInt(text(item(cfg, 0)));
	gLocY = toInt(text(item(cfg, 1)));

	//Reading "Paddock Dimension"
	cfg = selectConfig(doc, 5);
	paddockON = isOne(text(item(cfg, 0)));
	goalRadius = toInt(text(item(cfg, 1)));
	paddockLength = toInt(text(item(cfg, 2)));
	paddockWidth = toInt(text(item(cfg, 3)));

	//Reading "Shepherding Model Configuration"
	cfg = selectConfig(doc, 6);
	DrivingPositionEq = toInt(text(item(cfg, 0)));
	CollectingPositionEq = toInt(text(item(cfg, 1)));
	fNequation = toInt(text(item(cfg, 2)));
	StallingON = isOne(text(item(cfg, 3)));
	StallingDistance = toFloat(text(item(cfg, 4)));
	CircularPathPlanningON = isOne(text(item(cfg, 5)));
	SheepNeignborhoodSelection = toInt(text(item(cfg, 6)));
	R3 = toInt(text(item(cfg, 7)));
	R2 = toFloat(text(item(cfg, 8)));           // original parses R2 with stof into an int
	ForceRegulated = toInt(text(item(cfg, 9)));
	ModulationDecayFactor = toInt(text(item(cfg, 10)));

	//Reading "Shepherding Parameters"
	cfg = selectConfig(doc, 7);
	N = toInt(text(item(cfg, 0)));
	M = toInt(text(item(cfg, 1)));
	R_pi_beta = toFloat(text(item(cfg, 2)));
	Ra_pi_pi = toFloat(text(item(cfg, 3)));
	Rs_pi_pi = toFloat(text(item(cfg, 4)));
	card_Omega_pi_pi = toInt(text(item(cfg, 5)));
	card_Omega_beta_pi = toInt(text(item(cfg, 6)));
	W_pi_pi = toFloat(text(item(cfg, 7)));
	W_pi_beta = toFloat(text(item(cfg, 8)));
	W_pi_Lambda = toFloat(text(item(cfg, 9)));
	W_pi_upsilon = toFloat(text(item(cfg, 10)));
	W_e_pi_i = toFloat(text(item(cfg, 11)));
	W_e_beta_j = toFloat(text(item(cfg, 12)));
	S_t_beta_j = toFloat(text(item(cfg, 13)));
	eta = toFloat(text(item(cfg, 14)));
	R_beta_beta = toFloat(text(item(cfg, 15)));
	R_beta_pi = toFloat(text(item(cfg, 16)));
	W_beta_beta = toFloat(text(item(cfg, 17)));

	//Reading Sheep Initialization
	cfg = selectConfig(doc, 8);
	sheepInitializationStartingX = toInt(text(item(cfg, 0)));
	sheepInitializationStartingY = toInt(text(item(cfg, 1)));
	sheepInitializationXRange = toInt(text(item(cfg, 2)));
	sheepInitializationYRange = toInt(text(item(cfg, 3)));
	sheepInitializationPattern = text(item(cfg, 4));

	//Reading SheepDog Initialization
	cfg = selectConfig(doc, 9);
	sheepDogInitializationStartingX = toInt(text(item(cfg, 0)));
	sheepDogInitializationStartingY = toInt(text(item(cfg, 1)));
	sheepDogInitializationXRange = toInt(text(item(cfg, 2)));
	sheepDogInitializationYRange = toInt(text(item(cfg, 3)));

	//Reading Maximum Number of Steps
	cfg = selectConfig(doc, 10);
	MaximumNumSteps = toInt(text(item(cfg, 0)));

	//Reading Obstacles
	cfg = selectConfig(doc, 11);
	obstaclesDensity = toFloat(text(item(cfg, 0)));
	obstaclesRadius = toFloat(text(item(cfg, 1)));

	//Reading the optional Adversarial section (by category attribute and element name,
	//so configs without it parse exactly as before).
	for (const XMLElement* e = doc.RootElement()->FirstChildElement("config"); e; e = e->NextSiblingElement("config"))
	{
		const char* cat = e->Attribute("category");
		if (!cat || std::string(cat) != "Adversarial") continue;
		for (const XMLElement* c = e->FirstChildElement(); c; c = c->NextSiblingElement())
		{
			std::string k = c->Name();
			std::string v = text(c);
			if (k == "AdversarialMode") AdversarialMode = toInt(v);
			else if (k == "AdversarialWeights") AdversarialWeights = toInt(v);
			else if (k == "AOI_x") AOI_x = toFloat(v);
			else if (k == "AOI_y") AOI_y = toFloat(v);
			else if (k == "W_pi_I") W_pi_I = toFloat(v);
			else if (k == "Intercept_dist") Intercept_dist = toFloat(v);
			else if (k == "Patrol_radius") Patrol_radius = toFloat(v);
			else if (k == "Patrol_step") Patrol_step = toFloat(v);
			else if (k == "Patrol_noise") Patrol_noise = toFloat(v);
			else if (k == "LookAheadController") LookAheadController = toInt(v);
			else if (k == "MetricWeight_M1") MetricWeight_M1 = toFloat(v);
			else if (k == "MetricWeight_M2") MetricWeight_M2 = toFloat(v);
			else if (k == "MetricWeight_M3") MetricWeight_M3 = toFloat(v);
			else if (k == "Experiment_conditions") Experiment_conditions = toInt(v);
			else if (k == "Experiment_steps") Experiment_steps = toInt(v);
			else if (k == "Experiment_base_seed") Experiment_base_seed = toInt(v);
			else if (k == "Experiment_startY") Experiment_startY = toFloat(v);
			else if (k == "Experiment_dogX") Experiment_dogX = toFloat(v);
			else if (k == "Experiment_dogY") Experiment_dogY = toFloat(v);
			else if (k == "Experiment_dogRange") Experiment_dogRange = toFloat(v);
			else if (k == "Experiment_startX" || k == "Experiment_boxW" || k == "Experiment_boxH")
			{
				float* dst = (k == "Experiment_startX") ? Experiment_startX
					: (k == "Experiment_boxW") ? Experiment_boxW : Experiment_boxH;
				char* p = nullptr;
				const char* s = v.c_str();
				for (int i = 0; i < 3; i++) { dst[i] = std::strtof(s, &p); s = p; }
			}
		}
		printf("Adversarial section loaded: AdversarialMode=%d AdversarialWeights=%d LookAhead=%d\n",
			AdversarialMode, AdversarialWeights, LookAheadController);
	}
	if (AOI_x < 0) AOI_x = FieldLength / 2.0f;          // centre of the top third
	if (AOI_y < 0) AOI_y = FieldLength * 5.0f / 6.0f;

	printf("Random Numbers Speed: %d\n", randomNumberSeed);
	printf("Visualisation : %s\n", visualizationON ? "true" : "false");
	printf("Simulation Speed: %d\n", simSpeed);
	printf("ScreenWidth in Pixels: %d\n", screenWidthPixels);
	printf("Screen Height in Pixels: %d\n", screenHeightPixels);
	printf("Field Length and Width: %d\n", FieldLength);
	printf("Window Margin Size: %d\n", WindowMarginSize);
	printf("Goal LocationX: %d\n", gLocX);
	printf("Goal LocationT: %d\n", gLocY);
	printf("Paddock On : %s\n", paddockON ? "true" : "false");
	if (paddockON)
	{
		printf("Paddock Length: %d\n", paddockLength);
		printf("paddock Width: %d\n", paddockWidth);
	}
	else
	{
		printf("Goal Radius: %d\n", goalRadius);
	}

	printf("N: %d\n", N);
	printf("M: %d\n", M);
	printf("R_pi_beta: %.2f\n", R_pi_beta);
	printf("Ra_pi_pi: %.2f\n", Ra_pi_pi);
	printf("Rs_pi_pi: %.2f\n", Rs_pi_pi);
	printf("card_Omega_pi_pi: %d\n", card_Omega_pi_pi);
	printf("card_Omega_beta_pi: %d\n", card_Omega_beta_pi);
	printf("W_pi_pi: %.2f\n", W_pi_pi);
	printf("W_pi_beta: %.2f\n", W_pi_beta);
	printf("W_pi_Lambda: %.2f\n", W_pi_Lambda);
	printf("W_pi_upsilon: %.2f\n", W_pi_upsilon);
	printf("W_e_pi_i: %.2f\n", W_e_pi_i);
	printf("W_e_beta_j: %.2f\n", W_e_beta_j);
	printf("S_t_beta_j: %.2f\n", S_t_beta_j);
	printf("eta: %.2f\n", eta);
	printf("R_beta_beta: %.2f\n", R_beta_beta);
	printf("R_beta_pi: %.2f\n", R_beta_pi);
	printf("W_beta_beta: %.2f\n", W_beta_beta);
	printf("DrivingPositionEq: %d\n", DrivingPositionEq);
	printf("CollectingPositionEq: %d\n", CollectingPositionEq);
	printf("fNequation: %d\n", fNequation);
	printf("ForceRegulated: %d\n", ForceRegulated);
	printf("SheepNeignborhoodSelection: %d\n", SheepNeignborhoodSelection);
	printf("ModulationDecayFactor: %d\n", ModulationDecayFactor);
	printf("Circular Path Planning On : %s\n", CircularPathPlanningON ? "true" : "false");
	printf("StallingON : %s\n", StallingON ? "true" : "false");
	printf("StallingDistance : %.2f\n", StallingDistance);
	printf("R2 : %d\n", R2);
	printf("R3 : %d\n", R3);
	printf("Sheep Initialization %d ,%d, %d, %d, %s\n", sheepInitializationStartingX, sheepInitializationStartingY, sheepInitializationXRange, sheepInitializationYRange, sheepInitializationPattern.c_str());
	printf("SheepDog Initialization %d ,%d, %d, %d \n", sheepDogInitializationStartingX, sheepDogInitializationStartingY, sheepDogInitializationXRange, sheepDogInitializationYRange);

	return true;
}

bool loadGraphicsPortable(const std::string& filename)
{
	XMLDocument doc;
	if (doc.LoadFile(filename.c_str()) != tinyxml2::XML_SUCCESS)
	{
		printf("Failed to load DOM from config.xml. %s\n", doc.ErrorStr());
		return false;
	}
	printf("XML was successfully loaded\n");

	const XMLElement* cfg;

	//Reading simSpeed
	cfg = selectConfig(doc, 1);
	simSpeed = toInt(text(item(cfg, 0)));

	//Reading Screen Configuration
	cfg = selectConfig(doc, 2);
	screenWidthPixels = toInt(text(item(cfg, 0)));
	screenHeightPixels = toInt(text(item(cfg, 1)));

	//Reading Forces Visualization Configuration
	cfg = selectConfig(doc, 3);
	CollisionAvoidanceOpponentsForceON = toInt(text(item(cfg, 0))) == 1;
	CollisionAvoidanceFriendsForceON = toInt(text(item(cfg, 1))) == 1;
	AttractionBehaviorForceON = toInt(text(item(cfg, 2))) == 1;
	CollisionAvoidanceStaticObstaclesForceON = toInt(text(item(cfg, 3))) == 1;
	JitteringForceON = toInt(text(item(cfg, 4))) == 1;
	scaleForceVisualization = toInt(text(item(cfg, 5))) == 1;

	return true;
}
