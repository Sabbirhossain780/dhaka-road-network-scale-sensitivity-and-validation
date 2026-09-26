# Grid, Organic, or Neither? Scale-Dependent Morphology and Context-Dependent Criticality in Dhaka's Road Network

Class project (CSE, BUET). The title is the arc of the project, not a label for
its output: it started by asking whether Dhaka's zones sort into a typology (Grid,
Maze, Radial, Periphery). They don't, at the scale that question was asked. Measured
instead at 400 m, morphology turns out to be real and continuous — and the payoff
isn't a typology at all, it's that **the same critical intersection means something
different depending on the fabric around it** (Finding 6): the sign of the
relationship between betweenness rank and cut-vertex status reverses between organic
and grid fabric. Two findings, not one: structure is *scale-dependent* (visible at
400 m, invisible at 1–2 km), and criticality is *context-dependent* (the same rank
implies a different kind of vulnerability depending on where it sits).

## Abstract

This project began with one question: does Dhaka's road network sort into a handful
of recognisable types — grid, maze, radial, periphery — the way city planners often
assume a city's streets do? If it does, a zone's type could guide what kind of
transport fix makes sense there before anyone even looks at the traffic.

It doesn't sort, not at the scale the question was first asked. Every 1–2 km zone
turned out to be a patchwork of several street patterns at once — not a bad
measurement, just the wrong resolution to expect one clean answer at.

That failure became the real investigation. A long sequence of experiments confirmed
the null result was real and not noise, traced most of it to zone size and
mapping-density confounds, tried and discarded a few fixes, and eventually rebuilt the
measurement at a much finer scale — about 400 m, a few street blocks — where a single
street pattern is something a place can actually have. At that scale, morphology
turned out to be real, measurable, and — imperfectly — validated against human
judgement.

The most useful finding, though, wasn't the map. It was that the same busy
intersection means something different depending on what surrounds it: in
organically-grown streets, the busiest junctions tend to be single points of failure
with no way around them; in gridded streets, the busiest junctions usually have an
alternative route nearby. That distinction — not just *where* the critical points
are, but *what kind* of vulnerability they represent — is what transport-policy
targeting actually needs, and it wasn't even testable until the morphology measure
existed at the right scale.

**Questions this answered:**
- Does the four-archetype typology (grid, maze, radial, periphery) hold at 1–2 km?
  No — and the reason is now known: zones are mixtures at that scale, not single types.
- Is the weak two-way split that does show up real, or just noise? Real, but mostly
  driven by zone size, with a smaller genuine connectivity signal underneath.
- Is morphology measurable once the scale is corrected? Yes, at 400 m, city-wide.
- Does an independent geometric method agree? No — it turned out to be measuring
  mapping density, not shape.
- Does criticality actually depend on local street pattern? Yes — the relationship
  between "busiest intersection" and "single point of failure" flips sign between
  organic and gridded fabric.

**What's still open:**
- The morphology measure discriminates well but falls short of the accuracy target
  the project set for itself — and that gap survives even the best possible
  calibration, so it isn't a tuning problem.
- Validation so far rests on one person's judgement, not the panel originally
  planned, so agreement between independent raters is still unmeasured.
- Radial street patterns were never captured — they need a different kind of
  measure, based on spatial convergence rather than street orientation.
- Everything here measures structure, not the outcome of an actual intervention —
  the policy link is inferred from the literature, not demonstrated.

**Where this could go next:**
- A second, independent labeller, to close the validation gap.
- A convergence-based measure, to bring radial structure into scope.
- Testing whether the criticality-reversal finding holds in other cities with
  similarly mixed, informally-grown fabric.
- Revisiting the learned graph-attention component the original framework proposed
  but never built — now that a validated structural signal exists to condition it on.

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
