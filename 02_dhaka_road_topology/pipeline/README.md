# Dhaka Road Topology Pipeline

> **Status: work in progress.** The pipeline runs end-to-end and its output
> is validated bit-for-bit against the original notebooks (see
> [Validation](#validation--the-port-changed-nothing) below). The
> *underlying clustering result itself* is weak — see
> [Known Limitations](#known-limitations) before citing any cluster labels
> as a real finding.

Part of an MSc thesis (CSE, BUET) on topology-aware transport policy
targeting for Dhaka. Decomposes Dhaka's road network into 1km zones,
extracts 26 topology features per zone, clusters zones by structural type,
and identifies critical nodes (high betweenness centrality / articulation
points) as candidate policy-intervention points.

This repo contains the **pipeline code** and a **snapshot of its output**
from a full run over 827 zones. It does not contain the paper drafts,
presentations, or raw/intermediate data (see [What's not here](#whats-not-here)).

## Why this exists

The original analysis was six Jupyter notebooks that each forked off the
last one — `dhaka_topology_v1.ipynb` → `v2.ipynb` → `v3.ipynb` (same
pipeline, copy-pasted forward every time a bug was fixed or the bounding
box changed), plus `v4_2km.ipynb` and `thana.ipynb` (new notebooks just to
test a different grid size or zone unit), plus `gat_pipeline.ipynb` and
`uffm_algorithm_v3.ipynb` bolted on top. Grid size, bounding box, and zone
unit were never parameters — they were reasons to fork a notebook.

This package turns those forks into one config-driven pipeline with six
independent, testable stages.

## What's here

```
dhaka_topology/            the pipeline package
  config.py                  Config dataclass — bbox, grid size, zone unit,
                              every threshold — loaded from configs/*.yaml
  io_utils.py                 shared zone-loading helpers
  acquisition.py               Stage 1 — OSM download, cache, validate
  tiling.py                     Stage 2 — grid or thana zone extraction
  features.py                   Stage 3 — 26 topology features per zone
  clustering.py                  Stage 4 — PCA + KMeans/DBSCAN/GMM + report
  betweenness.py                  GAT stage — Brandes betweenness, 4-tier
                                   hierarchy, articulation points
  uffm.py                          UFFM stage — Wasserstein-distance
                                   geometric fingerprints + spectral clustering
  visualization.py                 every plot the pipeline produces
  pipeline.py                      stage orchestration

configs/                   one YAML per variant (v1, v3, v2km, thana)
tests/                     17 unit tests on the pure functions
compare_outputs.py         diffs this pipeline's output against the
                            original notebooks' saved results
results/                   a full run's output (see below) — this is the
                            actual analysis result, not just example output
```

### `results/` — what a full run over 827 zones produced

```
results/outputs/csv/
  features.csv                 26 features x 827 zones
  features_normalized.csv      min-max normalized, size features excluded
  feature_stability.csv        bootstrap CV per feature (see Limitations)
  cluster_assignments.csv      zone -> cluster label + confidence score
  clustering_scores.csv        KMeans/DBSCAN/GMM comparison
  uffm_fingerprints.csv        bearing/angle/length distribution fingerprints
  uffm_cluster_assignments.csv  spectral clustering on Wasserstein distances
  uffm_clustering_scores.csv    silhouette per k, k=2..8
  uffm_v3_crosstab.csv          scalar-feature clusters vs UFFM clusters
  metadata.csv                  per-zone centroid, node/edge counts, cluster

results/outputs/plots/     9 PNGs — road network, grid, PCA, elbow,
                            feature heatmap, choropleth, sample subnetworks
results/outputs/maps/      interactive Folium map (dhaka_cluster_map.html)

results/gat/csv/
  all_zones_summary.csv        822 zones — max/mean/p95/p99 betweenness,
                                tier counts, articulation point count,
                                master (highest-BC) node per zone
  all_nodes_bc.csv              every node in every zone: BC, tier (1-4),
                                degree, is_master, is_articulation_point
  Zone_DH*/nodes_bc.csv          per-zone breakdown (822 files)

results/gat/plots/         822 per-zone hierarchy maps (one PNG per zone)
results/gat/city_distributions.png   city-wide BC/articulation histograms
results/gat/city_master_nodes.png    every zone's master node, one map
```

## What came out

The port's initial clustering result was weak (see "Original weak result"
below) — but a systematic experiment sequence since then (full log in
[`experiments/EXPERIMENTS.md`](experiments/EXPERIMENTS.md)) found and fixed
the actual problem, and arrived at a validated, defensible finding:

**Dhaka's road network does not separate into discrete morphological
archetypes (Maze/Grid/Radial/Periphery) at 1-2km grid scale** — this
confirms the team's own prior null-result finding. **But it does separate,
robustly, into a connectivity-level gradient**: dense/continuous urban
fabric (whether organically grown or formally planned) vs.
sparse/fragmented/peripheral development. Unlike every earlier attempt,
this result is:
- **Statistically significant** against a permutation null (p=0.005,
  ~4-5x above the 95th-percentile of what random data produces)
- **Not a zone-size artifact** — most "normalized" centrality features
  turned out to be 60-85% explained by raw zone size alone
  (`mean_katz_centrality` R²=0.85, `global_efficiency` R²=0.83); the
  finding above is what survives after regressing that out
- **Visually confirmed on the ground** — 7/7 sampled zones matched their
  predicted profile when checked against OpenStreetMap (dense continuous
  fabric for the "connected" cluster including both organic and
  RAJUK-style planned-grid examples; sparse/rural/institutional/
  urbanizing-fringe fabric for the other)

See `experiments/EXPERIMENTS.md` Experiments 01, 06, and 07 for the full
methodology. The original weak numbers below are kept for context on how
this result was reached, not as the final word.

### Original weak result (superseded, kept for context)

KMeans won with k=2, silhouette 0.408 (1km) / 0.513 (2km, before the size
confound was found and corrected). DBSCAN found no structure at any stage
of this project. GMM's silhouette was 0.046-0.242 depending on
configuration. UFFM (geometric fingerprints) didn't independently confirm
the scalar-feature split. All of this turned out to be substantially a
zone-size confound, not a measure of the feature set's real
discriminative power — see Experiment 06.

**Betweenness/GAT:** this part was solid throughout — betweenness
centrality, tier assignment, and articulation-point detection are exact,
deterministic graph computations (Brandes' algorithm), not a fitted model.
`all_zones_summary.csv` and the master-node map are a reasonable output on
their own, independent of the clustering work above.

## Known limitations

- **This is a connectivity-level finding, not a morphology-type
  finding.** The validated cluster split doesn't distinguish "Grid" from
  "Maze" — both appear inside the same "connected" cluster in the
  Experiment 07 spot-check. It distinguishes dense/continuous networks
  from sparse/fragmented ones, which is a real and useful distinction for
  policy targeting, but narrower than the original four-archetype goal.
  **Experiment 08 shows visually why**: rendering whole zones
  ([`experiments/08_cv_fft_pilot/pilot_renders_and_spectra.png`](experiments/08_cv_fft_pilot/pilot_renders_and_spectra.png))
  reveals that no 2km zone *has* a single morphology — every one is a
  mixture of grid patches and organic fabric, and their 2D spectra are
  near-identical as a result. A zone-level morphology label is not a
  well-defined thing to ask for at this scale. **Experiments 09-10 then
  measured this** at 400m patch scale: a rotation-invariant per-patch
  grid-score, validated by eye
  ([`vector_ranking_check.png`](experiments/10_descriptor_validation/vector_ranking_check.png)),
  shows **within-zone morphological variation is ~4x the between-zone
  variation**. So the zone-level label isn't badly measured, it's
  poorly defined — and the **mixture ratio** is the measurable replacement.
  (Experiment 09's own numbers were later found to carry a rasterization
  artifact and are superseded by Experiment 10's vector recompute; the
  conclusion held and strengthened.)
- **The patch grid-score is partially validated** (Experiments 15 / 15b). A
  first blind run failed outright (68.0% agreement, AUC 0.663 p=0.083), but its
  post-mortem traced that to an instrument flaw of mine — one "unclear" button
  covering both "genuinely mixed" and "too little road to judge" — which
  swallowed 46% of items. A corrected, separately pre-registered run at
  n=60 fresh patches with a 1500m density floor gives:
  **ROC AUC 0.766 (p=0.0005)** and mean grid_score ordering
  organic 0.419 < mixed 0.476 < grid 0.620 exactly as a mixture measure
  requires. So the measure **does** discriminate, significantly.
  **But agreement is 75.5% against the proposal's 85% target — not met**, and
  this is not fixable by re-thresholding: the class distributions overlap
  (grid IQR 0.494-0.716, organic 0.305-0.549) and the best achievable single
  cut-point gives only 73.6%. The measure supports the aggregate, city-scale
  uses it is actually put to (Experiments 11, 13, 14) but **not per-patch
  claims about individual locations.**
- **Inter-rater reliability remains unmeasured.** Both validation runs had a
  single labeller (the author). That is precisely what the proposal's
  expert-panel design existed to supply, and no single-rater statistic
  substitutes for it.
- **The earlier satellite validation (Experiment 07) was a small, single-reviewer
  sample** (7 zones), and Experiment 08 then showed its zone-level labels were
  unreliable anyway.
- **The size-confound correction (Experiment 06) is not perfectly clean.**
  A ~3x mean node-count gap remains between the two clusters after
  regressing out `log(node_count)` (down from ~15x before) — better, but
  worth keeping in mind rather than treating as fully solved.
- **Bootstrap feature stability is still uneven.** `feature_stability.csv`
  flags several features (mostly the same ones later found to be
  size-confounded) with CV well above 0.35 under 80%-node resampling.

None of the above is a code bug — the pipeline is validated bit-for-bit
against the original notebooks (see Validation below). The weak initial
result and the confound that explained it were both genuine properties of
the feature set and the data, tracked down through the experiment sequence
in `experiments/EXPERIMENTS.md` rather than assumed or dismissed.

## Validation — the port changed nothing

Every formula here is copied verbatim from the notebooks (each module has
a comment pointing at its source cell). To catch any silent change during
the port, the pipeline was run against the same 827 zones the original
`dhaka_topology_v3.ipynb` already extracted, and every output was diffed
column-by-column against the notebooks' saved CSVs.

| Stage | Output | Result |
|---|---|---|
| Features | `features.csv` (26 x 827) | **exact match** (±1e-6) |
| Features | `features_normalized.csv` | **exact match** |
| Clustering | `cluster_assignments.csv`, `clustering_scores.csv` | **exact match** |
| Betweenness/GAT | `all_zones_summary.csv`, `all_nodes_bc.csv` (822 zones) | **exact match** (excl. wall-clock timing) |
| UFFM | `uffm_fingerprints.csv`, `uffm_cluster_assignments.csv`, `uffm_clustering_scores.csv` | **exact match** (with `uffm_bearing_metric: linear`, the default) |

**One deliberate divergence is available but off by default.** UFFM compares
street-bearing fingerprints with `wasserstein_distance` on a *linear* axis,
although bearing is circular — which makes it rotation-variant (Experiment 12:
rotating a real zone moves it 20% further than a genuinely different zone does).
`uffm_bearing_metric` now offers `circular` and `harmonic` (rotation-invariant)
alternatives. It defaults to `linear` **only** so the pipeline keeps reproducing
the notebooks bit-for-bit and matches the `results/` snapshot; set `harmonic`
when regenerating. Experiment 12 found the choice does not change UFFM's
conclusion either way — its k=2 split is a density split, not a geometry one.

`compare_outputs.py` is the tool that did this diff. It's included so the
same check can be re-run if the pipeline changes.

**Not yet validated:** the `tile` stage (Stage 2 — grid construction from a
freshly downloaded OSM graph) and the `thana` zone unit. Both are direct
ports but haven't been diffed the way the stages above were, because that
requires a multi-hour OSM download to test against.

## Install & run

```bash
pip install -r requirements.txt

# Full pipeline, canonical 1km / 827-zone variant
python run_pipeline.py --config configs/v3.yaml --stage all

# Just re-run feature engineering + clustering (zones already extracted)
python run_pipeline.py --config configs/v3.yaml --stage features cluster

# 2km grid experiment
python run_pipeline.py --config configs/v2km.yaml --stage all
```

Stages run in order: `acquire` -> `tile` -> `features` -> `cluster` ->
`betweenness` -> `uffm` -> `plots`. Each can be run alone; it reloads
whatever earlier-stage CSVs it needs from disk.

```bash
pytest tests/
```
17 tests on the pure functions: Gini coefficient, orientation entropy,
UFFM fingerprint histograms, betweenness/tier classification, and the
rotation-invariance properties of the UFFM bearing metrics.

## What's not here

Paper drafts, the LaTeX thesis document, and presentation slides are kept
outside this repo (local only) — this repo is code + results + docs. Raw
OSM data, per-zone intermediate CSVs, and the original notebooks (kept as
a local backup for reference) are gitignored: they're large, regeneratable
by running the pipeline, and not needed to understand or reproduce the
analysis from what's tracked here.

## TODO

- [ ] **Narrow the thesis's orthogonality claim** — the paper states that orientation entropy
      shows no correlation with betweenness concentration, "establishing that street geometry
      and routing vulnerability are orthogonal". Experiment 14 confirms that exact pairing is
      null (r=+0.010, p=0.78) but shows the generalisation fails: articulation-point fraction
      correlates at +0.214 (p<0.0001) with the same geometry measure, and with 400m patch
      grid-ness all five vulnerability measures are significant after controlling density.
      The claim should be narrowed to the pairing actually tested.


- [ ] Address the clustering weakness above — try a richer or different
      feature set before treating k=2 as a real finding
- [x] Validate the `tile` stage — done via the 2km grid run (Experiment 03), 224/234 zones
      extracted correctly from a freshly-tiled (not re-downloaded) graph
- [ ] `thana` zone-unit path is explicitly out of scope per user direction, not just
      unvalidated (see `experiments/EXPERIMENTS.md` Aim section)
- [x] **Patch-scale mixture-ratio pilot** — done as Experiment 09. A 400m patch grid-score
      (orthogonal-pair spectral energy) is calibrated, density-decoupled and visually
      validated; within-zone variation is 3.0x between-zone variation on n=4 zones.
- [x] **Scale the patch metric to all 224 zones** — done as Experiment 11: 89,600 sliding
      windows in 16s. Mixture ratio DOES vary between zones (between-zone sd 0.107 vs
      within-zone 0.216), survives density decorrelation with 79% of its spread, and stays
      spatially coherent (neighbour corr +0.355 after correction).
- [x] **Cross the mixture layer with betweenness/articulation data** — done as Experiment 13.
      Principle 2 supported: in organic fabric the most critical nodes are 40% MORE likely to
      be cut vertices than typical nodes there; in grid-like fabric 15% LESS likely. The sign
      flips with local morphology, so the same betweenness rank means a structurally different
      thing in each regime. Outputs: `13_morphology_criticality/nodes_morphology.csv`,
      `window_fragility.csv`.
- [x] **Fix `tiling.py` lon/lat** — done. Node coordinates are now inverse-projected through
      the transformer already used for cell centroids (verified to 5e-7 deg on 827 centroids).
      `betweenness.py` keeps its UTM-detection shim so cached zone data written before the fix
      still loads; both paths give identical output. Found in Experiment 13.
- [ ] **Multi-scale run (200/400/800m windows)** — the 400m window is chosen, not derived;
      three rasters would test how fast Dhaka's fabric actually turns over.
- [ ] Try a sliding patch window instead of a fixed lattice — a grid straddling two patch
      boundaries is currently penalised (Experiment 09 caveat)
- [x] **Fix UFFM's fingerprint comparison** — done as the `uffm_bearing_metric` config
      option (`linear` / `circular` / `harmonic`), with rotation-invariance covered by tests.
      Default stays `linear` to preserve bit-for-bit validation and the `results/` snapshot;
      see the Validation section. Experiment 12 showed this is NOT the cause of UFFM's null
      result — its k=2 split is a density split (η² density 0.36-0.49 vs η² morphology
      0.01-0.04), entering through the angle and length terms, not bearing.
- [ ] **Regenerate the `results/` snapshot with `uffm_bearing_metric: harmonic`** and retire the
      `linear` default once the bit-for-bit validation record is no longer needed.
- [ ] **Add a spatial convergence measure for "radial"** — Experiment 10 (C7) showed radial has
      no stable angular signature, so it cannot come from the |c_k| descriptor at all.
- [ ] Add a smoke config (`gat_max_zones` set low) for fast sanity checks
- [x] Run the validation at proper scale — done as Experiment 15 (n=40 blind patches, stratified,
      pre-registered). **It did not meet the target**: 68.0% agreement vs 85%, AUC 0.663 (p=0.083),
      self-consistency only 66.7%. Reported as a negative result.
- [x] **Re-run Experiment 15 with a corrected instrument** — done as Experiment 15b. The
      instrument fixes worked (can't-judge 46% -> 0%, self-consistency 66.7% -> 88%) and the
      measure now discriminates significantly (AUC 0.766, p=0.0005), but agreement is 75.5%
      vs the 85% target.
- [ ] **Recruit a second labeller** — still the outstanding gap. `labelling_tool_v2.html`
      already records rater identity and gives each rater an independently shuffled order;
      `score_v2.py` computes Cohen's kappa automatically once two raters exist.
- [ ] **Pre-register a test of |c2| against grid_score on a fresh sample** — Experiment 15b's
      post-hoc failure analysis suggests the raw second harmonic may discriminate better
      (AUC 0.832 vs 0.766) than the composite built on it. Post-hoc on that sample, so it needs
      its own test; do not cite 0.832 as a result.
- [ ] **Re-draw the Experiment 11 map with the sparse half greyed out** — Experiment 15 showed
      humans cannot judge morphology below ~1500m of road per 400m window, while Experiment 11's
      floor was 500m. The headline within/between ratio is robust to the floor (2.0x/2.2x/1.7x at
      500/1500/3000m) but per-window scores below ~1500m are unverified.
- [ ] Tighten the size-confound correction in Experiment 06 — a ~3x zone-size gap remains
      between clusters after decorrelation; worth investigating whether a stronger
      (e.g. non-linear) size correction removes it further without destroying the real signal
