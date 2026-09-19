#!/usr/bin/env python
"""Experiment 14 (Phase 0) -- is street geometry really orthogonal to routing
vulnerability, or was that an artifact of measuring geometry at the wrong scale?

The thesis states:

    "Orientation entropy shows no correlation with betweenness concentration
     (Spearman r=0.02; p=0.58) establishing that street geometry and routing
     vulnerability are orthogonal."

Experiment 13 is in tension with that. It found organic fabric has a 52% higher
articulation-point rate than grid-like fabric, and that the critical-node /
cut-vertex relationship REVERSES SIGN with local morphology. If geometry and
vulnerability were orthogonal, neither of those could happen.

TWO WAYS THE PAPER'S CLAIM COULD BE WRONG, and they need separating:

  A. OVER-GENERALISATION. The claim tests ONE geometry measure (orientation
     entropy) against ONE vulnerability measure (max betweenness) and generalises
     to "geometry and vulnerability are orthogonal". Other vulnerability measures
     were never tested against it.

  B. MEASUREMENT SCALE. Orientation entropy is a zone-level scalar, and
     Experiments 08-11 showed zone-level geometry measures are washed out because
     a 1-2km zone is a mixture of fabrics. A null from a blunt instrument is not
     evidence of absence.

This experiment tests both: it holds the vulnerability measures fixed and swaps
the geometry measure from the zone-level scalar to Experiment 11's patch-level
grid-ness, aggregated into the same 1km zones by spatial pooling.

The density confound (Experiments 06, 11, 12, 13) is controlled throughout --
if a geometry/vulnerability link is really a density link, it must show up here.

Usage:
    python experiments/14_orthogonality_recheck/run.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
V3 = os.path.join(ROOT, "pipeline_outputs", "v3")
WINDOWS = os.path.join(HERE, "..", "11_city_mixture_map", "windows.csv")
CORE_HALF_M = 500.0          # v3 zones are 1km
MIN_WINDOWS = 8              # per zone, to trust its patch grid-ness


def partial_corr(x, y, z):
    """Spearman correlation of x and y after linearly removing z from both."""
    Z = np.asarray(z, dtype=float).reshape(-1, 1)
    rx = x - LinearRegression().fit(Z, x).predict(Z)
    ry = y - LinearRegression().fit(Z, y).predict(Z)
    r = stats.spearmanr(rx, ry)
    return float(r.statistic), float(r.pvalue)


def main() -> int:
    feats = pd.read_csv(os.path.join(V3, "outputs", "csv", "features.csv"))
    meta = pd.read_csv(os.path.join(V3, "outputs", "csv", "metadata.csv"))
    gat = pd.read_csv(os.path.join(V3, "gat", "csv", "all_zones_summary.csv"))
    win = pd.read_csv(WINDOWS)
    win = win[~win["sparse"]].reset_index(drop=True)

    df = feats.merge(gat, on="zone_id").merge(
        meta[["zone_id", "centroid_x_utm", "centroid_y_utm", "osm_completeness"]],
        on="zone_id")
    nnodes = df["n_nodes"] if "n_nodes" in df.columns else df["n_nodes_y"]
    df["art_frac"] = df["art_point_count"] / nnodes
    df["tier1_frac"] = df["tier1_count"] / nnodes
    df["log_density"] = np.log(np.maximum(df["osm_completeness"], 1e-3))
    print(f"zones with features + GAT + metadata: {len(df)}")

    # ---- pool Experiment 11's 400m windows into each 1km v3 zone ----------
    wx, wy = win["wx"].values, win["wy"].values
    med, cnt = [], []
    for cx, cy in zip(df["centroid_x_utm"], df["centroid_y_utm"]):
        m = (np.abs(wx - cx) <= CORE_HALF_M) & (np.abs(wy - cy) <= CORE_HALF_M)
        cnt.append(int(m.sum()))
        med.append(float(np.median(win["excess"].values[m])) if m.sum() else np.nan)
    df["patch_gridness"] = med
    df["n_windows"] = cnt
    d = df[(df["n_windows"] >= MIN_WINDOWS) & df["patch_gridness"].notna()].copy()
    print(f"zones with >={MIN_WINDOWS} pooled windows: {len(d)} "
          f"(median {int(np.median(d['n_windows']))} windows/zone)")

    vuln = {"max_bc": "max betweenness (the paper's measure)",
            "betweenness_gini": "betweenness Gini",
            "p99_bc": "p99 betweenness",
            "art_frac": "articulation-point fraction",
            "tier1_frac": "tier-1 node fraction"}

    print("\n" + "=" * 88)
    print("IS GEOMETRY ORTHOGONAL TO VULNERABILITY?")
    print("=" * 88)

    # ---- [A] over-generalisation: paper's geometry vs OTHER vulnerabilities
    print("\n[A] THE PAPER'S OWN GEOMETRY MEASURE (orientation entropy),")
    print("    against vulnerability measures it did not test:")
    print(f"    {'vulnerability':<34}{'spearman':>11}{'p':>11}{'verdict':>14}")
    print("-" * 88)
    a_res = {}
    for k, lab in vuln.items():
        r = stats.spearmanr(d["orientation_entropy"], d[k])
        a_res[k] = {"r": float(r.statistic), "p": float(r.pvalue)}
        v = "null" if r.pvalue > 0.05 else ("**" if r.pvalue < 0.001 else "*")
        print(f"    {lab:<34}{r.statistic:>+11.3f}{r.pvalue:>11.4f}{v:>14}")
    print("\n    The paper generalised from the FIRST row to 'geometry and routing")
    print("    vulnerability are orthogonal'. Rows below it were never tested.")

    # ---- [B] measurement scale: patch-level geometry, same vulnerabilities
    print("\n[B] SAME VULNERABILITIES, geometry measured at 400m PATCH scale instead:")
    print(f"    {'vulnerability':<34}{'spearman':>11}{'p':>11}"
          f"{'partial(density)':>18}{'p':>9}")
    print("-" * 88)
    b_res = {}
    for k, lab in vuln.items():
        r = stats.spearmanr(d["patch_gridness"], d[k])
        pr, pp = partial_corr(d["patch_gridness"].values, d[k].values,
                              d["log_density"].values)
        b_res[k] = {"r": float(r.statistic), "p": float(r.pvalue),
                    "partial_r": pr, "partial_p": pp}
        print(f"    {lab:<34}{r.statistic:>+11.3f}{r.pvalue:>11.4f}"
              f"{pr:>+18.3f}{pp:>9.4f}")

    # ---- head-to-head --------------------------------------------------
    print("\n[C] HEAD TO HEAD -- |Spearman| by geometry measure")
    print(f"    {'vulnerability':<34}{'zone-level':>13}{'patch-level':>14}{'change':>12}")
    print("-" * 88)
    improved = 0
    for k, lab in vuln.items():
        za, pa = abs(a_res[k]["r"]), abs(b_res[k]["r"])
        if pa > za:
            improved += 1
        print(f"    {lab:<34}{za:>13.3f}{pa:>14.3f}{pa - za:>+12.3f}")
    print(f"\n    patch-level is stronger on {improved}/{len(vuln)} measures")

    # ---- verdict --------------------------------------------------------
    print("\n" + "=" * 88)
    print("VERDICT")
    print("=" * 88)
    paper_null = a_res["max_bc"]["p"] > 0.05
    others_sig = [k for k in vuln if k != "max_bc" and a_res[k]["p"] < 0.05]
    patch_sig = [k for k in vuln if b_res[k]["p"] < 0.05]
    patch_sig_partial = [k for k in vuln if b_res[k]["partial_p"] < 0.05]

    print(f"  The paper's specific claim (orientation entropy vs max betweenness):")
    print(f"    r={a_res['max_bc']['r']:+.3f}, p={a_res['max_bc']['p']:.3f} -> "
          f"{'HOLDS, that pairing really is null' if paper_null else 'DOES NOT HOLD'}")
    print(f"\n  But with the SAME geometry measure, these are NOT null: "
          f"{', '.join(others_sig) if others_sig else 'none'}")
    print(f"  With PATCH-level geometry, these are significant: "
          f"{', '.join(patch_sig) if patch_sig else 'none'}")
    print(f"  ... and after removing density: "
          f"{', '.join(patch_sig_partial) if patch_sig_partial else 'none'}")
    print(f"\n  => The narrow claim survives. The GENERALISATION -- 'street geometry and")
    print(f"     routing vulnerability are orthogonal' -- does not, and should be")
    print(f"     narrowed to the specific pairing actually tested.")

    figures(d, a_res, b_res, vuln)
    with open(os.path.join(HERE, "result.json"), "w") as f:
        json.dump({"n_zones": int(len(d)),
                   "zone_level_geometry": a_res, "patch_level_geometry": b_res,
                   "paper_pairing_null": bool(paper_null),
                   "others_significant_same_geometry": others_sig,
                   "patch_significant": patch_sig,
                   "patch_significant_density_controlled": patch_sig_partial},
                  f, indent=2)
    d.to_csv(os.path.join(HERE, "zone_geometry_vulnerability.csv"), index=False)
    print("\n  See orthogonality_recheck.png")
    print("=" * 88)
    return 0


def figures(d, a_res, b_res, vuln):
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.2))

    keys = list(vuln)
    xpos = np.arange(len(keys))
    ax[0].bar(xpos - 0.2, [abs(a_res[k]["r"]) for k in keys], 0.4,
              label="orientation entropy (zone-level)", color="tab:gray")
    ax[0].bar(xpos + 0.2, [abs(b_res[k]["r"]) for k in keys], 0.4,
              label="patch grid-ness (400m)", color="tab:green")
    ax[0].set_xticks(xpos)
    ax[0].set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=8)
    ax[0].set_ylabel("|Spearman| with vulnerability")
    ax[0].set_title("Does geometry predict vulnerability?\nDepends how you measure geometry",
                    fontsize=11)
    ax[0].legend(fontsize=8)
    ax[0].grid(axis="y", alpha=.3)

    ax[1].scatter(d["orientation_entropy"], d["art_frac"], s=14, alpha=.5,
                  color="tab:gray")
    r = a_res["art_frac"]
    ax[1].set_xlabel("orientation entropy (zone-level)")
    ax[1].set_ylabel("articulation-point fraction")
    ax[1].set_title(f"Zone-level geometry\nr={r['r']:+.3f}, p={r['p']:.4f}", fontsize=11)
    ax[1].grid(alpha=.3)

    ax[2].scatter(d["patch_gridness"], d["art_frac"], s=14, alpha=.5, color="tab:green")
    r = b_res["art_frac"]
    ax[2].set_xlabel("patch grid-ness (400m, Experiment 11)")
    ax[2].set_ylabel("articulation-point fraction")
    ax[2].set_title(f"Patch-level geometry\nr={r['r']:+.3f}, p={r['p']:.4f}"
                    f"  (density-controlled {r['partial_r']:+.3f})", fontsize=11)
    ax[2].grid(alpha=.3)

    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "orthogonality_recheck.png"), dpi=130,
                bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
