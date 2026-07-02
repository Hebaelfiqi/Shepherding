#!/usr/bin/env python3
"""Generate the report figures from results/perstep.csv as standalone SVG files.

Standard library only (matplotlib is not assumed on the machine). Produces:
  results/fig5_gcm_distance.svg   mean GCM-to-AOI distance over time (Fig 5 analogue)
  results/fig6_defender_angle.svg mean defender-side angle M3 over time (Fig 6 analogue)
  results/behaviour_usage.svg     behaviour usage bar chart

Usage: python3 tools/plot.py [results_dir]
"""
import csv
import math
import sys


def read_perstep(path):
    by_t = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            t = int(row["t"])
            by_t.setdefault(t, {"M1": [], "M3": []})
            by_t[t]["M1"].append(float(row["M1_gcm_aoi_dist"]))
            by_t[t]["M3"].append(float(row["M3_defender_angle"]))
    return by_t


def svg_line_chart(path, title, xlabel, ylabel, series, hline=None, ymax=None):
    """series: list of (label, colour, [(x, y)])"""
    W, H, ml, mr, mt, mb = 720, 420, 60, 20, 40, 50
    pw, ph = W - ml - mr, H - mt - mb
    xs = [p[0] for _, _, pts in series for p in pts]
    ys = [p[1] for _, _, pts in series for p in pts]
    x0, x1 = min(xs), max(xs)
    y0 = 0.0
    y1 = ymax if ymax is not None else max(ys) * 1.08
    if hline is not None:
        y1 = max(y1, hline * 1.15)

    def X(x):
        return ml + (x - x0) / (x1 - x0) * pw

    def Y(y):
        return mt + ph - (y - y0) / (y1 - y0) * ph

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{W/2}" y="20" text-anchor="middle" font-size="15">{title}</text>']
    # axes and grid
    for i in range(6):
        yv = y0 + (y1 - y0) * i / 5
        out.append(f'<line x1="{ml}" y1="{Y(yv)}" x2="{W-mr}" y2="{Y(yv)}" stroke="#ddd"/>')
        out.append(f'<text x="{ml-6}" y="{Y(yv)+4}" text-anchor="end">{yv:.1f}</text>')
    for i in range(6):
        xv = x0 + (x1 - x0) * i / 5
        out.append(f'<text x="{X(xv)}" y="{H-mb+18}" text-anchor="middle">{xv:.0f}</text>')
    out.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{H-mb}" stroke="black"/>')
    out.append(f'<line x1="{ml}" y1="{H-mb}" x2="{W-mr}" y2="{H-mb}" stroke="black"/>')
    out.append(f'<text x="{W/2}" y="{H-10}" text-anchor="middle">{xlabel}</text>')
    out.append(f'<text x="16" y="{H/2}" text-anchor="middle" transform="rotate(-90 16 {H/2})">{ylabel}</text>')
    if hline is not None:
        out.append(f'<line x1="{ml}" y1="{Y(hline)}" x2="{W-mr}" y2="{Y(hline)}" '
                   f'stroke="#c00" stroke-dasharray="6 4"/>')
        out.append(f'<text x="{W-mr-4}" y="{Y(hline)-5}" text-anchor="end" fill="#c00">pi/2</text>')
    lx = ml + 12
    for label, colour, pts in series:
        d = " ".join(f'{"M" if i == 0 else "L"}{X(x):.1f},{Y(y):.1f}' for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="1.6"/>')
        out.append(f'<line x1="{lx}" y1="{mt+10}" x2="{lx+22}" y2="{mt+10}" stroke="{colour}" stroke-width="2"/>')
        out.append(f'<text x="{lx+27}" y="{mt+14}">{label}</text>')
        lx += 30 + 8 * len(label)
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out))
    print("wrote", path)


def svg_bar_chart(path, title, labels, values):
    W, H, ml, mt, mb = 560, 360, 60, 40, 60
    pw, ph = W - ml - 20, H - mt - mb
    vmax = max(values) * 1.15
    bw = pw / len(values) * 0.6
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{W/2}" y="20" text-anchor="middle" font-size="15">{title}</text>']
    for i in range(5):
        yv = vmax * i / 4
        y = mt + ph - yv / vmax * ph
        out.append(f'<line x1="{ml}" y1="{y}" x2="{W-20}" y2="{y}" stroke="#ddd"/>')
        out.append(f'<text x="{ml-6}" y="{y+4}" text-anchor="end">{yv:.0f}%</text>')
    for i, (lab, v) in enumerate(zip(labels, values)):
        cx = ml + pw * (i + 0.5) / len(values)
        h = v / vmax * ph
        out.append(f'<rect x="{cx-bw/2}" y="{mt+ph-h}" width="{bw}" height="{h}" fill="#4477aa"/>')
        out.append(f'<text x="{cx}" y="{mt+ph-h-5}" text-anchor="middle">{v:.1f}%</text>')
        out.append(f'<text x="{cx}" y="{H-mb+18}" text-anchor="middle">{lab}</text>')
    out.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="black"/>')
    out.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{W-20}" y2="{mt+ph}" stroke="black"/>')
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out))
    print("wrote", path)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "results"
    by_t = read_perstep(f"{outdir}/perstep.csv")
    ts = sorted(by_t)
    mean_m1 = [(t, sum(by_t[t]["M1"]) / len(by_t[t]["M1"])) for t in ts]
    max_m1 = [(t, max(by_t[t]["M1"])) for t in ts]
    min_m1 = [(t, min(by_t[t]["M1"])) for t in ts]
    mean_m3 = [(t, sum(by_t[t]["M3"]) / len(by_t[t]["M3"])) for t in ts]
    max_m3 = [(t, max(by_t[t]["M3"])) for t in ts]

    svg_line_chart(f"{outdir}/fig5_gcm_distance.svg",
                   "GCM-to-AOI distance over time, 27 conditions (Fig 5 analogue)",
                   "timestep", "distance (units)",
                   [("mean", "#4477aa", mean_m1),
                    ("min", "#99bb55", min_m1),
                    ("max", "#ee6677", max_m1)])
    svg_line_chart(f"{outdir}/fig6_defender_angle.svg",
                   "Defender-side angle M3 over time (Fig 6 analogue)",
                   "timestep", "angle (rad)",
                   [("mean", "#4477aa", mean_m3),
                    ("max", "#ee6677", max_m3)],
                   hline=math.pi / 2, ymax=math.pi)

    labels, values = [], []
    with open(f"{outdir}/behaviour_usage.csv") as f:
        section = 0
        for row in csv.reader(f):
            if row and row[0] == "behaviour":
                section = 1
                continue
            if section == 1 and len(row) == 3:
                labels.append(row[0])
                values.append(float(row[2]))
    svg_bar_chart(f"{outdir}/behaviour_usage.svg",
                  "Behaviour usage (weighted share of chosen BCs)", labels, values)


if __name__ == "__main__":
    main()
