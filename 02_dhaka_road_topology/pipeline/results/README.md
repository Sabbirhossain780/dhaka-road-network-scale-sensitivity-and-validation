# `results/`

```
figures/                          the nine figures that carry the findings
data/                             the result tables worth citing
original_v3_run_2026-09-17/       the earlier snapshot — largely superseded
```

`figures/` and `data/` are curated copies. Each file is produced by a script under
[`../experiments/`](../experiments/) and regenerates by re-running it; the experiment
folders stay the source of truth, this folder is the reading order.

---

## `figures/` — the findings, in the order the argument runs

| Figure | Shows | From |
|---|---|---|
| `01_why_zone_morphology_is_illposed.png` | Four 2 km zones picked as clear examples of two morphological types. Each is a mixture, and their spectra are near-identical. **This is why the zone-level typology failed.** | Exp 08 |
| `02_measure_verified_on_synthetics.png` | The patch measure tested against patterns whose morphology is known by construction. Three of eight claims about it were wrong and were corrected before use. | Exp 10 |
| `03_patch_ranking_sanity_check.png` | Highest- vs lowest-scoring 400 m patches — the check that the measure ranks the way a human would, run before trusting any number. | Exp 10 |
| `04_dhaka_morphology_map_400m.png` | **Dhaka at 400 m resolution, 60,460 scored windows.** The headline output. | Exp 11 |
| `05_density_confound_and_residual.png` | Mixture ratio correlates with node density at +0.72. What survives decorrelation: 79% of the spread, still spatially coherent. | Exp 11 |
| `06_uffm_is_a_density_measure.png` | Rotating a real zone moves it further from itself than a genuinely different zone lies — and fixing that changes nothing, because UFFM was measuring density all along. | Exp 12 |
| `07_context_dependent_criticality.png` | In organic fabric the most critical nodes **are** the cut vertices; in grid fabric they are not. The sign reverses. **The framework's central claim, tested.** | Exp 13 |
| `08_geometry_vulnerability_by_scale.png` | Geometry vs vulnerability at zone scale and at 400 m. Stronger at patch scale on 5 of 5 measures. | Exp 14 |
| `09_blind_human_validation.png` | Blind labelling of 60 patches. AUC 0.766 (p=0.0005), but 75.5% agreement against an 85% target. **Partial validation.** | Exp 15b |
| `10_zone_index_400m_subgrids.png` | All 224 zones at their real grid positions, each as its 5x5 lattice of 400 m subgrids. **The index is a map** — find a zone by where it is. | Exp 16 |
| `11_example_zone_sheet_DH168.png` | One zone's full sheet: where its grid-like parts are, and what each part looks like on its own. One exists per zone (gitignored, regenerable). | Exp 16 |

## `data/` — tables worth citing

| File | Contents |
|---|---|
| `zone_morphology_decorrelated.csv` | Per-zone morphology after removing node density. **The defensible zone-level variable** — use this, not the raw mixture ratio. |
| `zone_mixture_ratio.csv` | Raw per-zone mixture ratio, before decorrelation. Kept for comparison; Exp 11 explains why the raw form is confounded. |
| `human_validation_labels.csv` | The 68 blind human labels from Experiment 15b. |
| `human_validation_manifest.csv` | What each labelled patch actually was — score, location, which items were repeats. |

Larger intermediates (`windows.csv`, 89,600 scored windows; `nodes_morphology.csv`,
57,999 nodes) are gitignored and regenerate in seconds from the experiment scripts.

---

## `original_v3_run_2026-09-17/` — the earlier snapshot

One run of `configs/v3.yaml` (1 km grid, 827 zones), generated before the experiment
sequence began. Kept because parts are still in active use, but **it is not the current
result** and its clustering outputs should not be cited.

**Still valid, still used:**

- `gat/csv/all_nodes_bc.csv` — exact Brandes betweenness, tiers and articulation status
  for 338,429 node-rows. Experiments 13 and 14 are built on it.
- `gat/csv/all_zones_summary.csv` — per-zone betweenness summary.
- `outputs/csv/features.csv`, `features_normalized.csv`, `feature_stability.csv` — the
  26 topology features.
- `gat/city_distributions.png`, `city_master_nodes.png`,
  `outputs/plots/dhaka_road_network.png`, `grid_tiling.png` — descriptive, not results.

Two caveats even on these. Betweenness is **zone-local**, computed per buffered subgraph,
so raw magnitudes are not comparable across zones — only within-zone rank is. And
articulation status is **subgraph-dependent**: 14.4% of nodes disagree between the zones
containing them.

**Superseded — do not cite:**

| Output | Why |
|---|---|
| `outputs/csv/cluster_assignments.csv` | The k=2 split is substantially a zone-size confound: cluster means 51.6 vs 544.3 nodes, a **10.6x ratio** (Exp 06). |
| `outputs/plots/cluster_choropleth.png`, `pca_clusters.png`, `elbow_silhouette.png` | All visualise that confounded split. |
| `outputs/plots/cluster_sample_subnetworks.png` | Presents zones as morphological exemplars; Exp 08 showed no 2 km zone has a single morphology. |
| `outputs/maps/dhaka_cluster_map.html` | Interactive map of the confounded clusters. |
| `outputs/csv/uffm_*.csv` | UFFM's k=2 is a density split — eta-squared 0.36-0.49 for density vs 0.01-0.04 for morphology (Exp 12). |
| `metadata.csv` -> `cluster_id`, `cluster_label`, `confidence_score` | Same confounded labels. Centroids and `osm_completeness` are fine, but note the latter is a node-density ratio (0.12-23.26), not a 0-1 fraction. |

**What survived:** after regressing out `log(node_count)`, a real two-way *connectivity*
split remains, significant at p=0.005 at both 1 km and 2 km (Exp 06). A connectivity
finding, not a morphology typology.

**Untracked but present on disk:** `gat/csv/Zone_DH*/nodes_bc.csv` (822 files,
byte-for-byte subsets of `all_nodes_bc.csv`) and `gat/plots/` (822 per-zone PNGs).
Regenerate with `python run_pipeline.py --config configs/v3.yaml --stage betweenness`,
or slice the per-zone tables straight out of `all_nodes_bc.csv`.

---

## Why there are no per-zone figures for the 224 2 km zones

The betweenness stage was only ever run on the 1 km config, and does not need re-running
at 2 km. The morphology layer is a *geographic* field of 400 m windows, not a zone
attribute, so Experiment 13 joins betweenness to it **on position, not zone id** — which
is why 1 km betweenness and the 2 km-derived morphology field combine without either
being recomputed.

---

## Validation status

The pipeline's outputs are validated bit-for-bit against the original notebooks, and the
check is **still runnable**. The notebook-era reference outputs live in
`02_dhaka_road_topology/outputs/` and `gat/` (March 2026, pre-pipeline); a duplicate copy
under `backup_original_topology/` was removed in a cleanup, but the originals remain:

```bash
python compare_outputs.py   --old ../outputs/v3 --new results/original_v3_run_2026-09-17/outputs   --old-gat ../gat   --new-gat results/original_v3_run_2026-09-17/gat
```

Re-verified after the cleanup: **ALL MATCH** across features, clustering, betweenness and
UFFM.
