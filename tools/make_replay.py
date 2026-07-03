#!/usr/bin/env python3
"""Build a self-contained HTML replay of adversarial runs from positions CSVs.

Single run:
  python3 tools/make_replay.py <..._Positions.csv> [-o replay.html]

Multi-pattern picker (one run per initialisation pattern, drag or click to load):
  python3 tools/make_replay.py --run P1=p1.csv --run P6=p6.csv [-o replay.html]

The simulator writes the positions file next to the per-step metrics on every single
(non-experiment) adversarial run:
  ./build/shepherd_sim InputFiles/Config_Adversarial.xml
Open the resulting replay.html in any browser. Standard library only.
"""
import argparse
import csv
import json

# Pattern cell sets from SheepFlock's 5x5 grid (Flock.cpp): index = row*5 + col,
# row 0 at the LOW y edge of the initialisation box (the mini-maps render y-up,
# matching the field view).
PATTERNS = {
    "P1": {"cells": list(range(25)), "name": "Full spread"},
    "P2": {"cells": [1, 2, 3, 6, 7, 8], "name": "Dense band"},
    "P3": {"cells": [1, 3, 10, 12, 14], "name": "Scattered"},
    "P4": {"cells": [0, 4, 10, 14, 22], "name": "Arrowhead"},
    "P5": {"cells": [2, 10, 14, 20, 24], "name": "Arrowhead reversed"},
    "P6": {"cells": [0, 4, 20, 24], "name": "Corners"},
}

BC_LABELS = [
    "BC1 Driving", "BC2 Collecting", "BC3 Intercepting", "BC4 Patrolling",
    "BC5 Drive+Collect", "BC6 Drive+Intercept", "BC7 Drive+Patrol",
    "BC8 Collect+Intercept", "BC9 Collect+Patrol", "BC10 Intercept+Patrol",
]

TEMPLATE = r"""<title>Adversarial patrolling replay</title>
<style>
  :root {
    --ground:#10161d; --panel:#161e28; --line:#26313f; --ink:#c9d3dd; --muted:#77828f;
    --attacker:#e0aa5e; --defender:#62b6cb; --aoi:#e4604e; --good:#7fb069;
  }
  * { box-sizing:border-box; margin:0; }
  body { background:var(--ground); color:var(--ink);
         font:14px/1.5 "Avenir Next","Segoe UI",system-ui,sans-serif;
         display:flex; justify-content:center; padding:24px 16px; }
  .wrap { width:min(1100px,100%); }
  header { display:flex; justify-content:space-between; align-items:baseline;
           flex-wrap:wrap; gap:4px 16px; margin-bottom:14px; }
  h1 { font-size:17px; font-weight:600; letter-spacing:.01em; }
  header .sub { color:var(--muted); font-size:12.5px; }
  .layout { display:grid; grid-template-columns:minmax(0,1fr) 286px; gap:14px; }
  @media (max-width:860px){ .layout { grid-template-columns:1fr; } }
  .stage { background:var(--panel); border:1px solid var(--line); border-radius:6px;
           padding:12px; position:relative; }
  canvas#field { width:100%; height:auto; display:block; border-radius:3px; }
  #overlay { position:absolute; inset:12px auto auto 12px; right:12px;
             display:flex; align-items:flex-start; justify-content:center;
             pointer-events:none; }
  #overlay .msg { margin-top:26px; background:rgba(13,19,25,.88);
                  border:1px solid var(--line); border-radius:5px; padding:9px 16px;
                  font-size:13px; color:var(--ink); }
  #overlay .msg b { color:var(--attacker); font-weight:600; }
  .controls { display:flex; align-items:center; gap:10px; margin-top:12px; flex-wrap:wrap; }
  button { background:#202b38; color:var(--ink); border:1px solid var(--line); border-radius:4px;
           font:inherit; font-size:13px; padding:5px 14px; cursor:pointer; }
  button:hover { border-color:#3a4a5d; }
  button:focus-visible { outline:2px solid var(--defender); outline-offset:1px; }
  button[aria-pressed="true"] { border-color:var(--defender); color:var(--defender); }
  input[type=range] { flex:1; min-width:120px; accent-color:var(--defender); }
  .step { font:13px/1 ui-monospace,"Cascadia Code",Menlo,monospace;
          font-variant-numeric:tabular-nums; color:var(--muted); min-width:150px; }
  .side { display:flex; flex-direction:column; gap:12px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:12px 14px; }
  .card h2 { font-size:10.5px; font-weight:600; letter-spacing:.14em; text-transform:uppercase;
             color:var(--muted); margin-bottom:8px; }
  .bc-chip { display:inline-block; font:13px ui-monospace,Menlo,monospace; padding:4px 10px;
             border:1px solid var(--defender); border-radius:3px; color:var(--defender); }
  .metrics { display:grid; grid-template-columns:auto 1fr; gap:3px 12px;
             font:12.5px ui-monospace,Menlo,monospace; font-variant-numeric:tabular-nums; }
  .metrics dt { color:var(--muted); }
  .metrics dd { text-align:right; }
  .explain { color:var(--muted); font-size:11.5px; margin-top:8px; line-height:1.45; }
  .legend { display:grid; gap:6px; font-size:12.5px; }
  .legend span { display:flex; align-items:center; gap:8px; }
  .dot { width:10px; height:10px; border-radius:50%; flex:none; }
  .ring { width:10px; height:10px; border-radius:50%; flex:none; border:1px dashed var(--muted); }
  .target { width:12px; height:12px; flex:none; }
  #spark, #cluststrip { width:100%; display:block; }
  .hint { color:var(--muted); font-size:11.5px; margin-top:10px; }
  select { background:#202b38; color:var(--ink); border:1px solid var(--line);
           border-radius:4px; font:inherit; font-size:13px; padding:4px 6px; }
  .patterns { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
  .pat { border:1px solid var(--line); border-radius:5px; padding:7px 6px 5px; text-align:center;
         cursor:grab; background:#131a23; }
  .pat:hover { border-color:#3a4a5d; }
  .pat[data-active="1"] { border-color:var(--attacker); }
  .pat canvas { width:100%; image-rendering:pixelated; border-radius:2px; }
  .pat .lab { font-size:10.5px; color:var(--muted); margin-top:4px; line-height:1.25; }
  .pat[data-active="1"] .lab b { color:var(--attacker); }
  .pat .lab b { font-size:11px; color:var(--ink); }
  .stat { font:12px ui-monospace,Menlo,monospace; color:var(--muted); margin-top:6px;
          font-variant-numeric:tabular-nums; }
  .stat b { color:var(--ink); font-weight:600; }
</style>
<div class="wrap">
  <header>
    <h1>Adversarial patrolling replay</h1>
    <span class="sub">__SUBTITLE__</span>
  </header>
  <div class="layout">
    <div class="stage">
      <canvas id="field" width="760" height="760"></canvas>
      <div id="overlay" hidden><span class="msg" id="overlayMsg"></span></div>
      <div class="controls">
        <button id="play" aria-pressed="false">Play</button>
        <button id="reset">Restart</button>
        <select id="speed" aria-label="Playback speed">
          <option value="0.15">0.15x</option>
          <option value="0.25" selected>0.25x</option>
          <option value="0.5">0.5x</option>
          <option value="1">1x</option>
          <option value="2">2x</option>
          <option value="4">4x</option>
        </select>
        <button id="trails" aria-pressed="true">Trails</button>
        <input id="scrub" type="range" min="0" max="__TMAX__" value="0" aria-label="Timestep">
        <span class="step" id="stepLabel">timestep 0 / __TMAX__</span>
      </div>
      <p class="hint">Space plays and pauses. Drag the slider to scrub. Drag a formation card onto
      the field (or click it) to load that run. The dashed ring around the AOI is the target
      standoff: the swarm should be held outside it.</p>
    </div>
    <div class="side">
      <div class="card" id="patternCard">
        <h2>Starting formation (drag onto field)</h2>
        <div class="patterns" id="patterns"></div>
      </div>
      <div class="card">
        <h2>Defender decision (this timestep)</h2>
        <span class="bc-chip" id="bcChip">BC1 Driving</span>
      </div>
      <div class="card">
        <h2>Telemetry</h2>
        <dl class="metrics">
          <dt>swarm to AOI</dt><dd id="mM1">0.0</dd>
          <dt>defender to AOI</dt><dd id="mDog">0.0</dd>
          <dt>blocking angle</dt><dd id="mM3">0.00</dd>
          <dt>swarm clustered</dt><dd id="mClus">yes</dd>
        </dl>
        <p class="explain">Blocking angle: measured at the AOI, between the direction to the
        swarm centre and the direction to the defender. 0 rad = defender exactly on the line
        between swarm and AOI (blocking); above 1.57 (pi/2) = defender on the far side, out of
        position.</p>
      </div>
      <div class="card">
        <h2>Swarm to AOI distance</h2>
        <canvas id="spark" width="252" height="72"></canvas>
        <p class="stat">inside target standoff: <b id="breachPct">0%</b> of timesteps so far</p>
      </div>
      <div class="card">
        <h2>Swarm cohesion over time</h2>
        <canvas id="cluststrip" width="252" height="26"></canvas>
        <p class="stat">clustered: <b id="clusPct">0%</b> of timesteps so far</p>
      </div>
      <div class="card">
        <h2>Legend</h2>
        <div class="legend">
          <span><i class="dot" style="background:var(--attacker)"></i>attacker swarm (N = __N__)</span>
          <span><i class="dot" style="background:var(--defender)"></i>defender (single sheepdog)</span>
          <span><svg class="target" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="#e4604e"/><circle cx="6" cy="6" r="1.8" fill="#e4604e"/></svg>AOI: Area of Interest, the protected point the attackers try to reach</span>
          <span><i class="ring"></i>target standoff (__EQ__ units): swarm held outside = defence holding</span>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
const RUNS = __RUNS__;
const PATTERNS = __PATTERNS__;
const AOI = __AOI__, FIELD = __FIELD__, EQ = __EQ__, FN = __FN__;
const BC = __BCLABELS__;
const BOX = __BOX__; // sheep initialisation box [x, y, w, h] for the mini-map inset
const DEFAULT_RUN = __DEFAULT__;

let runKey = DEFAULT_RUN;
let DATA = RUNS[runKey];
const N = (DATA[0].length - 4) / 2;
const cv = document.getElementById('field'), cx = cv.getContext('2d');
const sp = document.getElementById('spark'), sx = sp.getContext('2d');
const cs = document.getElementById('cluststrip'), csx = cs.getContext('2d');
const S = cv.width / FIELD;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let t = 0, playing = false, acc = 0, last = 0, trails = true;
let m1s = [], clustered = [];
let introTimer = null;

function computeSeries() {
  m1s = DATA.map(r => {
    let gx = 0, gy = 0;
    for (let i = 0; i < N; i++) { gx += r[4 + 2 * i]; gy += r[5 + 2 * i]; }
    return Math.hypot(gx / N - AOI[0], gy / N - AOI[1]);
  });
  clustered = DATA.map(r => {
    let gx = 0, gy = 0;
    for (let i = 0; i < N; i++) { gx += r[4 + 2 * i]; gy += r[5 + 2 * i]; }
    gx /= N; gy /= N;
    for (let i = 0; i < N; i++)
      if (Math.hypot(r[4 + 2 * i] - gx, r[5 + 2 * i] - gy) > FN) return 0;
    return 1;
  });
}

function X(x) { return x * S; }
function Y(y) { return cv.height - y * S; }

function drawAOI() {
  const ax = X(AOI[0]), ay = Y(AOI[1]);
  cx.strokeStyle = css('--aoi'); cx.lineWidth = 1.6;
  cx.beginPath(); cx.arc(ax, ay, 10, 0, 7); cx.stroke();
  cx.beginPath(); cx.arc(ax, ay, 5.5, 0, 7); cx.stroke();
  cx.fillStyle = css('--aoi');
  cx.beginPath(); cx.arc(ax, ay, 2, 0, 7); cx.fill();
  cx.font = '11px ui-monospace,Menlo,monospace';
  cx.fillText('AOI', ax + 14, ay + 4);
}

function draw() {
  cx.fillStyle = '#0d1319';
  cx.fillRect(0, 0, cv.width, cv.height);
  cx.strokeStyle = '#1c2632'; cx.lineWidth = 1;
  for (let g = 10; g < FIELD; g += 10) {
    cx.beginPath(); cx.moveTo(X(g), 0); cx.lineTo(X(g), cv.height); cx.stroke();
    cx.beginPath(); cx.moveTo(0, Y(g)); cx.lineTo(cv.width, Y(g)); cx.stroke();
  }
  const r = DATA[t];
  if (trails) {
    const from = Math.max(0, t - 45);
    for (let k = from; k < t; k++) {
      const a = 0.28 * (k - from) / Math.max(1, t - from);
      cx.fillStyle = 'rgba(224,170,94,' + a + ')';
      for (let i = 0; i < N; i++) cx.fillRect(X(DATA[k][4 + 2 * i]) - 1, Y(DATA[k][5 + 2 * i]) - 1, 2, 2);
      cx.fillStyle = 'rgba(98,182,203,' + a + ')';
      cx.fillRect(X(DATA[k][1]) - 1, Y(DATA[k][2]) - 1, 2, 2);
    }
  }
  cx.setLineDash([5, 5]); cx.strokeStyle = '#4a5866'; cx.lineWidth = 1;
  cx.beginPath(); cx.arc(X(AOI[0]), Y(AOI[1]), EQ * S, 0, 7); cx.stroke();
  cx.setLineDash([]);
  drawAOI();
  let gx = 0, gy = 0;
  for (let i = 0; i < N; i++) { gx += r[4 + 2 * i]; gy += r[5 + 2 * i]; }
  gx /= N; gy /= N;
  cx.strokeStyle = 'rgba(224,170,94,.25)';
  cx.beginPath(); cx.moveTo(X(AOI[0]), Y(AOI[1])); cx.lineTo(X(gx), Y(gy)); cx.stroke();
  cx.fillStyle = css('--attacker');
  for (let i = 0; i < N; i++) {
    cx.beginPath(); cx.arc(X(r[4 + 2 * i]), Y(r[5 + 2 * i]), 4, 0, 7); cx.fill();
  }
  cx.strokeStyle = 'rgba(224,170,94,.6)';
  cx.beginPath(); cx.arc(X(gx), Y(gy), 6.5, 0, 7); cx.stroke();
  cx.fillStyle = css('--defender');
  cx.beginPath(); cx.arc(X(r[1]), Y(r[2]), 5.5, 0, 7); cx.fill();
  cx.strokeStyle = 'rgba(98,182,203,.45)';
  cx.beginPath(); cx.arc(X(r[1]), Y(r[2]), 9.5, 0, 7); cx.stroke();

  document.getElementById('bcChip').textContent = BC[r[3] - 1];
  document.getElementById('mM1').textContent = m1s[t].toFixed(1) + ' u';
  document.getElementById('mDog').textContent =
    Math.hypot(r[1] - AOI[0], r[2] - AOI[1]).toFixed(1) + ' u';
  const v1 = [gx - AOI[0], gy - AOI[1]], v2 = [r[1] - AOI[0], r[2] - AOI[1]];
  const m3 = Math.acos(Math.min(1, Math.max(-1,
    (v1[0] * v2[0] + v1[1] * v2[1]) / (Math.hypot(...v1) * Math.hypot(...v2) || 1))));
  document.getElementById('mM3').textContent = m3.toFixed(2) + ' rad';
  const clusEl = document.getElementById('mClus');
  clusEl.textContent = clustered[t] ? 'yes' : 'no';
  clusEl.style.color = clustered[t] ? css('--good') : css('--aoi');
  document.getElementById('stepLabel').textContent =
    'timestep ' + r[0] + ' / ' + DATA[DATA.length - 1][0];
  document.getElementById('scrub').value = t;

  // distance graph with target standoff line, breach segments in red
  sx.clearRect(0, 0, sp.width, sp.height);
  const mmax = Math.max(EQ * 1.2, Math.max(...m1s) * 1.05);
  const gy2 = v => sp.height - 5 - (v / mmax) * (sp.height - 14);
  sx.strokeStyle = '#4a5866'; sx.setLineDash([3, 3]);
  sx.beginPath(); sx.moveTo(0, gy2(EQ)); sx.lineTo(sp.width, gy2(EQ)); sx.stroke();
  sx.setLineDash([]);
  sx.fillStyle = '#77828f'; sx.font = '9px ui-monospace,monospace';
  sx.fillText('target standoff ' + EQ.toFixed(1), 4, gy2(EQ) - 3);
  let breaches = 0;
  for (let k = 1; k <= t; k++) {
    sx.strokeStyle = m1s[k] < EQ ? css('--aoi') : css('--attacker');
    sx.lineWidth = 1.4;
    sx.beginPath();
    sx.moveTo((k - 1) / (DATA.length - 1) * sp.width, gy2(m1s[k - 1]));
    sx.lineTo(k / (DATA.length - 1) * sp.width, gy2(m1s[k]));
    sx.stroke();
  }
  for (let k = 0; k <= t; k++) if (m1s[k] < EQ) breaches++;
  sx.fillStyle = css('--attacker');
  sx.beginPath();
  sx.arc(t / (DATA.length - 1) * sp.width, gy2(m1s[t]), 2.5, 0, 7); sx.fill();
  document.getElementById('breachPct').textContent =
    (100 * breaches / (t + 1)).toFixed(0) + '%';

  // cohesion strip: green = clustered, red = a straggler beyond fN
  csx.clearRect(0, 0, cs.width, cs.height);
  csx.fillStyle = '#1c2632'; csx.fillRect(0, 8, cs.width, 12);
  let clus = 0;
  for (let k = 0; k <= t; k++) {
    if (clustered[k]) clus++;
    csx.fillStyle = clustered[k] ? css('--good') : css('--aoi');
    csx.fillRect(k / (DATA.length - 1) * cs.width, 8, Math.max(1, cs.width / DATA.length), 12);
  }
  document.getElementById('clusPct').textContent = (100 * clus / (t + 1)).toFixed(0) + '%';
}

function frame(ts) {
  if (playing) {
    if (!last) last = ts;
    acc += (ts - last);
    const interval = 40 / parseFloat(document.getElementById('speed').value);
    while (acc > interval) {
      acc -= interval;
      if (t < DATA.length - 1) t++; else setPlaying(false);
    }
    draw();
  }
  last = ts;
  requestAnimationFrame(frame);
}
function setPlaying(p) {
  playing = p;
  const b = document.getElementById('play');
  b.textContent = p ? 'Pause' : 'Play';
  b.setAttribute('aria-pressed', p);
  if (p) hideOverlay();
}
function hideOverlay() {
  document.getElementById('overlay').hidden = true;
  if (introTimer) { clearTimeout(introTimer); introTimer = null; }
}
function showIntro() {
  // Hold on the starting formation so the observer can read the scene, then autoplay.
  setPlaying(false);
  t = 0; draw();
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const msg = document.getElementById('overlayMsg');
  const name = PATTERNS[runKey] ? PATTERNS[runKey].name : runKey;
  const ov = document.getElementById('overlay');
  ov.hidden = false;
  if (reduced) {
    msg.innerHTML = 'Starting formation: <b>' + runKey + ' ' + name + '</b>. Press Play to run.';
    return;
  }
  let s = 5;
  const tick = () => {
    msg.innerHTML = 'Starting formation: <b>' + runKey + ' ' + name +
      '</b> &nbsp;-&nbsp; playing in ' + s + 's';
    if (s-- > 0) { introTimer = setTimeout(tick, 1000); }
    else { hideOverlay(); setPlaying(true); }
  };
  tick();
}

function loadRun(key) {
  if (!RUNS[key]) return;
  runKey = key;
  DATA = RUNS[key];
  computeSeries();
  document.querySelectorAll('.pat').forEach(p =>
    p.dataset.active = (p.dataset.key === key) ? '1' : '0');
  showIntro();
}

// formation picker: mini-maps of the 5x5 initialisation grid, drag onto field or click
function buildPatterns() {
  const host = document.getElementById('patterns');
  for (const key of Object.keys(RUNS)) {
    const meta = PATTERNS[key];
    const card = document.createElement('div');
    card.className = 'pat'; card.draggable = true;
    card.dataset.key = key;
    card.dataset.active = (key === runKey) ? '1' : '0';
    card.setAttribute('role', 'button'); card.tabIndex = 0;
    const mini = document.createElement('canvas');
    mini.width = 55; mini.height = 55;
    const g = mini.getContext('2d');
    g.fillStyle = '#0d1319'; g.fillRect(0, 0, 55, 55);
    for (const c of meta.cells) {
      const col = c % 5, row = Math.floor(c / 5);      // row 0 = low y, render y-up
      g.fillStyle = 'rgba(224,170,94,.9)';
      g.fillRect(col * 11 + 1.5, (4 - row) * 11 + 1.5, 8, 8);
    }
    card.appendChild(mini);
    const lab = document.createElement('div');
    lab.className = 'lab';
    lab.innerHTML = '<b>' + key + '</b><br>' + meta.name;
    card.appendChild(lab);
    card.addEventListener('click', () => loadRun(key));
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); loadRun(key); }
    });
    card.addEventListener('dragstart', e =>
      e.dataTransfer.setData('text/plain', key));
    host.appendChild(card);
  }
  cv.addEventListener('dragover', e => e.preventDefault());
  cv.addEventListener('drop', e => {
    e.preventDefault();
    loadRun(e.dataTransfer.getData('text/plain'));
  });
}

document.getElementById('play').onclick = () => {
  if (!playing && t >= DATA.length - 1) t = 0;
  setPlaying(!playing);
};
document.getElementById('reset').onclick = () => { t = 0; setPlaying(true); draw(); };
document.getElementById('trails').onclick = e => {
  trails = !trails; e.target.setAttribute('aria-pressed', trails); draw();
};
document.getElementById('scrub').oninput = e => {
  t = +e.target.value; setPlaying(false); hideOverlay(); draw();
};
document.addEventListener('keydown', e => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT' && !e.target.classList.contains('pat')) {
    e.preventDefault(); document.getElementById('play').click();
  }
});

buildPatterns();
computeSeries();
draw();
requestAnimationFrame(frame);
showIntro();
</script>
"""


def read_positions(path):
    rows = []
    with open(path) as f:
        rdr = csv.reader(f)
        next(rdr)
        for row in rdr:
            rows.append([round(float(v), 3) for v in row])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("positions_csv", nargs="?", help="single positions CSV (simple mode)")
    ap.add_argument("--run", action="append", default=[],
                    metavar="KEY=CSV", help="pattern key = positions CSV; repeatable")
    ap.add_argument("--default", default=None, help="run key selected at load")
    ap.add_argument("-o", "--out", default="replay.html")
    ap.add_argument("--aoi", nargs=2, type=float, default=[25.0, 41.667])
    ap.add_argument("--field", type=float, default=50.0)
    ap.add_argument("--fn", type=float, default=8.944, help="clustering radius fN")
    ap.add_argument("--eq", type=float, default=13.86,
                    help="target standoff radius (repulsion-attraction equilibrium)")
    ap.add_argument("--box", nargs=4, type=float, default=[15, 2, 15, 15],
                    help="sheep initialisation box x y w h (mini-map context)")
    ap.add_argument("--subtitle", default="")
    args = ap.parse_args()

    runs = {}
    for spec in args.run:
        key, _, path = spec.partition("=")
        runs[key] = read_positions(path)
    if args.positions_csv:
        runs.setdefault("P6", read_positions(args.positions_csv))
    if not runs:
        ap.error("give a positions CSV or at least one --run KEY=CSV")

    default = args.default or next(iter(runs))
    n = (len(next(iter(runs.values()))[0]) - 4) // 2
    steps = len(next(iter(runs.values())))
    subtitle = args.subtitle or (
        f"{steps} timesteps per run, {n} attackers, one defender guarding the "
        f"Area of Interest at ({args.aoi[0]:g}, {args.aoi[1]:g})")

    html = (TEMPLATE
            .replace("__RUNS__", json.dumps(runs, separators=(",", ":")))
            .replace("__PATTERNS__", json.dumps(PATTERNS))
            .replace("__AOI__", json.dumps(args.aoi))
            .replace("__FIELD__", json.dumps(args.field))
            .replace("__EQ__", json.dumps(args.eq))
            .replace("__FN__", json.dumps(args.fn))
            .replace("__BOX__", json.dumps(args.box))
            .replace("__BCLABELS__", json.dumps(BC_LABELS))
            .replace("__DEFAULT__", json.dumps(default))
            .replace("__TMAX__", str(steps - 1))
            .replace("__N__", str(n))
            .replace("__SUBTITLE__", subtitle))
    with open(args.out, "w") as f:
        f.write(html)
    print(f"wrote {args.out} ({len(runs)} runs, {steps} steps, {n} attackers)")


if __name__ == "__main__":
    main()
