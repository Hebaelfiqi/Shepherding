#!/usr/bin/env python3
"""Build a self-contained HTML replay of an adversarial run from its positions CSV.

Usage:
  python3 tools/make_replay.py <..._Positions.csv> [-o replay.html] [--aoi 25 41.667]

The simulator writes the positions file next to the per-step metrics on every single
(non-experiment) adversarial run:
  ./build/shepherd_sim InputFiles/Config_Adversarial.xml
  python3 tools/make_replay.py Config_Adversarial_AdversarialPerStep_Positions.csv
Open the resulting replay.html in any browser. Standard library only.
"""
import argparse
import csv
import json
import math

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
  .wrap { width:min(1060px,100%); }
  header { display:flex; justify-content:space-between; align-items:baseline;
           flex-wrap:wrap; gap:4px 16px; margin-bottom:14px; }
  h1 { font-size:17px; font-weight:600; letter-spacing:.01em; }
  header .sub { color:var(--muted); font-size:12.5px; }
  .layout { display:grid; grid-template-columns:minmax(0,1fr) 264px; gap:14px; }
  @media (max-width:820px){ .layout { grid-template-columns:1fr; } }
  .stage { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:12px; }
  canvas { width:100%; height:auto; display:block; border-radius:3px; }
  .controls { display:flex; align-items:center; gap:10px; margin-top:12px; flex-wrap:wrap; }
  button { background:#202b38; color:var(--ink); border:1px solid var(--line); border-radius:4px;
           font:inherit; font-size:13px; padding:5px 14px; cursor:pointer; }
  button:hover { border-color:#3a4a5d; }
  button:focus-visible { outline:2px solid var(--defender); outline-offset:1px; }
  button[aria-pressed="true"] { border-color:var(--defender); color:var(--defender); }
  input[type=range] { flex:1; min-width:120px; accent-color:var(--defender); }
  .step { font:13px/1 ui-monospace,"Cascadia Code",Menlo,monospace;
          font-variant-numeric:tabular-nums; color:var(--muted); min-width:86px; }
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
  .legend { display:grid; gap:6px; font-size:12.5px; }
  .legend span { display:flex; align-items:center; gap:8px; }
  .dot { width:9px; height:9px; border-radius:50%; flex:none; }
  #spark { width:100%; height:64px; display:block; }
  .hint { color:var(--muted); font-size:11.5px; margin-top:10px; }
  select { background:#202b38; color:var(--ink); border:1px solid var(--line);
           border-radius:4px; font:inherit; font-size:13px; padding:4px 6px; }
</style>
<div class="wrap">
  <header>
    <h1>Adversarial patrolling replay</h1>
    <span class="sub">__SUBTITLE__</span>
  </header>
  <div class="layout">
    <div class="stage">
      <canvas id="field" width="760" height="760"></canvas>
      <div class="controls">
        <button id="play" aria-pressed="false">Play</button>
        <button id="reset">Restart</button>
        <select id="speed" aria-label="Playback speed">
          <option value="2">0.5x</option><option value="1" selected>1x</option>
          <option value="0.5">2x</option><option value="0.25">4x</option>
        </select>
        <button id="trails" aria-pressed="true">Trails</button>
        <input id="scrub" type="range" min="0" max="__TMAX__" value="0" aria-label="Timestep">
        <span class="step" id="stepLabel">t = 0 / __TMAX__</span>
      </div>
      <p class="hint">Space plays and pauses. Drag the slider to scrub. The dashed ring is the
      repulsion-attraction equilibrium (__EQ__ units from the defender's post at the AOI).</p>
    </div>
    <div class="side">
      <div class="card">
        <h2>Defender decision</h2>
        <span class="bc-chip" id="bcChip">BC1 Driving</span>
      </div>
      <div class="card">
        <h2>Telemetry</h2>
        <dl class="metrics">
          <dt>swarm to AOI</dt><dd id="mM1">0.0</dd>
          <dt>defender to AOI</dt><dd id="mDog">0.0</dd>
          <dt>defender angle M3</dt><dd id="mM3">0.00</dd>
          <dt>clustered</dt><dd id="mClus">yes</dd>
        </dl>
      </div>
      <div class="card">
        <h2>Swarm to AOI distance</h2>
        <canvas id="spark" width="236" height="64"></canvas>
      </div>
      <div class="card">
        <h2>Legend</h2>
        <div class="legend">
          <span><i class="dot" style="background:var(--attacker)"></i>attacker swarm (N = __N__)</span>
          <span><i class="dot" style="background:var(--defender)"></i>defender</span>
          <span><i class="dot" style="background:var(--aoi)"></i>area of interest</span>
          <span><i class="dot" style="background:none;border:1px dashed var(--muted)"></i>standoff equilibrium</span>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
const DATA = __DATA__;
const AOI = __AOI__, FIELD = __FIELD__, EQ = __EQ__, FN = __FN__;
const BC = __BCLABELS__;
const N = (DATA[0].length - 2) / 2 - 1;
const cv = document.getElementById('field'), cx = cv.getContext('2d');
const sp = document.getElementById('spark'), sx = sp.getContext('2d');
const S = cv.width / FIELD;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let t = 0, playing = false, acc = 0, last = 0, trails = true;

const m1s = DATA.map(r => {
  let gx = 0, gy = 0;
  for (let i = 0; i < N; i++) { gx += r[4 + 2 * i]; gy += r[5 + 2 * i]; }
  return Math.hypot(gx / N - AOI[0], gy / N - AOI[1]);
});

function X(x) { return x * S; }
function Y(y) { return cv.height - y * S; }

function draw() {
  cx.fillStyle = '#0d1319';
  cx.fillRect(0, 0, cv.width, cv.height);
  cx.strokeStyle = '#1c2632'; cx.lineWidth = 1;
  for (let g = 10; g < FIELD; g += 10) {
    cx.beginPath(); cx.moveTo(X(g), 0); cx.lineTo(X(g), cv.height); cx.stroke();
    cx.beginPath(); cx.moveTo(0, Y(g)); cx.lineTo(cv.width, Y(g)); cx.stroke();
  }
  const r = DATA[t];
  // trails
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
  // equilibrium ring + AOI
  cx.setLineDash([5, 5]); cx.strokeStyle = '#4a5866';
  cx.beginPath(); cx.arc(X(AOI[0]), Y(AOI[1]), EQ * S, 0, 7); cx.stroke();
  cx.setLineDash([]);
  cx.strokeStyle = css('--aoi'); cx.lineWidth = 1.6;
  const ax = X(AOI[0]), ay = Y(AOI[1]);
  cx.beginPath(); cx.moveTo(ax - 7, ay); cx.lineTo(ax + 7, ay);
  cx.moveTo(ax, ay - 7); cx.lineTo(ax, ay + 7); cx.stroke();
  cx.beginPath(); cx.arc(ax, ay, 3.5, 0, 7); cx.stroke();
  // GCM ray
  let gx = 0, gy = 0;
  for (let i = 0; i < N; i++) { gx += r[4 + 2 * i]; gy += r[5 + 2 * i]; }
  gx /= N; gy /= N;
  cx.strokeStyle = 'rgba(224,170,94,.25)';
  cx.beginPath(); cx.moveTo(ax, ay); cx.lineTo(X(gx), Y(gy)); cx.stroke();
  // sheep
  cx.fillStyle = css('--attacker');
  for (let i = 0; i < N; i++) {
    cx.beginPath(); cx.arc(X(r[4 + 2 * i]), Y(r[5 + 2 * i]), 4, 0, 7); cx.fill();
  }
  // GCM marker
  cx.strokeStyle = 'rgba(224,170,94,.6)';
  cx.beginPath(); cx.arc(X(gx), Y(gy), 6.5, 0, 7); cx.stroke();
  // defender
  cx.fillStyle = css('--defender');
  cx.beginPath(); cx.arc(X(r[1]), Y(r[2]), 5.5, 0, 7); cx.fill();
  cx.strokeStyle = 'rgba(98,182,203,.45)';
  cx.beginPath(); cx.arc(X(r[1]), Y(r[2]), 9.5, 0, 7); cx.stroke();

  // telemetry
  document.getElementById('bcChip').textContent = BC[r[3] - 1];
  document.getElementById('mM1').textContent = m1s[t].toFixed(1) + ' u';
  const dDog = Math.hypot(r[1] - AOI[0], r[2] - AOI[1]);
  document.getElementById('mDog').textContent = dDog.toFixed(1) + ' u';
  const v1 = [gx - AOI[0], gy - AOI[1]], v2 = [r[1] - AOI[0], r[2] - AOI[1]];
  const m3 = Math.acos(Math.min(1, Math.max(-1,
    (v1[0] * v2[0] + v1[1] * v2[1]) / (Math.hypot(...v1) * Math.hypot(...v2) || 1))));
  document.getElementById('mM3').textContent = m3.toFixed(2) + ' rad';
  let clustered = true;
  for (let i = 0; i < N; i++)
    if (Math.hypot(r[4 + 2 * i] - gx, r[5 + 2 * i] - gy) > FN) { clustered = false; break; }
  const clusEl = document.getElementById('mClus');
  clusEl.textContent = clustered ? 'yes' : 'no';
  clusEl.style.color = clustered ? css('--good') : css('--aoi');
  document.getElementById('stepLabel').textContent = 't = ' + r[0] + ' / ' + DATA[DATA.length - 1][0];
  document.getElementById('scrub').value = t;

  // sparkline
  sx.clearRect(0, 0, sp.width, sp.height);
  const mmax = Math.max(...m1s) * 1.05;
  sx.strokeStyle = '#33404f'; sx.setLineDash([3, 3]);
  const eqy = sp.height - 4 - (EQ / mmax) * (sp.height - 8);
  sx.beginPath(); sx.moveTo(0, eqy); sx.lineTo(sp.width, eqy); sx.stroke(); sx.setLineDash([]);
  sx.strokeStyle = css('--attacker'); sx.lineWidth = 1.4; sx.beginPath();
  for (let k = 0; k <= t; k++) {
    const px = k / (DATA.length - 1) * sp.width;
    const py = sp.height - 4 - (m1s[k] / mmax) * (sp.height - 8);
    k ? sx.lineTo(px, py) : sx.moveTo(px, py);
  }
  sx.stroke();
  sx.fillStyle = css('--attacker');
  const ex = t / (DATA.length - 1) * sp.width;
  sx.beginPath(); sx.arc(ex, sp.height - 4 - (m1s[t] / mmax) * (sp.height - 8), 2.5, 0, 7); sx.fill();
}

function frame(ts) {
  if (playing) {
    if (!last) last = ts;
    acc += (ts - last);
    const speed = parseFloat(document.getElementById('speed').value) * 40;
    while (acc > speed) {
      acc -= speed;
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
}
document.getElementById('play').onclick = () => {
  if (!playing && t >= DATA.length - 1) t = 0;
  setPlaying(!playing);
};
document.getElementById('reset').onclick = () => { t = 0; setPlaying(true); draw(); };
document.getElementById('trails').onclick = e => {
  trails = !trails; e.target.setAttribute('aria-pressed', trails); draw();
};
document.getElementById('scrub').oninput = e => { t = +e.target.value; setPlaying(false); draw(); };
document.addEventListener('keydown', e => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
    e.preventDefault(); document.getElementById('play').click();
  }
});
draw();
requestAnimationFrame(frame);
if (!matchMedia('(prefers-reduced-motion: reduce)').matches) setPlaying(true);
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("positions_csv")
    ap.add_argument("-o", "--out", default="replay.html")
    ap.add_argument("--aoi", nargs=2, type=float, default=[25.0, 41.667])
    ap.add_argument("--field", type=float, default=50.0)
    ap.add_argument("--fn", type=float, default=8.944, help="clustering radius fN")
    ap.add_argument("--eq", type=float, default=13.86, help="standoff equilibrium radius")
    ap.add_argument("--subtitle", default="")
    args = ap.parse_args()

    rows = []
    with open(args.positions_csv) as f:
        rdr = csv.reader(f)
        next(rdr)
        for row in rdr:
            rows.append([round(float(v), 3) for v in row])
    n = (len(rows[0]) - 4) // 2
    subtitle = args.subtitle or (
        f"{len(rows)} timesteps, {n} attackers, one defender guarding the AOI at "
        f"({args.aoi[0]:g}, {args.aoi[1]:g})")

    html = (TEMPLATE
            .replace("__DATA__", json.dumps(rows, separators=(",", ":")))
            .replace("__AOI__", json.dumps(args.aoi))
            .replace("__FIELD__", json.dumps(args.field))
            .replace("__EQ__", json.dumps(args.eq))
            .replace("__FN__", json.dumps(args.fn))
            .replace("__BCLABELS__", json.dumps(BC_LABELS))
            .replace("__TMAX__", str(len(rows) - 1))
            .replace("__N__", str(n))
            .replace("__SUBTITLE__", subtitle))
    with open(args.out, "w") as f:
        f.write(html)
    print(f"wrote {args.out} ({len(rows)} steps, {n} attackers)")


if __name__ == "__main__":
    main()
