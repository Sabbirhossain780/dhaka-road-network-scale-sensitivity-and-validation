# Topology-Aware Classification of Dhaka's Road Network

MSc thesis work (CSE, BUET).

## What this is, in plain terms

Dhaka's traffic problems get treated with one-size-fits-all solutions. But the city
isn't one thing: a planned grid in Dhanmondi and an organic tangle of lanes in Old Dhaka
are different kinds of road network, and a fix that works in one can make the other
worse.

This project asks whether you can **measure** that difference from map data, and use it
to decide *where* and *what kind of* transport intervention makes sense.

## What we found

**1. The original plan didn't work — and finding out why was the useful part.**
The idea was to sort Dhaka into four network types (Grid, Maze, Radial, Periphery). It
doesn't sort. But the reason isn't that Dhaka lacks structure — it's that the analysis
was done on 1–2 km squares, and **every 1–2 km square contains several different street
patterns at once**. You can't label a zone "a grid" when a quarter of it is a grid and
the rest isn't.

**2. Measured at 400 m instead, the structure is there.**
At that scale a patch usually has *one* character, and it can be measured. The result is
a map of Dhaka's street morphology at 400 m resolution — 60,460 measured windows.

**3. The same "critical intersection" means different things in different places.**
In organic fabric, the busiest junctions tend to be the ones with **no alternative route
around them** — if one is blocked, the neighbourhood is cut off. In grid fabric, busy
junctions usually have alternatives a block away. This matters directly for policy:
traffic-signal optimisation can help the second case and cannot help the first, which
needs new connections instead.

**4. Several things that looked like findings turned out to be side effects of zone size.**
Bigger zones score differently from smaller ones on many measures, and that alone
explained a lot of the original results. Correcting for it is a running theme.

## Where to look

**→ [`02_dhaka_road_topology/pipeline/`](02_dhaka_road_topology/pipeline/README.md)** —
the code, the results, the figures, and the full write-up of how each finding was
reached and where it's weak.

```
02_dhaka_road_topology/
  pipeline/     the project: code, 15 documented experiments, results and figures
  outputs/      original notebook-era results, kept as the validation baseline
  gat/          original betweenness results and per-zone figures
```

## Honesty about status

Work in progress, and the write-up says so throughout. The morphology measure passes a
blind human check as a *discriminator* (AUC 0.77) but falls short of the 85% agreement
target the project set itself, so it supports city-scale conclusions and not claims about
individual locations. The validation used one reviewer, not the expert panel originally
planned. Several results are negative, and they're reported as negative rather than
buried.
