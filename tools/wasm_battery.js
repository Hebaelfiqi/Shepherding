#!/usr/bin/env node
// Run shepherding batteries inside the WebAssembly build (validation harness).
//
// Usage:
//   node tools/wasm_battery.js build-wasm/shepherd_sim_web.js t0
//   node tools/wasm_battery.js build-wasm/shepherd_sim_web.js battery <model> <seeds> [pattern]
// where <model> is "proposed" or "strombom". Prints completion step per run
// (or -1 if not completed) and summary statistics.

const path = require("path");

const MAX_STEPS = 2000;

// Table 2 of the IEEE Access paper == InputFiles/Config.xml
function params(model, seed, pattern) {
  const strombom = model === "strombom";
  return {
    seed, nSheep: 100, nDogs: 1, fieldLength: 50,
    R_pi_beta: 65, Ra_pi_pi: 0.4, Rs_pi_pi: 3, R_beta_beta: 2, R_beta_pi: 65,
    W_pi_pi: 2, W_beta_beta: 0.5, W_pi_beta: 1, W_pi_Lambda: 1.05,
    W_pi_upsilon: 0.5, W_e_pi_i: 0.3, W_e_beta_j: 0.3,
    S_t_beta_j: 2.0, eta: 0.05,
    // Strombom neighbourhood is nearest-n with n = 0.5 N (paper Fig. 5 main variant)
    card_Omega_pi_pi: strombom ? 50 : 99,
    card_Omega_beta_pi: 100,
    goalX: 25, goalY: 50, goalRadius: 10,
    circularPathPlanningON: strombom ? 0 : 1,
    stallingON: strombom ? 1 : 0,
    stallingDistance: 3 * 0.4,
    R2: 4, R3: 10,
    forceRegulated: strombom ? 0 : 1,
    fNequation: strombom ? 0 : 1,
    drivingPositionEq: strombom ? 0 : 1,
    collectingPositionEq: strombom ? 0 : 1,
    sheepNeighborhoodSelection: strombom ? 0 : 1,
    modulationDecayFactor: 2,
    sheepX: 20, sheepY: 20, sheepW: 10, sheepH: 10, patternId: pattern,
    dogX: 15, dogY: 45, dogW: 20, dogH: 5,
    maximumSteps: MAX_STEPS,
  };
}

function create(mod, p) {
  // all arguments are numbers, so the raw export is callable directly
  mod._sim_create(
    p.seed, p.nSheep, p.nDogs, p.fieldLength,
     p.R_pi_beta, p.Ra_pi_pi, p.Rs_pi_pi, p.R_beta_beta, p.R_beta_pi,
     p.W_pi_pi, p.W_beta_beta, p.W_pi_beta, p.W_pi_Lambda,
     p.W_pi_upsilon, p.W_e_pi_i, p.W_e_beta_j,
     p.S_t_beta_j, p.eta, p.card_Omega_pi_pi, p.card_Omega_beta_pi,
     p.goalX, p.goalY, p.goalRadius,
     p.circularPathPlanningON, p.stallingON, p.stallingDistance,
     p.R2, p.R3, p.forceRegulated, p.fNequation,
     p.drivingPositionEq, p.collectingPositionEq, p.sheepNeighborhoodSelection,
     p.modulationDecayFactor,
     p.sheepX, p.sheepY, p.sheepW, p.sheepH, p.patternId,
     p.dogX, p.dogY, p.dogW, p.dogH, p.maximumSteps);
}

function runOne(mod, model, seed, pattern) {
  create(mod, params(model, seed, pattern));
  while (mod._sim_step()) { /* advance */ }
  return mod._sim_goal_found() ? mod._sim_time() : -1;
}

async function main() {
  const [, , modulePath, mode, ...rest] = process.argv;
  const createShepherdModule = require(path.resolve(modulePath));
  const mod = await createShepherdModule();

  if (mode === "t0") {
    const t = runOne(mod, "proposed", 0, 1);
    console.log(`wasm T0 scenario (proposed model, N=100, seed 0, P1): ` +
      (t >= 0 ? `completed at step ${t}` : `NOT completed within ${MAX_STEPS}`));
    return;
  }

  const model = rest[0] || "proposed";
  const seeds = parseInt(rest[1] || "30", 10);
  const patterns = rest[2] ? [parseInt(rest[2], 10)] : [1, 2, 3, 4, 5, 6];
  for (const pat of patterns) {
    const times = [];
    let completed = 0;
    for (let s = 0; s < seeds; s++) {
      const t = runOne(mod, model, s, pat);
      if (t >= 0) { completed++; times.push(t); }
    }
    const mean = times.length ? (times.reduce((a, b) => a + b, 0) / times.length) : NaN;
    console.log(`${model} P${pat}: completed ${completed}/${seeds}` +
      (times.length ? `, mean completion ${mean.toFixed(1)} steps` : ""));
  }
}

main();
