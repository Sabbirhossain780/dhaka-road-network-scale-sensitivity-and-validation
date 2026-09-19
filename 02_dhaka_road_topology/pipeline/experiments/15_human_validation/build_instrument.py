#!/usr/bin/env python
"""Experiment 15 (Phase 2) -- blind human validation of the patch grid-score.

Closes the validation gap the proposal set and the project never met: an
expert-morphological-assessment panel with n=30 and a >=85% agreement target.
Experiment 07 managed 7 zones, and Experiment 08 then showed those labels were
unreliable anyway, because a 2km zone has no single morphology to label.

That gap is now closable precisely BECAUSE of what Experiments 08-11 found: a
400m patch does plausibly have one morphology, so "is this grid-like?" is a
well-posed question about it in a way it never was about a zone.

VALIDITY SAFEGUARDS -- each exists to block a specific way this could be fooled:

  BLINDING. The labeller sees anonymous ids in randomised order, never a score,
    never the source zone, never the sampling stratum. The scores live only in
    manifest.csv, which the labelling page does not contain.

  STRATIFIED SAMPLING. Uniform random sampling would draw mostly mid-range
    patches and produce a mushy, uninformative test. Sampling is stratified
    across grid-score deciles so the full range is covered. This is selection on
    the variable under test, so it is declared here and the analysis reports
    per-stratum results rather than only a pooled number.

  SPATIAL SEPARATION. Experiment 11's windows slide at 100m, so neighbours
    overlap and are not independent. Sampled patches are forced >=800m apart.

  PRE-REGISTERED THRESHOLD. The grid/organic boundary is fixed HERE, before any
    label exists, as Experiment 11's existing "above null p95" rule -- a rule
    defined for a different purpose and not tuned for this test. The headline
    statistic is ROC AUC, which needs no threshold at all.

  REPEATED ITEMS. 6 patches appear twice. Self-consistency bounds the agreement
    achievable in principle: if the labeller agrees with themselves only 80% of
    the time, 85% agreement with any measure is not attainable.

  AN "UNCLEAR" OPTION. Experiments 08-09 established that mixed fabric is real.
    Forcing a binary choice on genuinely mixed patches would manufacture noise
    and misrepresent the finding, so "unclear" is a first-class answer.

Usage:
    python experiments/15_human_validation/build_instrument.py
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ZONES = os.path.join(ROOT, "pipeline_outputs", "v2km", "data", "zones")
WINDOWS = os.path.join(HERE, "..", "11_city_mixture_map", "windows.csv")

N_STRATA = 10
PER_STRATUM = 4              # -> 40 unique patches, above the proposal's n=30
N_REPEAT = 6                 # repeated items for self-consistency
MIN_SEP_M = 800.0            # sampled patches must be this far apart
PATCH_M = 400.0
IMG_PX = 460
SEED = 2026


def render_patch(zone_id: str, cx: float, cy: float, cache: dict) -> Image.Image:
    """Draw the streets inside a 400m box centred on (cx, cy), from vector data."""
    if zone_id not in cache:
        nodes = pd.read_csv(os.path.join(ZONES, zone_id, "nodes.csv"))
        links = pd.read_csv(os.path.join(ZONES, zone_id, "links.csv"))
        pos = dict(zip(nodes["node_id"], zip(nodes["x_utm"], nodes["y_utm"])))
        cache[zone_id] = (pos, links)
    pos, links = cache[zone_id]

    half = PATCH_M / 2.0
    scale = IMG_PX / PATCH_M
    img = Image.new("L", (IMG_PX, IMG_PX), 255)
    draw = ImageDraw.Draw(img)
    for _, r in links.iterrows():
        u, v = r["from_node"], r["to_node"]
        if u not in pos or v not in pos:
            continue
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        # keep any segment that could cross the box
        if (max(x1, x2) < cx - half or min(x1, x2) > cx + half or
                max(y1, y2) < cy - half or min(y1, y2) > cy + half):
            continue
        p1 = ((x1 - cx + half) * scale, IMG_PX - (y1 - cy + half) * scale)
        p2 = ((x2 - cx + half) * scale, IMG_PX - (y2 - cy + half) * scale)
        draw.line([p1, p2], fill=0, width=2)
    return img


def main() -> int:
    rng = np.random.default_rng(SEED)
    win = pd.read_csv(WINDOWS)
    pool = win[(~win["sparse"]) & (~win["low_completeness"])].reset_index(drop=True)
    print(f"candidate windows: {len(pool):,}")

    pool["stratum"] = pd.qcut(pool["excess"], N_STRATA, labels=False, duplicates="drop")

    chosen, taken_xy = [], []
    for s in sorted(pool["stratum"].unique()):
        cand = pool[pool["stratum"] == s].sample(frac=1.0, random_state=SEED + int(s))
        got = 0
        for _, r in cand.iterrows():
            if got >= PER_STRATUM:
                break
            if taken_xy:
                d = np.hypot(np.array([p[0] for p in taken_xy]) - r["wx"],
                             np.array([p[1] for p in taken_xy]) - r["wy"])
                if d.min() < MIN_SEP_M:
                    continue
            chosen.append(r)
            taken_xy.append((r["wx"], r["wy"]))
            got += 1
        print(f"  stratum {int(s)}: {got} patches "
              f"(excess {cand['excess'].min():+.3f}..{cand['excess'].max():+.3f})")

    sel = pd.DataFrame(chosen).reset_index(drop=True)
    print(f"\nselected {len(sel)} unique patches, min separation "
          f"{MIN_SEP_M:.0f}m, spanning excess "
          f"{sel['excess'].min():+.3f} to {sel['excess'].max():+.3f}")

    # ---- render, assign anonymous ids -----------------------------------
    cache = {}
    items, manifest = [], []
    for i, r in sel.iterrows():
        img = render_patch(r["zone_id"], r["wx"], r["wy"], cache)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        pid = f"P{i:03d}"
        items.append({"id": pid, "img": b64})
        manifest.append({"item_id": pid, "zone_id": r["zone_id"],
                         "wx": r["wx"], "wy": r["wy"], "stratum": int(r["stratum"]),
                         "grid_score": r["grid_score"], "excess": r["excess"],
                         "null_p95": r["null_p95"],
                         "pre_registered_label": "grid" if r["grid_score"] > r["null_p95"]
                                                 else "organic",
                         "c1": r["c1"], "c2": r["c2"], "is_repeat_of": ""})

    # repeated items, re-encoded under fresh ids so they look like new patches
    rep_idx = rng.choice(len(items), size=N_REPEAT, replace=False)
    for j, k in enumerate(rep_idx):
        pid = f"P{len(items) + j:03d}"
        items.append({"id": pid, "img": items[k]["img"]})
        m = dict(manifest[k])
        m.update(item_id=pid, is_repeat_of=manifest[k]["item_id"])
        manifest.append(m)

    order = rng.permutation(len(items))
    items = [items[i] for i in order]

    pd.DataFrame(manifest).to_csv(os.path.join(HERE, "manifest.csv"), index=False)
    print(f"rendered {len(items)} items ({len(sel)} unique + {N_REPEAT} repeats), "
          f"presentation order randomised")
    print(f"manifest.csv written -- HOLDS THE ANSWERS, do not open before labelling")

    html = build_html(items)
    out = os.path.join(HERE, "labelling_tool.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"labelling_tool.html written ({os.path.getsize(out)/1e6:.1f} MB)")

    with open(os.path.join(HERE, "design.json"), "w") as f:
        json.dump({"n_unique": int(len(sel)), "n_repeat": N_REPEAT,
                   "n_items": len(items), "strata": N_STRATA,
                   "per_stratum": PER_STRATUM, "min_sep_m": MIN_SEP_M,
                   "patch_m": PATCH_M, "seed": SEED,
                   "pre_registered_rule": "grid_score > null_p95 (Experiment 11)",
                   "primary_statistic": "ROC AUC of grid_score vs human label",
                   "proposal_target": 0.85}, f, indent=2)
    return 0


def build_html(items) -> str:
    """Emit the labelling page.

    Written as a fragment (no doctype/html/head/body): the Artifact platform
    supplies that skeleton, and a browser opening the file directly renders it
    fine anyway -- so one file serves both as a local file and as a published
    page. Results come out via clipboard, because the artifact viewer's sandbox
    blocks page-initiated downloads; the download button is offered as a
    secondary path that works when the file is opened locally.
    """
    data = json.dumps([{"id": it["id"], "img": it["img"]} for it in items])
    return """<title>Patch Morphology Labelling</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
:root{
  --paper:#fbfaf8; --card:#ffffff; --ink:#14171c; --muted:#6c7280;
  --line:#e4e1dc; --grid:#2f6f4f; --organic:#b04a35; --unclear:#8a8f98;
  --accent:#3563b8; --shade:#f2efea;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#101317; --card:#181c22; --ink:#e9ecf1; --muted:#98a0ad;
  --line:#2b313a; --grid:#5fc38d; --organic:#e8846c; --unclear:#9aa0aa;
  --accent:#6f9bec; --shade:#1e232a;
}}
:root[data-theme="dark"]{
  --paper:#101317; --card:#181c22; --ink:#e9ecf1; --muted:#98a0ad;
  --line:#2b313a; --grid:#5fc38d; --organic:#e8846c; --unclear:#9aa0aa;
  --accent:#6f9bec; --shade:#1e232a;
}
*{box-sizing:border-box}
body{margin:0;padding-block:28px;padding-left:16px;padding-right:16px;
  background:var(--paper);color:var(--ink);
  font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,sans-serif}
.wrap{max-width:620px;margin:0 auto}
header{margin-bottom:18px}
h1{font:600 25px/1.2 "Source Serif 4",Georgia,serif;margin:0 0 5px;
  text-wrap:balance;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13.5px;margin:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:18px}
.bar{height:3px;background:var(--line);border-radius:2px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent);width:0;transition:width .18s}
.meta{display:flex;justify-content:space-between;align-items:baseline;
  color:var(--muted);font-size:11.5px;margin:9px 0 13px;
  font-family:"IBM Plex Mono",ui-monospace,monospace;letter-spacing:.04em}
figure{margin:0}
img{width:100%;max-width:100%;height:auto;display:block;border-radius:6px;
  background:#fff;border:1px solid var(--line)}
.btns{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-top:16px}
button{font:500 14px/1.2 "IBM Plex Sans",system-ui,sans-serif;padding:14px 6px;
  border-radius:8px;cursor:pointer;border:1px solid var(--line);
  background:var(--card);color:var(--ink);transition:border-color .12s,background .12s}
button:hover{background:var(--shade)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btns button{font-weight:600}
.btns .k{display:block;font:400 10.5px/1 "IBM Plex Mono",monospace;
  color:var(--muted);margin-top:5px;letter-spacing:.06em}
#g{color:var(--grid)}#o{color:var(--organic)}#u{color:var(--unclear)}
#g:hover{border-color:var(--grid)}#o:hover{border-color:var(--organic)}
#u:hover{border-color:var(--unclear)}
.back{margin-top:9px;width:100%;font-weight:400;padding:9px;color:var(--muted)}
.guide{font-size:13px;color:var(--muted);margin-top:15px;padding-top:13px;
  border-top:1px solid var(--line)}
.guide b{color:var(--ink);font-weight:600}
.guide p{margin:0 0 5px}
.done h2{font:600 21px/1.25 "Source Serif 4",Georgia,serif;margin:0 0 6px}
.tally{display:flex;gap:16px;font-size:13px;color:var(--muted);
  margin:0 0 15px;flex-wrap:wrap}
.tally b{font-family:"IBM Plex Mono",monospace;color:var(--ink);font-weight:400}
textarea{width:100%;height:160px;font:12px/1.45 "IBM Plex Mono",ui-monospace,monospace;
  background:var(--paper);color:var(--ink);border:1px solid var(--line);
  border-radius:7px;padding:11px;margin-top:12px;resize:vertical}
.acts{display:flex;gap:9px;flex-wrap:wrap}
.acts button{flex:1;min-width:150px}
#copy{border-color:var(--accent);color:var(--accent);font-weight:600}
</style>
<div class="wrap">
  <header>
    <h1>Patch morphology labelling</h1>
    <p class="sub">Each image is 400&nbsp;m of Dhaka street network. Judge by eye
      alone &mdash; there is no right answer recorded anywhere in this page.</p>
  </header>
  <div id="app"></div>
</div>
<script>
const ITEMS = """ + data + """;
let i = 0; const ans = {};
const app = document.getElementById('app');

function esc(s){ return String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function save(v){
  ans[ITEMS[i].id] = v;
  try{ localStorage.setItem('patchlabels', JSON.stringify(ans)); }catch(e){}
  i++; render();
}
function back(){ if(i > 0){ i--; render(); } }

function render(){
  if(i >= ITEMS.length){ return done(); }
  const it = ITEMS[i];
  const pct = (i / ITEMS.length * 100).toFixed(1);
  app.innerHTML = `
    <div class="card">
      <div class="bar"><i style="width:${pct}%"></i></div>
      <div class="meta"><span>${i+1} / ${ITEMS.length}</span><span>${esc(it.id)}</span></div>
      <figure><img src="data:image/png;base64,${it.img}"
        alt="Street network within a 400 metre square"></figure>
      <div class="btns">
        <button id="g" onclick="save('grid')">Grid-like<span class="k">1</span></button>
        <button id="o" onclick="save('organic')">Organic<span class="k">2</span></button>
        <button id="u" onclick="save('unclear')">Unclear<span class="k">3</span></button>
      </div>
      <button class="back" onclick="back()">&larr; Back</button>
      <div class="guide">
        <p><b>Grid-like</b> &mdash; two roughly perpendicular families of streets
          at fairly regular spacing.</p>
        <p><b>Organic</b> &mdash; irregular, curving or oblique; no repeating pattern.</p>
        <p><b>Unclear</b> &mdash; genuinely mixed, or too little road to judge.
          This is a real answer, not a cop-out.</p>
      </div>
    </div>`;
}

function done(){
  let csv = 'item_id,label\\n';
  ITEMS.forEach(it => { if(ans[it.id]) csv += it.id + ',' + ans[it.id] + '\\n'; });
  window._csv = csv;
  const c = {grid:0, organic:0, unclear:0};
  Object.values(ans).forEach(v => c[v]++);
  app.innerHTML = `
    <div class="card done">
      <h2>All ${ITEMS.length} labelled</h2>
      <p class="tally"><span>grid <b>${c.grid}</b></span>
        <span>organic <b>${c.organic}</b></span>
        <span>unclear <b>${c.unclear}</b></span></p>
      <div class="acts">
        <button id="copy" onclick="copyCsv()">Copy labels</button>
        <button onclick="dl()" title="Only works when this file is opened directly in a browser">Download&nbsp;.csv <span style="color:var(--muted);font-weight:400">(local file only)</span></button>
      </div>
      <textarea readonly onclick="this.select()">${esc(csv)}</textarea>
      <div class="guide">
        <p>Save this as <b>labels.csv</b> in the
          <b>15_human_validation</b> folder, then run <b>score.py</b>.</p>
        <p>Copy works everywhere; the download button only works when this file
          is opened directly in a browser.</p>
      </div>
    </div>`;
}

function copyCsv(){
  const b = document.getElementById('copy');
  const ok = () => { b.textContent = 'Copied \\u2713'; setTimeout(()=>{b.textContent='Copy labels';}, 1800); };
  if(navigator.clipboard){ navigator.clipboard.writeText(window._csv).then(ok, fallback); }
  else fallback();
  function fallback(){
    const t = document.querySelector('textarea');
    t.select(); try{ document.execCommand('copy'); ok(); }
    catch(e){ b.textContent = 'Select the text below'; }
  }
}

function dl(){
  const b = new Blob([window._csv], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(b); a.download = 'labels.csv'; a.click();
}

document.addEventListener('keydown', e => {
  if(i >= ITEMS.length) return;
  if(e.key === '1') save('grid');
  if(e.key === '2') save('organic');
  if(e.key === '3') save('unclear');
  if(e.key === 'Backspace'){ e.preventDefault(); back(); }
});
render();
</script>"""


if __name__ == "__main__":
    sys.exit(main())
