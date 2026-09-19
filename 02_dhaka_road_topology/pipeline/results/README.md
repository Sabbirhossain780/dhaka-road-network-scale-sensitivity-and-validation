# `results/` — provenance and status

**Everything in this folder is the output of one run: `configs/v3.yaml`, the 1km
grid, 827 zones (822 with betweenness), generated 17 Sep 2026 — before the
experiment sequence in [`../experiments/EXPERIMENTS.md`](../experiments/EXPERIMENTS.md)
began.**

That matters, because Experiments 06-15b substantially revised what these files
mean. This page says which outputs still stand, which are superseded, and where
the current results actually live. Read it before citing anything here.

---

## Still valid

| Output | Why it stands |
|---|---|
| `gat/csv/all_nodes_bc.csv` | Exact Brandes betweenness, tier and articulation status for 338,429 node-rows across 822 zones. A deterministic graph computation, not a fitted model. Experiment 13 is built on it. |
| `gat/csv/all_zones_summary.csv` | Per-zone betweenness summary. Same basis. |
| `gat/city_distributions.png`, `gat/city_master_nodes.png` | City-wide betweenness distributions and master nodes. |
| `outputs/csv/features.csv`, `features_normalized.csv` | The 26 topology features. Were validated bit-for-bit against the original notebooks; that comparison is a recorded finding and can no longer be re-executed (its reference data was deleted in cleanup — see `../README.md`). |
| `outputs/csv/feature_stability.csv` | Bootstrap CV per feature. |
| `outputs/plots/dhaka_road_network.png`, `grid_tiling.png` | Descriptive figures of the data and the tiling. Not results. |

Two caveats that apply even to the valid files:

- **Betweenness is zone-local.** It was computed on each zone's buffered subgraph,
  so raw `bc` magnitudes are *not* comparable across zones — only within-zone rank
  is. Experiment 13 uses within-zone percentile for this reason.
- **Articulation status is subgraph-dependent.** 14.4% of nodes disagree between
  the zones that contain them (Experiment 13).

---

## Superseded — do not cite as findings

| Output | Superseded by | What went wrong |
|---|---|---|
| `outputs/csv/cluster_assignments.csv` | Experiment 06 | The k=2 split is substantially a **zone-size confound**. Cluster means are 51.6 vs 544.3 nodes — a **10.6x** size ratio. Most "normalised" centrality features are 60-85% explained by raw zone size alone. |
| `outputs/plots/cluster_choropleth.png` | Experiments 06, 11 | Maps the confounded split above. |
| `outputs/plots/pca_clusters.png` | Experiments 06, 11 | Visualises the same. |
| `outputs/plots/elbow_silhouette.png` | Experiment 06 | The silhouette curve that selected the confounded k=2. |
| `outputs/plots/cluster_sample_subnetworks.png` | Experiments 08, 09 | Presents zones as morphological exemplars. Experiment 08 showed no 2km zone *has* a single morphology. |
| `outputs/maps/dhaka_cluster_map.html` | Experiment 06 | Interactive map of the confounded clusters. |
| `outputs/csv/uffm_*.csv` | Experiment 12 | UFFM's k=2 split is a **density split**: η² density 0.36-0.49 vs η² morphology 0.01-0.04, entering through the angle and length terms. Its bearing comparison is also rotation-variant (`uffm.py:161`). |
| `outputs/csv/metadata.csv` → `cluster_id`, `cluster_label`, `confidence_score` | Experiment 06 | Same confounded labels. The centroid and `osm_completeness` columns are fine — note `osm_completeness` is a **node-density ratio** (range 0.12-23.26), not a 0-1 completeness fraction. |

**What survived the correction:** after regressing out `log(node_count)`, a real
two-way *connectivity* split remains, significant at p=0.005 at both 1km and 2km
(Experiment 06). It is a connectivity-level finding, not a morphology typology.

---

## Where the current results live

The headline findings are **not in this folder**. They are under
[`../experiments/`](../experiments/), because they come from the 2km run and from
patch-scale analysis that this 1km snapshot predates:

| Finding | Location |
|---|---|
| City-wide morphology map, 400m windows | `experiments/11_city_mixture_map/city_mixture_map.png` |
| Zone mixture ratio, density-decorrelated | `experiments/11_city_mixture_map/zone_final.csv` |
| Density confound analysis | `experiments/11_city_mixture_map/completeness_confound.png` |
| Context-dependent criticality (Principle 2) | `experiments/13_morphology_criticality/morphology_criticality.png` |
| Fragility layer | `experiments/13_morphology_criticality/window_fragility.csv` *(gitignored — regenerate with `run.py`)* |
| Geometry/vulnerability recheck | `experiments/14_orthogonality_recheck/orthogonality_recheck.png` |
| Blind human validation | `experiments/15_human_validation/human_validation_v2.png` |

---

## Why there are no per-zone figures for the 224 2km zones

`gat/plots/` holds 822 per-zone hierarchy maps — one per **1km** zone. There is no
equivalent set for the 2km run, because **the betweenness/GAT stage was never run on
`configs/v2km.yaml`**, and it does not need to be.

The morphology layer produced by Experiment 11 is a *geographic* field of 400m
windows, not a zone attribute. Experiment 13 therefore joins betweenness to
morphology **on space, not on zone id** — node lon/lat against window coordinates —
which is why the 1km betweenness and the 2km-derived morphology field combine
without either being re-run. Running GAT again at 2km would produce a second,
parallel betweenness result requiring its own validation, to answer a question that
is already answered.

If a 2km betweenness run is ever wanted:

```bash
python run_pipeline.py --config configs/v2km.yaml --stage betweenness
```

It takes roughly 10-15 minutes (822 zones took ~25 minutes at 1km).

---

## Known redundancy in this folder

- `gat/csv/Zone_DH*/nodes_bc.csv` — 822 files, **22 MB**, byte-for-byte subsets of
  `all_nodes_bc.csv` (identical columns and row counts). They carry no information
  that file does not.
- `gat/plots/` — 822 PNGs, **111 MB**, regenerable by re-running the betweenness
  stage.

Together these are ~133 MB of the folder's 169 MB. **Both are now untracked**
(still present on disk, excluded via `.gitignore`) — only `all_nodes_bc.csv`,
`all_zones_summary.csv` and the two city-level PNGs are kept under `gat/`.

To regenerate either, re-run the betweenness stage (~25 min for 822 zones):

```bash
python run_pipeline.py --config configs/v3.yaml --stage betweenness
```

Per-zone CSVs can also be reconstructed from `all_nodes_bc.csv` alone, without
re-running anything:

```python
import pandas as pd
df = pd.read_csv("results/gat/csv/all_nodes_bc.csv")
zone = df[df["zone_id"] == "Zone_DH019"]      # identical to that zone's nodes_bc.csv
```

Note that untracking them shrinks future commits but **not** the existing `.git`
directory (~498 MB), which still holds their history. Only a history rewrite
(`git filter-repo` / BFG) plus a force-push would reclaim that space.
