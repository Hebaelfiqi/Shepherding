#!/usr/bin/env python3
"""Run shepherding batteries with the native shepherd_sim (validation harness).

Generates a Config.xml per (model, pattern, seed), runs the native binary, and reads
the completion file. Mirrors tools/wasm_battery.js exactly so native and wasm results
are directly comparable.

Usage: python3 tools/native_battery.py <shepherd_sim path> <model> <seeds> [pattern]
       model = proposed | strombom
"""
import subprocess
import sys
import tempfile
import os

MAX_STEPS = 2000

CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<ConfigurationFile>
<config category="Reproducibility"><RandomSeed>{seed}</RandomSeed></config>
<config category="Visualisation"><Visualisation>0</Visualisation></config>
<config category="Field"><FieldWidth>50</FieldWidth><WindowMarginSize>10</WindowMarginSize></config>
<config category="Goal"><x>25</x><y>50</y></config>
<config category="Paddock"><PaddockON>0</PaddockON><GoalRadius>10</GoalRadius><Length>30</Length><Width>30</Width></config>
<config category="Model">
<DrivingPositionEq>{flag}</DrivingPositionEq>
<CollectingPositionEq>{flag}</CollectingPositionEq>
<fNequation>{flag}</fNequation>
<StallingON>{stall}</StallingON>
<StallingDistance>1.2</StallingDistance>
<CircularPathPlanningON>{flag}</CircularPathPlanningON>
<SheepNeignborhoodSelection>{flag}</SheepNeignborhoodSelection>
<R3>10</R3>
<R2>4</R2>
<ForceRegulated>{flag}</ForceRegulated>
<ModulationDecayFactor>2</ModulationDecayFactor>
</config>
<config category="Parameters">
<N>100</N><M>1</M>
<R_pi_beta>65</R_pi_beta><Ra_pi_pi>0.4</Ra_pi_pi><Rs_pi_pi>3</Rs_pi_pi>
<card_Omega_pi_pi>{card}</card_Omega_pi_pi><card_Omega_beta_pi>100</card_Omega_beta_pi>
<W_pi_pi>2</W_pi_pi><W_pi_beta>1</W_pi_beta><W_pi_Lambda>1.05</W_pi_Lambda>
<W_pi_upsilon>0.5</W_pi_upsilon><W_e_pi_i>0.3</W_e_pi_i><W_e_beta_j>0.3</W_e_beta_j>
<S_t_beta_j>2.0</S_t_beta_j><eta>0.05</eta>
<R_beta_beta>2</R_beta_beta><R_beta_pi>65</R_beta_pi><W_beta_beta>0.5</W_beta_beta>
</config>
<config category="SheepInit">
<X>20</X><Y>20</Y><XR>10</XR><YR>10</YR><Pattern>P{pattern}</Pattern>
</config>
<config category="DogInit"><X>15</X><Y>45</Y><XR>20</XR><YR>5</YR></config>
<config category="MaxSteps"><maximumSteps>{max_steps}</maximumSteps></config>
<config category="obstacle"><Density>0.0</Density><Radius>1</Radius></config>
</ConfigurationFile>
"""


def run_one(binary, model, seed, pattern, workdir):
    strombom = model == "strombom"
    cfg = CONFIG.format(seed=seed, flag=0 if strombom else 1,
                        stall=1 if strombom else 0,
                        card=50 if strombom else 99,
                        pattern=pattern, max_steps=MAX_STEPS)
    path = os.path.join(workdir, "Config.xml")
    with open(path, "w") as f:
        f.write(cfg)
    subprocess.run([binary, "Config.xml"], cwd=workdir,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    with open(os.path.join(workdir, "Config_CompletionTimeOnly.txt")) as f:
        line = f.read().strip()
    # completed run: "<step>,1,"; timeout: "<step>,<fraction at goal>"
    parts = line.split(",")
    step, frac = int(parts[0]), float(parts[1])
    return step if (frac >= 1 and step < MAX_STEPS) else -1


def main():
    binary = os.path.abspath(sys.argv[1])
    model = sys.argv[2]
    seeds = int(sys.argv[3])
    patterns = [int(sys.argv[4])] if len(sys.argv) > 4 else [1, 2, 3, 4, 5, 6]
    with tempfile.TemporaryDirectory() as workdir:
        for pat in patterns:
            times = []
            completed = 0
            for s in range(seeds):
                t = run_one(binary, model, s, pat, workdir)
                if t >= 0:
                    completed += 1
                    times.append(t)
            mean = sum(times) / len(times) if times else float("nan")
            extra = f", mean completion {mean:.1f} steps" if times else ""
            print(f"{model} P{pat}: completed {completed}/{seeds}{extra}")


if __name__ == "__main__":
    main()
