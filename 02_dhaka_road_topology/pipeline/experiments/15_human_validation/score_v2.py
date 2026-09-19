#!/usr/bin/env python
"""Experiment 15b -- score the corrected validation run.

WRITTEN BEFORE ANY v2 LABEL EXISTED, and implements exactly the analysis fixed in
design_v2.json -- nothing more. The point of a second run is defeated if the
analysis is chosen after seeing the numbers, so this file is the contract.

  PRIMARY      ROC AUC of grid_score, grid vs organic. Mixed and can't-judge are
               excluded: neither is a binary ground truth. Threshold-free.

  SECONDARY    Ordinal Spearman across organic(0) < mixed(1) < grid(2). Uses the
               mixed items instead of discarding them, so it is better powered
               than the binary test.

  DIRECTIONAL  mean grid_score must order organic < mixed < grid. In v1 the
               equivalent prediction FAILED -- "unclear" sat at the bottom of the
               scale, not the middle, because it was being used to mean "can't
               see". With the two meanings separated, a genuine mixture label
               should sit between the two pure classes. If it does not, the
               measure is not tracking morphological mixture, and that is a
               substantive negative result, not a technicality.

  AGREEMENT    accuracy at Experiment 11's pre-existing grid_score > null_p95
               rule, versus the proposal's 85% target.

  CEILINGS     per-rater self-consistency from the 8 repeats; Cohen's kappa
               between raters when two or more have labelled. Agreement with the
               measure is reported against the ceiling, never against 100%.

  CAN'T-JUDGE  reported as an instrument-health check. v1's failure was that this
               category swallowed 46% of items. If it is small here, the density
               floor worked.

Usage:
    python experiments/15_human_validation/score_v2.py [--labels labels_v2.csv]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score, roc_auc_score, roc_curve

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = 0.85
ORDINAL = {"organic": 0, "mixed": 1, "grid": 2}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=os.path.join(HERE, "labels_v2.csv"))
    args = ap.parse_args()
    if not os.path.exists(args.labels):
        print(f"No labels at {args.labels}\nLabel in labelling_tool_v2.html, copy the "
              f"CSV, save it there. Append extra raters' rows to the same file.")
        return 1

    lab = pd.read_csv(args.labels)
    if "rater" not in lab.columns:
        lab["rater"] = "R1"
    man = pd.read_csv(os.path.join(HERE, "manifest_v2.csv"))
    d = man.merge(lab, on="item_id", how="inner")
    raters = sorted(d["rater"].unique())
    print(f"raters: {', '.join(raters)}   rows: {len(d)}")

    # ---- instrument health ------------------------------------------------
    print("\n[0] INSTRUMENT HEALTH (v1 failed because 'unclear' swallowed 46%)")
    for r in raters:
        g = d[d["rater"] == r]
        cj = (g["label"] == "cant_judge").mean()
        mx = (g["label"] == "mixed").mean()
        print(f"    {r:<10} can't-judge {cj:>5.0%}   mixed {mx:>5.0%}   "
              f"decided {1-cj-mx:>5.0%}   n={len(g)}")
    cj_all = (d["label"] == "cant_judge").mean()
    print(f"    -> density floor {'WORKED' if cj_all < 0.15 else 'still insufficient'} "
          f"(can't-judge {cj_all:.0%} overall, was 46% in v1)")
    if (d["label"] == "cant_judge").any():
        cj = d[d["label"] == "cant_judge"]
        print(f"       can't-judge median road {cj['road_len_m'].median():.0f} m "
              f"vs {d[d['label']!='cant_judge']['road_len_m'].median():.0f} m for the rest")

    # ---- ceilings ---------------------------------------------------------
    print("\n[1] CEILINGS")
    cons = {}
    for r in raters:
        g = d[d["rater"] == r].set_index("item_id")
        reps = g[g["is_repeat_of"].notna() & (g["is_repeat_of"] != "")]
        pairs = [(g.loc[x["is_repeat_of"], "label"], x["label"])
                 for _, x in reps.iterrows() if x["is_repeat_of"] in g.index]
        if pairs:
            c = sum(a == b for a, b in pairs) / len(pairs)
            cons[r] = c
            print(f"    {r:<10} self-consistency {c:>5.0%}  ({sum(a==b for a,b in pairs)}/{len(pairs)} repeats)")
    kappa = {}
    if len(raters) >= 2:
        for a, b in itertools.combinations(raters, 2):
            ga = d[d["rater"] == a].set_index("item_id")["label"]
            gb = d[d["rater"] == b].set_index("item_id")["label"]
            common = ga.index.intersection(gb.index)
            if len(common) >= 10:
                k = cohen_kappa_score(ga[common], gb[common])
                kappa[f"{a}|{b}"] = float(k)
                agree = (ga[common] == gb[common]).mean()
                print(f"    {a} vs {b}: Cohen's kappa {k:+.3f}, raw agreement "
                      f"{agree:.0%} on {len(common)} shared items")
    else:
        print("    only one rater -- inter-rater reliability CANNOT be estimated.")
        print("    This is the quantity the proposal's expert-panel design required.")
    ceiling = np.mean(list(cons.values())) if cons else np.nan

    # ---- directional prediction ------------------------------------------
    print("\n[2] DIRECTIONAL PREDICTION -- mean grid_score: organic < mixed < grid")
    means = {}
    for k in ("organic", "mixed", "grid"):
        g = d[d["label"] == k]
        if len(g):
            means[k] = float(g["grid_score"].mean())
            print(f"    {k:<9} n={len(g):>3}   mean grid_score {means[k]:.3f}")
    ordered = (len(means) == 3 and means["organic"] < means["mixed"] < means["grid"])
    print(f"    -> {'ORDERED as predicted' if ordered else 'NOT in the predicted order'}"
          f"{'' if ordered else ' -- the measure is not tracking mixture'}")

    # ---- secondary: ordinal ----------------------------------------------
    orddf = d[d["label"].isin(ORDINAL)].copy()
    orddf["ord"] = orddf["label"].map(ORDINAL)
    rho = stats.spearmanr(orddf["grid_score"], orddf["ord"])
    print(f"\n[3] SECONDARY -- ordinal Spearman (organic<mixed<grid), n={len(orddf)}")
    print(f"    rho = {rho.statistic:+.3f}   p = {rho.pvalue:.4f}")

    # ---- primary: AUC ------------------------------------------------------
    bin_df = d[d["label"].isin(["grid", "organic"])]
    print(f"\n[4] PRIMARY -- ROC AUC, grid vs organic, n={len(bin_df)} "
          f"({(bin_df['label']=='grid').sum()} grid, {(bin_df['label']=='organic').sum()} organic)")
    auc = p = np.nan
    if len(bin_df) >= 10 and bin_df["label"].nunique() == 2:
        y = (bin_df["label"] == "grid").astype(int).values
        auc = roc_auc_score(y, bin_df["grid_score"].values)
        rng = np.random.default_rng(0)
        null = np.array([roc_auc_score(rng.permutation(y), bin_df["grid_score"].values)
                         for _ in range(2000)])
        p = float(((null >= auc).sum() + 1) / (len(null) + 1))
        print(f"    AUC = {auc:.3f}   permutation p = {p:.4f} "
              f"(null mean {null.mean():.3f}, 95th pct {np.percentile(null,95):.3f})")
        print(f"    v1 for comparison: AUC 0.663, p 0.083")
    else:
        print("    too few binary labels to test")

    # ---- agreement ---------------------------------------------------------
    acc = np.nan
    if len(bin_df):
        pred = (bin_df["grid_score"] > bin_df["null_p95"]).map({True: "grid", False: "organic"})
        acc = float((pred.values == bin_df["label"].values).mean())
        print(f"\n[5] AGREEMENT at the pre-registered threshold = {acc:.1%} "
              f"(target {TARGET:.0%})   v1: 68.0%")
        print(pd.crosstab(bin_df["label"], pred, rownames=["human"],
                          colnames=["measure"]).to_string())
        if not np.isnan(ceiling) and ceiling > 0:
            print(f"    against the {ceiling:.0%} self-consistency ceiling: "
                  f"{acc/ceiling:.0%} of achievable")

    print("\n" + "=" * 74)
    print("VERDICT")
    print("=" * 74)
    if not np.isnan(auc):
        print(f"  Primary AUC {auc:.3f} (p={p:.4f}) -- "
              f"{'discriminates' if p < 0.05 else 'NOT distinguishable from chance'}")
    print(f"  Ordinal rho {rho.statistic:+.3f} (p={rho.pvalue:.4f})")
    print(f"  Directional prediction: {'held' if ordered else 'FAILED'}")
    if not np.isnan(acc):
        print(f"  Agreement {acc:.1%} vs {TARGET:.0%} target -- "
              f"{'MET' if acc >= TARGET else 'not met'}")
    if len(raters) < 2:
        print("  NO inter-rater estimate -- single rater. The proposal's panel")
        print("  design remains unmet regardless of the numbers above.")

    figure(d, bin_df, means, auc, acc, ceiling)
    with open(os.path.join(HERE, "result_v2.json"), "w") as f:
        json.dump({"raters": raters, "n_rows": int(len(d)),
                   "cant_judge_rate": float(cj_all),
                   "self_consistency": cons, "cohen_kappa": kappa,
                   "class_means": means, "directional_ok": bool(ordered),
                   "ordinal_rho": float(rho.statistic), "ordinal_p": float(rho.pvalue),
                   "auc": None if np.isnan(auc) else float(auc),
                   "auc_p": None if np.isnan(p) else float(p),
                   "agreement": None if np.isnan(acc) else float(acc),
                   "target": TARGET,
                   "met_target": bool(acc >= TARGET) if not np.isnan(acc) else False},
                  f, indent=2)
    print("=" * 74)
    return 0


def figure(d, bin_df, means, auc, acc, ceiling):
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
    order = ["organic", "mixed", "grid", "cant_judge"]
    cols = {"organic": "tab:red", "mixed": "tab:olive", "grid": "tab:green",
            "cant_judge": "0.6"}
    present = [k for k in order if (d["label"] == k).any()]
    ax[0].boxplot([d[d["label"] == k]["grid_score"] for k in present],
                  labels=[k.replace("_", "\n") for k in present], showfliers=False)
    for j, k in enumerate(present, 1):
        v = d[d["label"] == k]["grid_score"]
        ax[0].scatter(np.full(len(v), j) + np.random.uniform(-.09, .09, len(v)), v,
                      s=20, alpha=.6, color=cols[k], zorder=3)
    ax[0].set_ylabel("grid_score")
    ax[0].set_title("Does the measure order the\nhuman classes?", fontsize=11)
    ax[0].grid(axis="y", alpha=.3)

    if not np.isnan(auc) and len(bin_df):
        y = (bin_df["label"] == "grid").astype(int).values
        fpr, tpr, _ = roc_curve(y, bin_df["grid_score"].values)
        ax[1].plot(fpr, tpr, linewidth=2, color="tab:blue", label=f"v2 AUC {auc:.3f}")
        ax[1].plot([0, 1], [0, 1], "k--", linewidth=1)
        ax[1].set_xlabel("false positive rate"); ax[1].set_ylabel("true positive rate")
        ax[1].set_title("ROC -- grid vs organic", fontsize=11)
        ax[1].legend(fontsize=9); ax[1].grid(alpha=.3)

    bars, names = [], []
    if not np.isnan(acc):
        bars.append(acc); names.append("agreement")
    if not np.isnan(ceiling):
        bars.append(ceiling); names.append("self-consistency\n(ceiling)")
    bars.append(0.85); names.append("proposal\ntarget")
    ax[2].bar(names, bars, color=["tab:blue", "0.6", "tab:orange"][:len(bars)])
    for j, b in enumerate(bars):
        ax[2].text(j, b + .015, f"{b:.0%}", ha="center", fontsize=10)
    ax[2].set_ylim(0, 1.08); ax[2].set_ylabel("proportion")
    ax[2].set_title("Agreement vs ceiling and target", fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "human_validation_v2.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
