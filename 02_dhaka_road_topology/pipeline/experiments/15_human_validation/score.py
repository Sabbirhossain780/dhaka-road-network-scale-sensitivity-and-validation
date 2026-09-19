#!/usr/bin/env python
"""Experiment 15 -- score the blind labels against the patch grid-score.

WRITTEN BEFORE ANY LABEL EXISTED. Every decision below -- which statistic is
primary, where the grid/organic threshold sits, how "unclear" is handled, how
self-consistency bounds the result -- was fixed in advance so nothing can be
tuned after seeing the answers. `build_instrument.py` records the same choices
in design.json.

  PRIMARY STATISTIC: ROC AUC of grid_score against the human binary label.
    Threshold-free, so it cannot be inflated by choosing a cut-point afterwards.

  PRE-REGISTERED THRESHOLD: Experiment 11's existing rule, grid_score > null_p95.
    Defined for a different purpose, never tuned for this test. Accuracy at this
    threshold is reported as the secondary, directly comparable to the proposal's
    >=85% agreement target.

  "UNCLEAR" is excluded from accuracy and AUC (no ground truth to score against)
    but analysed separately: if the measure is meaningful, unclear patches should
    sit in the MIDDLE of the score range, not at the extremes.

  SELF-CONSISTENCY from the 6 repeated items is the ceiling. A labeller who
    agrees with themselves x% of the time cannot meaningfully exceed x% agreement
    with any measure, so the headline is reported against that ceiling, not
    against 100%.

Usage:
    python experiments/15_human_validation/score.py [--labels labels.csv]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, roc_curve

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = 0.85          # the proposal's own agreement target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=os.path.join(HERE, "labels.csv"))
    args = ap.parse_args()

    if not os.path.exists(args.labels):
        print(f"No labels file at {args.labels}\n"
              f"Open labelling_tool.html, label all 46 items, download labels.csv,\n"
              f"and save it into {HERE}")
        return 1

    lab = pd.read_csv(args.labels)
    man = pd.read_csv(os.path.join(HERE, "manifest.csv"))
    d = man.merge(lab, on="item_id", how="inner")
    print(f"labelled items: {len(d)} / {len(man)}")

    # ---- [1] self-consistency: the ceiling -------------------------------
    reps = d[d["is_repeat_of"].notna() & (d["is_repeat_of"] != "")]
    print("\n[1] SELF-CONSISTENCY (repeated items -- this is the achievable ceiling)")
    ceiling = np.nan
    if len(reps):
        orig = d.set_index("item_id")["label"]
        pairs = [(r["is_repeat_of"], orig.get(r["is_repeat_of"]), r["label"])
                 for _, r in reps.iterrows() if r["is_repeat_of"] in orig.index]
        same = sum(1 for _, a, b in pairs if a == b)
        ceiling = same / len(pairs) if pairs else np.nan
        print(f"    {same}/{len(pairs)} repeated patches labelled identically "
              f"-> self-consistency {ceiling:.1%}")
        for pid, a, b in pairs:
            if a != b:
                print(f"      disagreed on {pid}: '{a}' then '{b}'")
    else:
        print("    no repeated items found")

    # ---- [2] where does 'unclear' sit? -----------------------------------
    print("\n[2] WHERE 'UNCLEAR' FALLS ON THE SCORE SCALE")
    u = d[d["label"] == "unclear"]
    dec = d[d["label"] != "unclear"]
    print(f"    unclear: {len(u)} / {len(d)} ({100*len(u)/len(d):.0f}%)")
    if len(u):
        print(f"    mean grid_score  unclear {u['grid_score'].mean():.3f}  "
              f"vs decided {dec['grid_score'].mean():.3f}")
        lo, hi = dec["grid_score"].quantile(.25), dec["grid_score"].quantile(.75)
        mid = ((u["grid_score"] >= lo) & (u["grid_score"] <= hi)).mean()
        print(f"    {mid:.0%} of unclear patches fall inside the decided IQR "
              f"[{lo:.3f}, {hi:.3f}]")
        print(f"    -> {'consistent with genuine mixture' if mid > 0.4 else 'unclear is NOT mid-range -- investigate'}")

    if len(dec) < 10:
        print("\nToo few decided labels to score.")
        return 1

    # ---- [3] primary: threshold-free AUC ---------------------------------
    y = (dec["label"] == "grid").astype(int).values
    print(f"\n[3] PRIMARY -- ROC AUC (threshold-free), n={len(dec)} decided "
          f"({y.sum()} grid, {len(y)-y.sum()} organic)")
    aucs = {}
    for col in ("grid_score", "excess", "c2"):
        if len(np.unique(y)) < 2:
            break
        a = roc_auc_score(y, dec[col].values)
        aucs[col] = float(a)
        print(f"    AUC({col:<11}) = {a:.3f}")
    auc = aucs.get("grid_score", np.nan)

    # permutation null for the AUC
    rng = np.random.default_rng(0)
    null = np.array([roc_auc_score(rng.permutation(y), dec["grid_score"].values)
                     for _ in range(2000)])
    p = float(((null >= auc).sum() + 1) / (len(null) + 1))
    print(f"    permutation null: mean {null.mean():.3f}, 95th pct "
          f"{np.percentile(null,95):.3f}, p = {p:.4f}")

    # ---- [4] secondary: accuracy at the pre-registered threshold ---------
    pred = (dec["grid_score"] > dec["null_p95"]).map({True: "grid", False: "organic"})
    acc = (pred.values == dec["label"].values).mean()
    print(f"\n[4] SECONDARY -- accuracy at the PRE-REGISTERED threshold "
          f"(grid_score > null_p95)")
    print(f"    agreement = {acc:.1%}   (proposal target {TARGET:.0%})")
    ct = pd.crosstab(dec["label"], pred, rownames=["human"], colnames=["measure"])
    print(f"\n{ct.to_string()}")
    if not np.isnan(ceiling) and ceiling > 0:
        print(f"\n    against the self-consistency ceiling of {ceiling:.1%}: "
              f"{acc/ceiling:.1%} of achievable")

    # ---- [5] per-stratum --------------------------------------------------
    print("\n[5] PER-STRATUM (sampling was stratified, so pooled numbers alone mislead)")
    print(f"    {'stratum':<9}{'n':>4}{'mean excess':>13}{'human grid %':>15}{'unclear':>9}")
    print("-" * 60)
    for s, g in d.groupby("stratum"):
        gd = g[g["label"] != "unclear"]
        pct = (gd["label"] == "grid").mean() if len(gd) else np.nan
        print(f"    {int(s):<9}{len(g):>4}{g['excess'].mean():>+13.3f}"
              f"{pct:>15.0%}{(g['label']=='unclear').sum():>9}")
    rho = stats.spearmanr(d["stratum"], (d["label"] == "grid").astype(int))
    print(f"\n    Spearman(stratum, labelled grid) = {rho.statistic:+.3f} "
          f"(p={rho.pvalue:.2e})")

    # ---- verdict ---------------------------------------------------------
    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)
    print(f"  AUC {auc:.3f} (p={p:.4f}) -- "
          f"{'discriminates' if p < 0.05 else 'NOT distinguishable from chance'}")
    print(f"  Agreement {acc:.1%} vs the proposal's {TARGET:.0%} target -- "
          f"{'MET' if acc >= TARGET else 'not met'}")
    if not np.isnan(ceiling):
        print(f"  Self-consistency ceiling {ceiling:.1%}")
    print("\n  n=40 unique patches, single labeller. This meets the proposal's n=30")
    print("  but NOT its 'expert panel' design -- one reviewer is not a panel, and")
    print("  inter-rater reliability cannot be estimated from one person.")

    figure(dec, y, acc, auc, ceiling)
    with open(os.path.join(HERE, "result.json"), "w") as f:
        json.dump({"n_labelled": int(len(d)), "n_decided": int(len(dec)),
                   "n_unclear": int(len(u)), "self_consistency": None if np.isnan(ceiling)
                   else float(ceiling), "auc": aucs, "auc_p": p,
                   "accuracy_preregistered": float(acc), "target": TARGET,
                   "met_target": bool(acc >= TARGET)}, f, indent=2)
    print("=" * 72)
    return 0


def figure(dec, y, acc, auc, ceiling):
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
    fpr, tpr, _ = roc_curve(y, dec["grid_score"].values)
    ax[0].plot(fpr, tpr, linewidth=2, color="tab:blue")
    ax[0].plot([0, 1], [0, 1], "k--", linewidth=1)
    ax[0].set_xlabel("false positive rate"); ax[0].set_ylabel("true positive rate")
    ax[0].set_title(f"ROC -- grid_score vs human label\nAUC = {auc:.3f}", fontsize=11)
    ax[0].grid(alpha=.3)

    for lab, c in [("grid", "tab:green"), ("organic", "tab:red")]:
        v = dec[dec["label"] == lab]["grid_score"]
        ax[1].hist(v, bins=12, alpha=.6, label=f"human: {lab} (n={len(v)})", color=c)
    ax[1].set_xlabel("grid_score"); ax[1].set_ylabel("patches")
    ax[1].set_title("Do the two human classes\nseparate on the measure?", fontsize=11)
    ax[1].legend(fontsize=8)

    bars = [acc, ceiling if not np.isnan(ceiling) else 0, 0.85]
    names = ["agreement", "self-consistency\n(ceiling)", "proposal\ntarget"]
    ax[2].bar(names, bars, color=["tab:blue", "0.6", "tab:orange"])
    for i, b in enumerate(bars):
        ax[2].text(i, b + .015, f"{b:.0%}", ha="center", fontsize=10)
    ax[2].set_ylim(0, 1.08); ax[2].set_ylabel("proportion")
    ax[2].set_title("Agreement against its ceiling\nand the proposal's target", fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "human_validation.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
