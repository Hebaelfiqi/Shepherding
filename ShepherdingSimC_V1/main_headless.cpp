// main_headless.cpp : headless Linux entry point (Milestone M0.5). No SDL, no COM.
//
// Mirrors the non-visualisation branch of the original main() in ShepherdingSimC_V1.cpp:
// load the config (portable tinyxml2 loader), open the same output files, run the CLI
// simulation loop (Sim.cpp / SupportingCalc.cpp unchanged), stream per-step CSV.
// The Visualisation flag in the config is ignored: this target is headless by definition
// and always takes the CLI path.

#include <iostream>
#include <fstream>
#include <string>

#include "CLI.h"
#include "Environment.h"
#include "ConfigLoaderPortable.h"
#include "Experiment.h"

static void WriteOutFilesHeadless(std::ofstream& outputHeader_file, std::ofstream& outputConfigfile)
{
	//write config out (same fields and order as WriteOutFiles in ShepherdingSimC_V1.cpp)
	outputConfigfile << "Random Numbers Seed : " << randomNumberSeed << std::endl;
	outputConfigfile << "Visualisation : " << visualizationON << std::endl;
	outputConfigfile << "Simulation Speed: " << simSpeed << std::endl;
	outputConfigfile << "ScreenWidth in Pixels: " << screenWidthPixels << std::endl;
	outputConfigfile << "Screen Height in Pixels: " << screenHeightPixels << std::endl;
	outputConfigfile << "Field Length and Width: " << FieldLength << std::endl;
	outputConfigfile << "Goal LocationX: " << gLocX << std::endl;
	outputConfigfile << "Goal LocationT: " << gLocY << std::endl;
	outputConfigfile << "Paddock On : " << paddockON << std::endl;
	outputConfigfile << "Paddock Length: " << paddockLength << std::endl;
	outputConfigfile << "paddock Width: " << paddockWidth << std::endl;
	outputConfigfile << "Goal Radius: " << goalRadius << std::endl;
	outputConfigfile << "N: " << N << std::endl;
	outputConfigfile << "M: " << M << std::endl;
	outputConfigfile << "R_pi_beta: " << R_pi_beta << std::endl;
	outputConfigfile << "Ra_pi_pi: " << Ra_pi_pi << std::endl;
	outputConfigfile << "Rs_pi_pi: " << Rs_pi_pi << std::endl;
	outputConfigfile << "card_Omega_pi_pi: " << card_Omega_pi_pi << std::endl;
	outputConfigfile << "card_Omega_beta_pi: " << card_Omega_beta_pi << std::endl;
	outputConfigfile << "W_pi_pi: " << W_pi_pi << std::endl;
	outputConfigfile << "W_pi_beta: " << W_pi_beta << std::endl;
	outputConfigfile << "W_pi_Lambda: " << W_pi_Lambda << std::endl;
	outputConfigfile << "W_pi_upsilon: " << W_pi_upsilon << std::endl;
	outputConfigfile << "W_e_pi_i: " << W_e_pi_i << std::endl;
	outputConfigfile << "W_e_beta_j: " << W_e_beta_j << std::endl;
	outputConfigfile << "S_t_beta_j: " << S_t_beta_j << std::endl;
	outputConfigfile << "eta: " << eta << std::endl;
	outputConfigfile << "R_beta_beta: " << R_beta_beta << std::endl;
	outputConfigfile << "R_beta_pi: " << R_beta_pi << std::endl;
	outputConfigfile << "W_beta_beta: " << W_beta_beta << std::endl;
	outputConfigfile << "DrivingPositionEq" << DrivingPositionEq << std::endl;
	outputConfigfile << "CollectingPositionEq" << CollectingPositionEq << std::endl;
	outputConfigfile << "fNequation" << fNequation << std::endl;
	outputConfigfile << "Circular Path Planning On : " << CircularPathPlanningON << std::endl;
	outputConfigfile << "StallingON : " << StallingON << std::endl;
	outputConfigfile << "StallingDistance : " << StallingDistance << std::endl;
	outputConfigfile << "ForceRegulated" << ForceRegulated << std::endl;
	outputConfigfile << "SheepNeignborhoodSelection" << SheepNeignborhoodSelection << std::endl;
	outputConfigfile << "ModulationDecayFactor" << ModulationDecayFactor << std::endl;
	outputConfigfile << "R2 : " << R2 << std::endl;
	outputConfigfile << "R3 : " << R3 << std::endl;
	outputConfigfile << "sheepInitializationStartingX: " << sheepInitializationStartingX << std::endl;
	outputConfigfile << "sheepInitializationStartingX: " << sheepInitializationStartingX << std::endl;
	outputConfigfile << "sheepInitializationXRange: " << sheepInitializationXRange << std::endl;
	outputConfigfile << "sheepInitializationYRange: " << sheepInitializationYRange << std::endl;
	outputConfigfile << "sheepInitializationPattern: " << sheepInitializationPattern << std::endl;
	outputConfigfile << "sheepDogInitializationStartingX: " << sheepDogInitializationStartingX << std::endl;
	outputConfigfile << "sheepDogInitializationStartingY: " << sheepDogInitializationStartingX << std::endl;
	outputConfigfile << "sheepDogInitializationXRange: " << sheepDogInitializationXRange << std::endl;
	outputConfigfile << "sheepDogInitializationYRange: " << sheepDogInitializationYRange << std::endl;
	outputConfigfile << "ObstaclesDensity: " << obstaclesDensity << std::endl;
	outputConfigfile << "ObstaclesRadius: " << obstaclesRadius << std::endl;

	outputHeader_file << "TimeStep,";

	for (int i = 0; i < M; i++)
	{
		outputHeader_file << "SheepDogID,";
		outputHeader_file << "SheepDogPositionX,";
		outputHeader_file << "SheepDogPositionY,";
		outputHeader_file << "SheepDogPositionVelocityX,";
		outputHeader_file << "SheepDogPositionVelocityY,";
		outputHeader_file << "SheepDogCurrentMode,";
		outputHeader_file << "Role,";
	}

	for (int i = 0; i < N; i++)
	{
		outputHeader_file << "SheepID,";
		outputHeader_file << "SheepPositionX,";
		outputHeader_file << "SheepPositionY,";
		outputHeader_file << "SheepPositionVelocityX,";
		outputHeader_file << "SheepPositionVelocityY,";
		outputHeader_file << "Sheep_F_pi_i_beta_j_X,";
		outputHeader_file << "Sheep_F_pi_i_beta_j_Y,";
		outputHeader_file << "Sheep_F_pi_i_Lambda_X,";
		outputHeader_file << "Sheep_F_pi_i_Lambda_Y,";
		outputHeader_file << "Sheep_F_pi_i_pi_i_X,";
		outputHeader_file << "Sheep_F_pi_i_pi_i_Y,";
	}
}

static void WriteObstaclesFilesHeadless(std::ofstream& ObstaclesOutputFile)
{
	Environment& env = Environment::getInstance();
	for (int i = 0; i < env.terrain.staticObstacles->size(); i++) {
		ObstaclesOutputFile << (*env.terrain.staticObstacles)[i]->position_t.x << ",";
		ObstaclesOutputFile << (*env.terrain.staticObstacles)[i]->position_t.y << ",";
		ObstaclesOutputFile << (*env.terrain.staticObstacles)[i]->radius << std::endl;
	}
}

int main(int argc, char* argv[])
{
	std::string ConfigFile = "../InputFiles/config.xml"; //set the default configuration file name
	std::string GraphicFile = "../InputFiles/VisualizationOptions.xml"; //set the default filename
	bool experimentMode = false;
	for (int i = 1; i < argc; i++)
	{
		if (std::string(argv[i]) == "--experiment")
		{
			experimentMode = true;
		}
		else
		{
			ConfigFile = argv[i]; //if a new configuration file name is given then update the ConfigFile name
		}
	}
	for (int i = 1; i < argc; i++)
		printf("Argument %d: %s\n", (i + 1), argv[i]);

	loadConfigurationPortable(ConfigFile);
	loadGraphicsPortable(GraphicFile); //visualisation-only values; loaded for parity, unused headless

	if (experimentMode)
	{
		// 27-condition adversarial experiment (REQUIREMENTS.md Section 3.7). Requires
		// AdversarialMode=1 in the config.
		if (AdversarialMode != 1)
		{
			printf("--experiment requires AdversarialMode=1 in the config\n");
			return 1;
		}
		return runExperiment("results");
	}
	if (AdversarialMode == 1)
	{
		// Single adversarial run with the config's own initialisation.
		return runAdversarialSingle(std::string("./") + ConfigFile.substr(0, ConfigFile.length() - 4) + "_AdversarialPerStep.csv");
	}

	std::ofstream output_file(std::string("./") + ConfigFile.substr(0, ConfigFile.length() - 4) + std::string("_OutPutData.csv"));
	std::ofstream outputHeader_file(std::string("./") + ConfigFile.substr(0, ConfigFile.length() - 4) + std::string("_OutPutDataHeader.csv"));
	std::ofstream outputConfigfile(std::string("./") + ConfigFile.substr(0, ConfigFile.length() - 4) + std::string("_RunConfigurationSaved.txt"));
	std::ofstream outputCompletionTimefile(std::string("./") + ConfigFile.substr(0, ConfigFile.length() - 4) + std::string("_CompletionTimeOnly.txt"));
	std::ofstream StaticObstaclesOutputFile(std::string("./") + ConfigFile.substr(0, ConfigFile.length() - 4) + std::string("_StaticObstaclesOutputFile.csv"));

	WriteOutFilesHeadless(outputHeader_file, outputConfigfile);

	int fieldWidth = FieldLength, fieldHeight = FieldLength;

	CLI* cli = new CLI();
	cli->init(randomNumberSeed, fieldWidth, fieldHeight, N, M, R_pi_beta, Ra_pi_pi, Rs_pi_pi, R_beta_beta, R_beta_pi, W_pi_pi, W_beta_beta, W_pi_beta, W_pi_Lambda, W_pi_upsilon, W_e_pi_i, W_e_beta_j, S_t_beta_j, eta, card_Omega_pi_pi, card_Omega_beta_pi, gLocX, gLocY, paddockLength, paddockWidth, paddockON, CircularPathPlanningON, StallingON, StallingDistance, R2, R3, goalRadius, ForceRegulated, fNequation, DrivingPositionEq, CollectingPositionEq, SheepNeignborhoodSelection, ModulationDecayFactor, sheepInitializationStartingX, sheepInitializationStartingY, sheepInitializationXRange, sheepInitializationYRange, sheepInitializationPattern, sheepDogInitializationStartingX, sheepDogInitializationStartingY, sheepDogInitializationXRange, sheepDogInitializationYRange, MaximumNumSteps, obstaclesDensity, obstaclesRadius);
	WriteObstaclesFilesHeadless(StaticObstaclesOutputFile);

	while (cli->running()) //while running
	{
		cli->handleEvents();
		cli->update();
		cli->streamOut(output_file, outputCompletionTimefile);
	}

	return 0;
}
