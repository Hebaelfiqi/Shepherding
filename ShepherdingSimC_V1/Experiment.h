// Experiment.h : adversarial experiment harness (REQUIREMENTS.md Sections 3.7, 3.8).
// Runs the 27 reconstructed conditions x Experiment_steps timesteps, logs the Table III
// metrics and mission-success indicators per step, and writes results/results.csv plus
// results/perstep.csv for the figures.

#pragma once
#include <string>

// Run one adversarial simulation (AdversarialMode=1 config already loaded): uses the
// config's own initialisation, runs for `steps` timesteps, appends per-step metric rows
// to perStepPath (with the given run/condition labels). Returns 0 on success.
int runAdversarialSingle(const std::string& perStepPath);

// Run the full experiment: Experiment_conditions runs of Experiment_steps steps, seeded
// base_seed + run_index, writing results under outDir. Returns 0 on success.
int runExperiment(const std::string& outDir);
