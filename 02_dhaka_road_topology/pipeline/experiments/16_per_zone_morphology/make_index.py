#!/usr/bin/env python
"""Experiment 16b -- a browsable index for the 224 per-zone morphology sheets.

224 sheets is too many to page through looking for a place. This builds the index
as a map rather than a list: each zone is drawn as a small tile at its actual grid
position (metadata.csv carries col_idx / row_idx), so the index is the city, and
finding a zone means looking at where it is rather than scanning filenames.

Each tile shows the zone's 5x5 subgrid lattice tinted by grid-score, with the zone
id underneath. Warm = more grid-like. Grey = no data for that grid cell.

Usage:
    python experiments/16_per_zone_morphology/make_index.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "11_city_mixture_map"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

from run import (CORE_HALF_M, META_CSV, ZONES_DIR, build_null_lookup,
                 zone_cell_data)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    import importlib.util
    spec = importlib.util.spec_from_file_location("sheet", os.path.join(HERE, "run.py"))
    sheet = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sheet)

    meta = pd.read_csv(META_CSV).set_index("zone_id")
    zones = [z for z in sorted(os.listdir(ZONES_DIR)) if z in meta.index]
    pool = pd.read_csv(os.path.join(ZONES_DIR, zones[0], "links.csv"))["length_m"].values
    ns, nmean, _ = build_null_lookup(pool[pool > 0])

    ncol = int(meta["col_idx"].max()) + 1
    nrow = int(meta["row_idx"].max()) + 1
    cmap = plt.get_cmap("RdYlBu_r")
    half = CORE_HALF_M

    fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * 1.55, nrow * 1.72))
    for ax in axes.ravel():
        ax.axis("off")

    print(f"building {nrow}x{ncol} index over {len(zones)} zones ...")
    for i, z in enumerate(zones):
        if i % 40 == 0:
            print(f"  [{i:>3}/{len(zones)}]")
        r, c = int(meta.loc[z, "row_idx"]), int(meta.loc[z, "col_idx"])
        ax = axes[r, c]
        cx = float(meta.loc[z, "centroid_x_utm"]); cy = float(meta.loc[z, "centroid_y_utm"])
        data = zone_cell_data(os.path.join(ZONES_DIR, z), cx, cy)
        if data is None:
            continue
        H, C, _ = data
        score, excess, _ = sheet.subgrid_scores(H, C, ns, nmean, None)

        seg = sheet.zone_segments(os.path.join(ZONES_DIR, z), cx, cy)
        sx, sy, ex, ey = seg
        keep = ~((np.maximum(sx, ex) < -half) | (np.minimum(sx, ex) > half) |
                 (np.maximum(sy, ey) < -half) | (np.minimum(sy, ey) > half))
        if keep.any():
            ax.add_collection(LineCollection(
                np.stack([np.stack([sx[keep], sy[keep]], 1),
                          np.stack([ex[keep], ey[keep]], 1)], 1),
                colors="#333", linewidths=0.18))
        for rr in range(sheet.NSUB):
            for cc in range(sheet.NSUB):
                e = excess[rr, cc]
                fc = "0.88" if np.isnan(e) else cmap(np.clip((e + 0.35) / 0.85, 0, 1))
                ax.add_patch(plt.Rectangle((-half + cc * 400.0, half - (rr + 1) * 400.0),
                                           400, 400, facecolor=fc, alpha=.55,
                                           edgecolor="none", zorder=2))
        ax.set_xlim(-half, half); ax.set_ylim(-half, half)
        ax.set_aspect("equal"); ax.axis("on"); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.4); s.set_color("#aaa")
        ax.set_xlabel(z.replace("Zone_", ""), fontsize=6.2, labelpad=1.5)

    fig.suptitle("Dhaka morphology index — 224 zones at their grid positions, "
                 "each in 400 m subgrids\nwarm = more grid-like · "
                 "open experiments/16_per_zone_morphology/zones/<ZONE>_morphology.png "
                 "for the full sheet", fontsize=13, y=.995)
    plt.tight_layout(rect=[0, 0, 1, 0.975])
    out = os.path.join(HERE, "index_all_zones.png")
    fig.savefig(out, dpi=125, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"index written: {out} ({os.path.getsize(out)/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
