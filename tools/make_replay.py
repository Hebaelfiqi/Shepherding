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
         display:flex; justify-content:center; padding:18px 16px; }
  .wrap { width:min(1140px,100%); }
  header { display:flex; justify-content:space-between; align-items:baseline;
           flex-wrap:wrap; gap:2px 16px; margin-bottom:10px; }
  h1 { font-size:16px; font-weight:600; letter-spacing:.01em; }
  header .sub { color:var(--muted); font-size:12px; }
  .layout { display:grid; grid-template-columns:minmax(0,1fr) 286px; gap:14px; align-items:start; }
  @media (max-width:880px){ .layout { grid-template-columns:1fr; } }
  .stage { background:var(--panel); border:1px solid var(--line); border-radius:6px;
           padding:12px; position:relative; }
  /* The field always fits the viewport together with the transport controls:
     width bound by the column, height bound by the viewport budget. */
  canvas#field { display:block; margin:0 auto; aspect-ratio:1/1; border-radius:3px;
                 width:min(100%, calc(100vh - 300px)); min-width:280px; height:auto; }
  #overlay { position:absolute; inset:12px 12px auto 12px; display:flex;
             justify-content:center; cursor:pointer; }
  #overlay .msg { margin-top:22px; background:rgba(13,19,25,.9);
                  border:1px solid var(--line); border-radius:5px; padding:8px 16px;
                  font-size:13px; color:var(--ink); }
  #overlay .msg b { color:var(--attacker); font-weight:600; }
  #overlay .msg small { color:var(--muted); }
  .controls { display:flex; align-items:center; gap:10px; margin-top:10px; flex-wrap:wrap; }
  button { background:#202b38; color:var(--ink); border:1px solid var(--line); border-radius:4px;
           font:inherit; font-size:13px; padding:5px 14px; cursor:pointer; }
  button:hover { border-color:#3a4a5d; }
  button:focus-visible, .pat:focus-visible, select:focus-visible, input:focus-visible
    { outline:2px solid var(--defender); outline-offset:1px; }
  button[aria-pressed="true"] { border-color:var(--defender); color:var(--defender); }
  input[type=range] { flex:1; min-width:110px; accent-color:var(--defender); }
  .ctl-label { font-size:10.5px; letter-spacing:.1em; text-transform:uppercase;
               color:var(--muted); }
  .step { font:13px/1 ui-monospace,"Cascadia Code",Menlo,monospace;
          font-variant-numeric:tabular-nums; color:var(--muted); min-width:150px; }
  .hint { color:var(--muted); font-size:11.5px; margin-top:8px; }
  select { background:#202b38; color:var(--ink); border:1px solid var(--line);
           border-radius:4px; font:inherit; font-size:13px; padding:4px 6px; }
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
  #spark, #cluststrip { width:100%; display:block; cursor:crosshair; touch-action:none; }
  .chart-hint { color:var(--muted); font-size:10.5px; margin-top:4px; }
  .stat { font:12px ui-monospace,Menlo,monospace; color:var(--muted); margin-top:6px;
          font-variant-numeric:tabular-nums; }
  .stat b { color:var(--ink); font-weight:600; }
  /* formation picker: setup control, lives under the field it configures */
  .pattern-strip { margin-top:12px; border-top:1px solid var(--line); padding-top:10px; }
  .pattern-strip h2 { font-size:10.5px; font-weight:600; letter-spacing:.14em;
                      text-transform:uppercase; color:var(--muted); margin-bottom:8px; }
  .patterns { display:flex; flex-wrap:wrap; gap:8px; }
  .pat { flex:1 1 100px; max-width:118px; border:1px solid var(--line); border-radius:5px;
         padding:6px 6px 5px; text-align:center; cursor:grab; background:#131a23; }
  .pat:hover { border-color:#3a4a5d; }
  .pat[data-active="1"] { border-color:var(--attacker); }
  .pat canvas { width:100%; image-rendering:pixelated; border-radius:2px; }
  .pat .lab { font-size:10.5px; color:var(--muted); margin-top:4px; line-height:1.25; }
  .pat .lab b { font-size:11px; color:var(--ink); }
  .pat[data-active="1"] .lab b { color:var(--attacker); }
  /* compact readout on the stage for narrow screens where the side column stacks far below */
  #miniHud { display:none; margin-top:8px; font:12px ui-monospace,Menlo,monospace;
             color:var(--muted); font-variant-numeric:tabular-nums; }
  #miniHud b { color:var(--defender); font-weight:600; }
  @media (max-width:880px){ #miniHud { display:block; } }
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
        <span class="ctl-label" id="speedLabel">speed</span>
        <select id="speed" aria-labelledby="speedLabel">
          <option value="0.15">0.15x</option>
          <option value="0.25" selected>0.25x</option>
          <option value="0.5">0.5x</option>
          <option value="1">1x</option>
          <option value="2">2x</option>
          <option value="4">4x</option>
        </select>
        <button id="trails" aria-pressed="true">Trails: on</button>
        <input id="scrub" type="range" min="0" max="__TMAX__" value="0" aria-label="Timestep">
        <span class="step" id="stepLabel">timestep 0 / __TMAX__</span>
      </div>
      <p class="hint">Space plays and pauses. Jump in time with the slider or by clicking
      either chart. Load a formation by clicking its card or dragging it onto the field.</p>
      <div id="miniHud"><b id="hudBC">BC1 Driving</b> &nbsp; swarm <span id="hudM1">0.0</span> u
        from AOI &nbsp; standoff breached <span id="hudBreach">0%</span></div>
      <div class="pattern-strip">
        <h2>Starting formation</h2>
        <div class="patterns" id="patterns"></div>
      </div>
    </div>
    <div class="side">
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
        <canvas id="spark" width="252" height="86" role="slider" aria-label="Distance timeline, click to jump"></canvas>
        <p class="chart-hint">click or drag on the chart to jump to that timestep</p>
        <p class="stat">standoff breached: <b id="breachPct">0%</b> of timesteps so far</p>
      </div>
      <div class="card">
        <h2>Swarm cohesion over time</h2>
        <canvas id="cluststrip" width="252" height="40" role="slider" aria-label="Cohesion timeline, click to jump"></canvas>
        <p class="stat">clustered: <b id="clusPct">0%</b> of timesteps so far</p>
      </div>
      <div class="card">
        <h2>Legend</h2>
        <div class="legend">
          <span><i class="dot" style="background:var(--attacker)"></i>attacker swarm (N = __N__)</span>
          <span><i class="dot" style="background:var(--defender)"></i>defender (single sheepdog)</span>
          <span><svg class="target" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="none" stroke="#e4604e"/><circle cx="6" cy="6" r="1.8" fill="#e4604e"/></svg>AOI: Area of Interest, the protected point the attackers try to reach</span>
          <span><i class="ring"></i>target standoff (__EQ__ units): the defence is holding while the swarm stays outside it</span>
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
let introTimer = null, firstIntro = true;

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

function tag(x, y, text, color, align) {
  cx.font = '600 12px "Avenir Next","Segoe UI",sans-serif';
  cx.textAlign = align || 'left';
  const w = cx.measureText(text).width;
  const bx = align === 'right' ? x - w - 6 : x - 3;
  cx.fillStyle = 'rgba(13,19,25,.85)';
  cx.fillRect(bx, y - 11, w + 8, 16);
  cx.fillStyle = color;
  cx.fillText(text, x, y + 2);
  cx.textAlign = 'left';
}

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

  // Teaching labels on the scene itself while the intro hold is up: the observer
  // decodes the field exactly when there is time to read it.
  if (!document.getElementById('overlay').hidden) {
    tag(X(r[1]) + 13, Y(r[2]) - 8, 'defender', css('--defender'));
    tag(X(gx) + 12, Y(gy) - 10, 'attackers', css('--attacker'));
    tag(X(AOI[0]), Y(AOI[1]) - 20, 'protected point', css('--aoi'), 'right');
    tag(X(AOI[0]) + EQ * S * 0.7071, Y(AOI[1]) - EQ * S * 0.7071 - 6,
        'target standoff', '#8b98a5');
  }

  document.getElementById('bcChip').textContent = BC[r[3] - 1];
  document.getElementById('hudBC').textContent = BC[r[3] - 1];
  document.getElementById('mM1').textContent = m1s[t].toFixed(1) + ' u';
  document.getElementById('hudM1').textContent = m1s[t].toFixed(1);
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

  drawDistanceChart();
  drawCohesionStrip();
}

// Distance timeline: full run drawn faintly for context, progress emphasised,
// breach segments red AND shaded (redundant position encoding below the dashed
// line), playhead cursor, sparse axis labels. Clickable to seek.
function drawDistanceChart() {
  sx.clearRect(0, 0, sp.width, sp.height);
  const padB = 14, padT = 6;
  const mmax = Math.max(EQ * 1.2, Math.max(...m1s) * 1.05);
  const gy = v => sp.height - padB - (v / mmax) * (sp.height - padB - padT);
  const gx = k => k / (DATA.length - 1) * sp.width;
  // axes
  sx.fillStyle = '#5b6875'; sx.font = '9px ui-monospace,monospace';
  sx.fillText('0', 2, sp.height - 3);
  sx.fillText(String(DATA[DATA.length - 1][0]), sp.width - 20, sp.height - 3);
  sx.fillText(mmax.toFixed(0) + 'u', 2, padT + 7);
  sx.strokeStyle = '#232e3b';
  sx.beginPath(); sx.moveTo(0, gy(0)); sx.lineTo(sp.width, gy(0)); sx.stroke();
  // standoff line + breach shading (full run, faint)
  sx.strokeStyle = '#4a5866'; sx.setLineDash([3, 3]);
  sx.beginPath(); sx.moveTo(0, gy(EQ)); sx.lineTo(sp.width, gy(EQ)); sx.stroke();
  sx.setLineDash([]);
  sx.fillStyle = '#77828f';
  sx.fillText('target standoff ' + EQ.toFixed(1), 4, gy(EQ) - 3);
  // full-run context line
  sx.strokeStyle = 'rgba(224,170,94,.22)'; sx.lineWidth = 1;
  sx.beginPath();
  for (let k = 0; k < DATA.length; k++)
    k ? sx.lineTo(gx(k), gy(m1s[k])) : sx.moveTo(gx(k), gy(m1s[k]));
  sx.stroke();
  // progress line with breach emphasis
  let breaches = 0;
  for (let k = 1; k <= t; k++) {
    const breach = m1s[k] < EQ;
    if (breach) {
      sx.fillStyle = 'rgba(228,96,78,.18)';
      sx.fillRect(gx(k - 1), gy(EQ), gx(k) - gx(k - 1) + 0.5, gy(m1s[k]) - gy(EQ));
    }
    sx.strokeStyle = breach ? css('--aoi') : css('--attacker');
    sx.lineWidth = breach ? 2 : 1.4;
    sx.beginPath(); sx.moveTo(gx(k - 1), gy(m1s[k - 1])); sx.lineTo(gx(k), gy(m1s[k])); sx.stroke();
  }
  for (let k = 0; k <= t; k++) if (m1s[k] < EQ) breaches++;
  // playhead
  sx.strokeStyle = '#8b98a5';
  sx.beginPath(); sx.moveTo(gx(t), padT); sx.lineTo(gx(t), sp.height - padB); sx.stroke();
  sx.fillStyle = css('--attacker');
  sx.beginPath(); sx.arc(gx(t), gy(m1s[t]), 2.5, 0, 7); sx.fill();
  const pct = (100 * breaches / (t + 1)).toFixed(0) + '%';
  document.getElementById('breachPct').textContent = pct;
  document.getElementById('hudBreach').textContent = pct;
}

// Cohesion timeline: clustered ticks sit ABOVE the baseline (green), broken ones
// drop BELOW it (red), so state reads by position as well as colour. Clickable.
function drawCohesionStrip() {
  csx.clearRect(0, 0, cs.width, cs.height);
  const mid = 20;
  csx.strokeStyle = '#3a4653';
  csx.beginPath(); csx.moveTo(0, mid); csx.lineTo(cs.width, mid); csx.stroke();
  csx.fillStyle = '#5b6875'; csx.font = '9px ui-monospace,monospace';
  csx.fillText('0', 2, cs.height - 1);
  csx.fillText(String(DATA[DATA.length - 1][0]), cs.width - 20, cs.height - 1);
  const bw = Math.max(1, cs.width / DATA.length);
  // full-run context, faint
  for (let k = 0; k < DATA.length; k++) {
    csx.fillStyle = clustered[k] ? 'rgba(127,176,105,.18)' : 'rgba(228,96,78,.18)';
    csx.fillRect(k / (DATA.length - 1) * cs.width, clustered[k] ? mid - 9 : mid + 1, bw, 8);
  }
  let clus = 0;
  for (let k = 0; k <= t; k++) {
    if (clustered[k]) clus++;
    csx.fillStyle = clustered[k] ? css('--good') : css('--aoi');
    csx.fillRect(k / (DATA.length - 1) * cs.width, clustered[k] ? mid - 9 : mid + 1, bw, 8);
  }
  csx.strokeStyle = '#8b98a5';
  csx.beginPath();
  csx.moveTo(t / (DATA.length - 1) * cs.width, 2);
  csx.lineTo(t / (DATA.length - 1) * cs.width, cs.height - 10);
  csx.stroke();
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
  // Hold on the starting formation (labels drawn on the field) so the observer can
  // decode the scene, then autoplay. First load holds longer; switching formations
  // holds briefly; clicking the banner starts immediately.
  setPlaying(false);
  t = 0;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const msg = document.getElementById('overlayMsg');
  const name = PATTERNS[runKey] ? PATTERNS[runKey].name : runKey;
  document.getElementById('overlay').hidden = false;
  draw();
  if (reduced) {
    msg.innerHTML = 'Starting formation: <b>' + runKey + ' ' + name + '</b>. Press Play to run.';
    return;
  }
  let s = firstIntro ? 5 : 2;
  firstIntro = false;
  const tick = () => {
    msg.innerHTML = 'Starting formation: <b>' + runKey + ' ' + name +
      '</b> &nbsp;-&nbsp; playing in ' + s + 's &nbsp;<small>(click to start now)</small>';
    if (s-- > 0) { introTimer = setTimeout(tick, 1000); }
    else { hideOverlay(); setPlaying(true); }
  };
  tick();
}
document.getElementById('overlay').addEventListener('click', () => setPlaying(true));

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

// charts are seekable timelines: click or drag to jump
function makeSeekable(canvas) {
  let down = false;
  const seek = e => {
    const rect = canvas.getBoundingClientRect();
    const frac = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    t = Math.round(frac * (DATA.length - 1));
    setPlaying(false); hideOverlay(); draw();
  };
  canvas.addEventListener('pointerdown', e => {
    down = true; seek(e);
    try { canvas.setPointerCapture(e.pointerId); } catch (_) { /* synthetic pointers */ }
  });
  canvas.addEventListener('pointermove', e => { if (down) seek(e); });
  canvas.addEventListener('pointerup', () => { down = false; });
}
makeSeekable(sp);
makeSeekable(cs);

document.getElementById('play').onclick = () => {
  if (!playing && t >= DATA.length - 1) t = 0;
  setPlaying(!playing);
};
document.getElementById('reset').onclick = () => { t = 0; setPlaying(true); draw(); };
document.getElementById('trails').onclick = e => {
  trails = !trails;
  e.target.setAttribute('aria-pressed', trails);
  e.target.textContent = 'Trails: ' + (trails ? 'on' : 'off');
  draw();
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
