#!/usr/bin/env python
"""Experiment 16 -- per-zone morphology sheets for all 224 zones.

Experiment 11 produced the city-wide map: 60,460 windows as coloured dots. That
shows THAT morphological structure exists and varies, but it is close to unreadable
as a description of any particular place -- you cannot look at it and say what
Zone_DH168 is actually like.

This is the per-zone counterpart, and the direct modern replacement for the old
notebook's 822 per-zone betweenness hierarchy plots. One sheet per zone:

  LEFT   the zone's 2km core with its street network drawn, divided into a 5x5
         lattice of 400m subgrids, each tinted by its grid-score and labelled.
         Shows WHERE the grid-like parts of the zone are.

  RIGHT  the same 25 subgrids rendered individually in the same spatial
         positions, so the fabric of each part is legible on its own. Shows WHAT
         each part actually looks like.

This produces figures, not findings. Every number on the sheets comes from the
measure established in Experiments 10-11; nothing new is claimed here.

ONE DIFFERENCE FROM THE ANALYSIS, DELIBERATE: Experiment 11 scores a SLIDING
window at 100m stride, because a fixed lattice dices a grid that spans a seam and
penalises it. For a figure that is the wrong trade -- overlapping windows cannot
be drawn as discrete labelled cells. These sheets therefore use a non-overlapping
5x5 lattice, which is more legible and slightly less faithful. Zone-level summary
statistics quoted on each sheet come from the sliding-window analysis, not from
the 25 lattice cells, so they match Experiment 11.

Usage:
    python experiments/16_per_zone_morphology/run.py            # all 224 zones
    python experiments/16_per_zone_morphology/run.py --zones Zone_DH168 Zone_DH116
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "11_city_mixture_map"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

from run import (CELL_M, CORE_HALF_M, HALF_EXTENT_M, N_CELL, ZONES_DIR, META_CSV,
                 build_null_lookup, grid_scores_batch, lookup, zone_cell_data)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "zones")
BLOCK = 4                       # 4 x 100m cells = one 400m subgrid
LO = int((HALF_EXTENT_M - CORE_HALF_M) / CELL_M)     # 8
NSUB = int(2 * CORE_HALF_M / CELL_M / BLOCK)         # 5
MIN_ROAD_M = 500.0


def zone_segments(zone_dir, cx, cy):
    """Street segments as (x1,y1,x2,y2) arrays, in metres relative to zone centre."""
    nodes = pd.read_csv(os.path.join(zone_dir, "nodes.csv"))
    links = pd.read_csv(os.path.join(zone_dir, "links.csv"))
    px = pd.Series(nodes["x_utm"].values, index=nodes["node_id"].values)
    py = pd.Series(nodes["y_utm"].values, index=nodes["node_id"].values)
    m = links["from_node"].isin(px.index) & links["to_node"].isin(px.index)
    fn, tn = links.loc[m, "from_node"].values, links.loc[m, "to_node"].values
    return (px[fn].values - cx, py[fn].values - cy,
            px[tn].values - cx, py[tn].values - cy)


def subgrid_scores(H_cells, C_cells, ns, nmean, np95):
    """Aggregate the 100m cell histograms into a 5x5 lattice of 400m subgrids."""
    score = np.full((NSUB, NSUB), np.nan)
    excess = np.full((NSUB, NSUB), np.nan)
    road = np.zeros((NSUB, NSUB))
    for r in range(NSUB):
        for c in range(NSUB):
            r0, c0 = LO + r * BLOCK, LO + c * BLOCK
            h = H_cells[r0:r0 + BLOCK, c0:c0 + BLOCK].sum(axis=(0, 1))
            n = C_cells[r0:r0 + BLOCK, c0:c0 + BLOCK].sum()
            tot = h.sum()
            road[r, c] = tot
            if tot <= 0 or n < 3:
                continue
            s = grid_scores_batch((h / tot)[None, :])[0]
            score[r, c] = s
            excess[r, c] = s - lookup(ns, nmean, n)
    return score, excess, road


def draw_network(ax, seg, x0, x1, y0, y1, lw=0.55, color="#222"):
    sx, sy, ex, ey = seg
    keep = ~((np.maximum(sx, ex) < x0) | (np.minimum(sx, ex) > x1) |
             (np.maximum(sy, ey) < y0) | (np.minimum(sy, ey) > y1))
    if keep.any():
        ax.add_collection(LineCollection(
            np.stack([np.stack([sx[keep], sy[keep]], 1),
                      np.stack([ex[keep], ey[keep]], 1)], 1),
            colors=color, linewidths=lw))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])


def make_sheet(zone_id, seg, score, excess, road, zinfo, path):
    cmap = plt.get_cmap("RdYlBu_r")
    half = CORE_HALF_M
    fig = plt.figure(figsize=(15.5, 8.2))
    gs = fig.add_gridspec(NSUB, 11, wspace=0.08, hspace=0.18,
                          left=.035, right=.975, top=.87, bottom=.05)

    # ---- left: the zone core with the 5x5 lattice --------------------------
    axm = fig.add_subplot(gs[:, 0:5])
    draw_network(axm, seg, -half, half, -half, half, lw=0.6)
    for r in range(NSUB):
        for c in range(NSUB):
            x = -half + c * 400.0
            y = half - (r + 1) * 400.0
            e = excess[r, c]
            if np.isnan(e):
                fc, txt = "0.85", "--"
            else:
                fc = cmap(np.clip((e + 0.35) / 0.85, 0, 1))
                txt = f"{score[r, c]:.2f}"
            axm.add_patch(plt.Rectangle((x, y), 400, 400, facecolor=fc, alpha=.42,
                                        edgecolor="k", linewidth=.7, zorder=2))
            axm.text(x + 200, y + 200, txt, ha="center", va="center",
                     fontsize=11, weight="bold", zorder=3)
    axm.set_title("where the grid-like parts are\n(warm = more grid-like, "
                  "number = grid-score)", fontsize=10.5)
    fig.text(0.755, 0.895, "what each part looks like, on its own",
             fontsize=10.5, ha="center")

    # ---- right: each subgrid on its own, same positions --------------------
    for r in range(NSUB):
        for c in range(NSUB):
            ax = fig.add_subplot(gs[r, 6 + c])
            x0 = -half + c * 400.0
            y0 = half - (r + 1) * 400.0
            draw_network(ax, seg, x0, x0 + 400, y0, y0 + 400, lw=0.75)
            e = excess[r, c]
            if np.isnan(e):
                ax.set_title("too sparse", fontsize=7.5, color="#999", pad=2)
                for s in ax.spines.values():
                    s.set_color("#ccc")
            else:
                ax.set_title(f"{score[r, c]:.2f}", fontsize=8.5, pad=2,
                             color="#111")
                for s in ax.spines.values():
                    s.set_color(cmap(np.clip((e + 0.35) / 0.85, 0, 1)))
                    s.set_linewidth(2.2)

    valid = ~np.isnan(excess)
    mix = float((excess[valid] > 0).mean()) if valid.any() else float("nan")
    fig.suptitle(
        f"{zone_id}   —   2 km core in 400 m subgrids\n"
        f"grid-like subgrids: {int((excess[valid] > 0).sum())}/{int(valid.sum())}"
        f"   ·   zone mixture ratio (sliding-window analysis): {zinfo}",
        fontsize=13, y=.965)
    fig.savefig(path, dpi=105, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return mix


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zones", nargs="*", default=None)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()

    meta = pd.read_csv(META_CSV).set_index("zone_id")
    available = sorted(os.listdir(ZONES_DIR))
    zones = args.zones or [z for z in available if z in meta.index]
    print(f"generating sheets for {len(zones)} zones")

    # zone-level summary from the sliding-window analysis, so sheets agree with Exp 11
    zf = os.path.join(HERE, "..", "11_city_mixture_map", "zone_final.csv")
    zsum = pd.read_csv(zf).set_index("zone_id") if os.path.exists(zf) else None

    pool = pd.read_csv(os.path.join(ZONES_DIR, zones[0], "links.csv"))["length_m"].values
    pool = pool[pool > 0]
    print("building null lookup ...")
    ns, nmean, np95 = build_null_lookup(pool)

    rows = []
    for i, z in enumerate(zones):
        if i % 25 == 0:
            print(f"  [{i:>3}/{len(zones)}]  {z}   ({time.time()-t0:.0f}s)")
        cx = float(meta.loc[z, "centroid_x_utm"]); cy = float(meta.loc[z, "centroid_y_utm"])
        zd = os.path.join(ZONES_DIR, z)
        data = zone_cell_data(zd, cx, cy)
        if data is None:
            continue
        H_cells, C_cells, _ = data
        score, excess, road = subgrid_scores(H_cells, C_cells, ns, nmean, np95)
        if zsum is not None and z in zsum.index:
            zinfo = f"{zsum.loc[z, 'med_excess']:+.3f} median excess"
        else:
            zinfo = "n/a"
        seg = zone_segments(zd, cx, cy)
        mix = make_sheet(z, seg, score, excess, road, zinfo,
                         os.path.join(OUT, f"{z}_morphology.png"))
        rows.append({"zone_id": z, "lattice_mixture_ratio": mix,
                     "n_valid_subgrids": int((~np.isnan(excess)).sum()),
                     "mean_subgrid_score": float(np.nanmean(score))})

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(HERE, "per_zone_lattice_summary.csv"), index=False)
    print(f"\n{len(df)} sheets written to {OUT} in {time.time()-t0:.0f}s")
    print(f"mean lattice mixture ratio {df['lattice_mixture_ratio'].mean():.3f} "
          f"(range {df['lattice_mixture_ratio'].min():.3f}-"
          f"{df['lattice_mixture_ratio'].max():.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
