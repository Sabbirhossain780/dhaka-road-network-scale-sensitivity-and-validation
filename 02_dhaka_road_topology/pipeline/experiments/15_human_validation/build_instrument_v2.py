#!/usr/bin/env python
"""Experiment 15b -- corrected blind validation instrument.

Experiment 15 failed its target (68.0% agreement vs 85%, AUC 0.663 p=0.083) and
its post-mortem identified four fixable design errors. This is the corrected
instrument. It is a SEPARATE PRE-REGISTERED TEST, not a retry: its result is
reported whatever it says, and v1's negative result stands in the log regardless.

WHAT CHANGED, AND WHY EACH CHANGE WAS FORCED BY THE DATA

  1. "UNCLEAR" IS SPLIT IN TWO. v1 offered one button described as "genuinely
     mixed, OR too little road to judge" -- two unrelated things. It was used
     almost entirely for the second: unclear patches had a median 1,203m of road
     vs 4,570m for decided ones (Mann-Whitney p < 0.0001). That destroyed 21 of
     46 items and meant the organic end of the scale was never actually tested.
     Now: "Mixed" is a substantive answer ABOUT morphology; "Can't judge" is a
     complaint about the DATA. They are scored completely differently.

  2. DENSITY FLOOR RAISED 500m -> 1500m. v1 sampled from Experiment 11's
     scorable pool, whose floor was 500m of road per 400m window. v1 showed
     humans cannot judge anywhere near that: 0 of 16 patches above 3,000m were
     called unclear, versus 21 of 46 above 500m. Sampling now requires >=1500m.

  3. MORE ITEMS. v1 yielded only 25 decided labels -- underpowered for an AUC
     test. 60 unique patches, and with the density floor most should be decidable.

  4. MULTI-RATER. v1 had one labeller whose self-consistency was 66.7%, which
     caps everything and cannot be separated from measure error. The page now
     asks who is labelling, records it, and gives each rater an independently
     shuffled order. Cohen's kappa between raters is the quantity the proposal's
     "expert panel" design existed to supply.

  FRESH PATCHES. The 40 patches shown in v1 are excluded, so recognition of a
  previously-seen image cannot contaminate this run.

PRE-REGISTERED ANALYSIS (fixed here, before any v2 label exists; score_v2.py
implements exactly this and nothing more):
  PRIMARY    ROC AUC of grid_score, grid vs organic, excluding mixed/can't-judge.
  SECONDARY  Ordinal Spearman across organic < mixed < grid. Better powered than
             the binary test because it uses the mixed items instead of dropping
             them.
  DIRECTIONAL PREDICTION  mean grid_score: organic < mixed < grid. v1 predicted
             "unclear" would sit mid-range and it did NOT (it sat low, because it
             meant "can't see"). With the meanings separated, "mixed" genuinely
             should sit between. If it does not, the measure is not tracking
             morphological mixture and that is a substantive negative finding.
  AGREEMENT  accuracy at Experiment 11's pre-existing grid_score > null_p95 rule.
  CEILINGS   per-rater self-consistency from repeats; Cohen's kappa between
             raters when there are >=2.

Usage:
    python experiments/15_human_validation/build_instrument_v2.py
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

from build_instrument import render_patch          # identical rendering as v1

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS = os.path.join(HERE, "..", "11_city_mixture_map", "windows.csv")

MIN_ROAD_M = 1500.0          # fix 2 -- humans cannot judge below roughly this
N_STRATA = 10
PER_STRATUM = 6              # fix 3 -> 60 unique patches
N_REPEAT = 8                 # fix 4 -- per-rater self-consistency
MIN_SEP_M = 800.0
SEED = 20262                 # different from v1's 2026


def main() -> int:
    rng = np.random.default_rng(SEED)
    win = pd.read_csv(WINDOWS)
    pool = win[(~win["sparse"]) & (~win["low_completeness"]) &
               (win["road_len_m"] >= MIN_ROAD_M)].reset_index(drop=True)
    print(f"pool after density floor ({MIN_ROAD_M:.0f}m): {len(pool):,} windows "
          f"(was {int(((~win['sparse']) & (~win['low_completeness'])).sum()):,})")

    # exclude anything shown in v1
    seen = pd.read_csv(os.path.join(HERE, "manifest.csv"))[["wx", "wy"]].round(1)
    seen_set = set(map(tuple, seen.values))
    keep = [t not in seen_set for t in zip(pool["wx"].round(1), pool["wy"].round(1))]
    pool = pool[keep].reset_index(drop=True)
    print(f"after excluding v1 patches: {len(pool):,}")

    pool["stratum"] = pd.qcut(pool["excess"], N_STRATA, labels=False, duplicates="drop")

    chosen, taken = [], []
    for s in sorted(pool["stratum"].unique()):
        cand = pool[pool["stratum"] == s].sample(frac=1.0, random_state=SEED + int(s))
        got = 0
        for _, r in cand.iterrows():
            if got >= PER_STRATUM:
                break
            if taken:
                d = np.hypot(np.array([p[0] for p in taken]) - r["wx"],
                             np.array([p[1] for p in taken]) - r["wy"])
                if d.min() < MIN_SEP_M:
                    continue
            chosen.append(r); taken.append((r["wx"], r["wy"])); got += 1
        print(f"  stratum {int(s)}: {got}")

    sel = pd.DataFrame(chosen).reset_index(drop=True)
    print(f"\nselected {len(sel)} unique patches, excess "
          f"{sel['excess'].min():+.3f} to {sel['excess'].max():+.3f}, "
          f"road {sel['road_len_m'].min():.0f}-{sel['road_len_m'].max():.0f} m")

    cache, items, manifest = {}, [], []
    for i, r in sel.iterrows():
        img = render_patch(r["zone_id"], r["wx"], r["wy"], cache)
        buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True)
        pid = f"Q{i:03d}"
        items.append({"id": pid, "img": base64.b64encode(buf.getvalue()).decode()})
        manifest.append({"item_id": pid, "zone_id": r["zone_id"], "wx": r["wx"],
                         "wy": r["wy"], "stratum": int(r["stratum"]),
                         "grid_score": r["grid_score"], "excess": r["excess"],
                         "null_p95": r["null_p95"], "road_len_m": r["road_len_m"],
                         "c1": r["c1"], "c2": r["c2"],
                         "pre_registered_label": "grid" if r["grid_score"] > r["null_p95"]
                                                 else "organic",
                         "is_repeat_of": ""})

    # repeats -- ids assigned from a running counter (v1 double-counted and
    # produced gappy ids; harmless but confusing)
    n_unique = len(items)
    for j, k in enumerate(rng.choice(n_unique, size=N_REPEAT, replace=False)):
        pid = f"Q{n_unique + j:03d}"
        items.append({"id": pid, "img": items[k]["img"]})
        m = dict(manifest[k]); m.update(item_id=pid, is_repeat_of=manifest[k]["item_id"])
        manifest.append(m)

    pd.DataFrame(manifest).to_csv(os.path.join(HERE, "manifest_v2.csv"), index=False)
    print(f"{len(items)} items ({n_unique} unique + {N_REPEAT} repeats)")
    print("manifest_v2.csv written -- HOLDS THE ANSWERS")

    out = os.path.join(HERE, "labelling_tool_v2.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(build_html(items))
    print(f"labelling_tool_v2.html written ({os.path.getsize(out)/1e6:.1f} MB)")

    with open(os.path.join(HERE, "design_v2.json"), "w") as f:
        json.dump({"version": 2, "n_unique": n_unique, "n_repeat": N_REPEAT,
                   "n_items": len(items), "min_road_m": MIN_ROAD_M,
                   "strata": N_STRATA, "per_stratum": PER_STRATUM,
                   "min_sep_m": MIN_SEP_M, "seed": SEED,
                   "excluded_v1_patches": True,
                   "labels": ["grid", "organic", "mixed", "cant_judge"],
                   "primary": "ROC AUC grid_score, grid vs organic",
                   "secondary": "ordinal Spearman organic<mixed<grid",
                   "directional_prediction": "mean grid_score: organic < mixed < grid",
                   "agreement_rule": "grid_score > null_p95 (Experiment 11)",
                   "target": 0.85}, f, indent=2)
    return 0


def build_html(items) -> str:
    data = json.dumps([{"id": it["id"], "img": it["img"]} for it in items])
    return """<title>Patch Morphology Labelling</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
:root{--paper:#fbfaf8;--card:#fff;--ink:#14171c;--muted:#6c7280;--line:#e4e1dc;
--grid:#2f6f4f;--organic:#b04a35;--mixed:#8a6d1f;--skip:#8a8f98;
--accent:#3563b8;--shade:#f2efea}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--paper:#101317;--card:#181c22;--ink:#e9ecf1;--muted:#98a0ad;--line:#2b313a;
--grid:#5fc38d;--organic:#e8846c;--mixed:#d9b25e;--skip:#9aa0aa;
--accent:#6f9bec;--shade:#1e232a}}
:root[data-theme="dark"]{--paper:#101317;--card:#181c22;--ink:#e9ecf1;--muted:#98a0ad;
--line:#2b313a;--grid:#5fc38d;--organic:#e8846c;--mixed:#d9b25e;--skip:#9aa0aa;
--accent:#6f9bec;--shade:#1e232a}
*{box-sizing:border-box}
body{margin:0;padding-block:28px;padding-left:16px;padding-right:16px;
background:var(--paper);color:var(--ink);
font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,sans-serif}
.wrap{max-width:620px;margin:0 auto}
header{margin-bottom:18px}
h1{font:600 25px/1.2 "Source Serif 4",Georgia,serif;margin:0 0 5px;
text-wrap:balance;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13.5px;margin:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px}
.bar{height:3px;background:var(--line);border-radius:2px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent);width:0;transition:width .18s}
.meta{display:flex;justify-content:space-between;align-items:baseline;color:var(--muted);
font-size:11.5px;margin:9px 0 13px;font-family:"IBM Plex Mono",monospace;letter-spacing:.04em}
figure{margin:0}
img{width:100%;max-width:100%;height:auto;display:block;border-radius:6px;
background:#fff;border:1px solid var(--line)}
.btns{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:16px}
button{font:500 14px/1.2 "IBM Plex Sans",system-ui,sans-serif;padding:14px 8px;
border-radius:8px;cursor:pointer;border:1px solid var(--line);background:var(--card);
color:var(--ink);transition:border-color .12s,background .12s}
button:hover{background:var(--shade)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btns button{font-weight:600}
.btns .k{display:block;font:400 10.5px/1 "IBM Plex Mono",monospace;color:var(--muted);
margin-top:5px;letter-spacing:.06em}
#g{color:var(--grid)}#o{color:var(--organic)}#m{color:var(--mixed)}#s{color:var(--skip)}
#g:hover{border-color:var(--grid)}#o:hover{border-color:var(--organic)}
#m:hover{border-color:var(--mixed)}#s:hover{border-color:var(--skip)}
.back{margin-top:9px;width:100%;font-weight:400;padding:9px;color:var(--muted)}
.guide{font-size:13px;color:var(--muted);margin-top:15px;padding-top:13px;
border-top:1px solid var(--line)}
.guide b{color:var(--ink);font-weight:600}
.guide p{margin:0 0 5px}
.note{background:var(--shade);border-radius:7px;padding:10px 12px;font-size:12.5px;
color:var(--muted);margin-top:11px}
input[type=text]{width:100%;font:15px "IBM Plex Sans",system-ui,sans-serif;padding:11px;
border-radius:8px;border:1px solid var(--line);background:var(--paper);color:var(--ink);
margin:10px 0}
.done h2{font:600 21px/1.25 "Source Serif 4",Georgia,serif;margin:0 0 6px}
.tally{display:flex;gap:15px;font-size:13px;color:var(--muted);margin:0 0 15px;flex-wrap:wrap}
.tally b{font-family:"IBM Plex Mono",monospace;color:var(--ink);font-weight:400}
textarea{width:100%;height:160px;font:12px/1.45 "IBM Plex Mono",monospace;
background:var(--paper);color:var(--ink);border:1px solid var(--line);border-radius:7px;
padding:11px;margin-top:12px;resize:vertical}
.acts{display:flex;gap:9px;flex-wrap:wrap}
.acts button{flex:1;min-width:150px}
#copy{border-color:var(--accent);color:var(--accent);font-weight:600}
</style>
<div class="wrap">
  <header>
    <h1>Patch morphology labelling</h1>
    <p class="sub">Each image is 400&nbsp;m of Dhaka street network. Judge by eye
      alone &mdash; no answer is recorded anywhere in this page.</p>
  </header>
  <div id="app"></div>
</div>
<script>
const ITEMS_RAW = """ + data + """;
let ITEMS = ITEMS_RAW.slice();
let rater = '', i = 0, ans = {};
const app = document.getElementById('app');

function esc(s){ return String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// each rater sees an independently shuffled order, seeded by their name
function seedFrom(s){ let h=2166136261; for(const c of s){ h^=c.charCodeAt(0); h=Math.imul(h,16777619);} return h>>>0; }
function mulberry32(a){ return function(){ a|=0; a=a+1831565813|0; let t=Math.imul(a^a>>>15,1|a);
  t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
function shuffle(arr, seed){ const r=mulberry32(seed); const a=arr.slice();
  for(let k=a.length-1;k>0;k--){ const j=Math.floor(r()*(k+1)); [a[k],a[j]]=[a[j],a[k]]; } return a; }

function key(){ return 'patchlabels_v2_' + rater.toLowerCase().replace(/\\s+/g,'_'); }
function persist(){ try{ localStorage.setItem(key(), JSON.stringify({i, ans})); }catch(e){} }

function start(){
  const v = document.getElementById('who').value.trim();
  if(!v){ document.getElementById('who').focus(); return; }
  rater = v;
  ITEMS = shuffle(ITEMS_RAW, seedFrom(rater.toLowerCase()));
  try{
    const prev = JSON.parse(localStorage.getItem(key()) || 'null');
    if(prev && prev.i > 0){ i = prev.i; ans = prev.ans || {}; }
  }catch(e){}
  render();
}

function intro(){
  app.innerHTML = `
    <div class="card">
      <p style="margin:0 0 4px"><b>Who is labelling?</b></p>
      <p class="sub" style="margin:0">Your name or initials. It only separates one
        rater's answers from another's, and lets you stop and resume.</p>
      <input type="text" id="who" placeholder="e.g. SH" autocomplete="off">
      <button onclick="start()" style="width:100%;border-color:var(--accent);
        color:var(--accent);font-weight:600">Begin &rarr;</button>
      <div class="guide">
        <p><b>Grid-like</b> &mdash; two roughly perpendicular families of streets at
          fairly regular spacing.</p>
        <p><b>Organic</b> &mdash; irregular, curving or oblique; no repeating pattern.</p>
        <p><b>Mixed</b> &mdash; you can see <i>both</i> kinds of fabric in the same
          image. This is a real answer about the shape.</p>
        <p><b>Can't judge</b> &mdash; not enough road drawn to tell. This is a
          complaint about the image, not an answer about the shape.</p>
      </div>
      <div class="note">Mixed and Can't judge mean different things and are scored
        differently. Please don't use one for the other &mdash; running them together
        is what invalidated the previous round.</div>
    </div>`;
  document.getElementById('who').addEventListener('keydown', e => { if(e.key==='Enter') start(); });
}

function save(v){ ans[ITEMS[i].id] = v; i++; persist(); render(); }
function back(){ if(i>0){ i--; persist(); render(); } }

function render(){
  if(!rater) return intro();
  if(i >= ITEMS.length) return done();
  const it = ITEMS[i], pct = (i/ITEMS.length*100).toFixed(1);
  app.innerHTML = `
    <div class="card">
      <div class="bar"><i style="width:${pct}%"></i></div>
      <div class="meta"><span>${i+1} / ${ITEMS.length}</span>
        <span>${esc(rater)} &middot; ${esc(it.id)}</span></div>
      <figure><img src="data:image/png;base64,${it.img}"
        alt="Street network within a 400 metre square"></figure>
      <div class="btns">
        <button id="g" onclick="save('grid')">Grid-like<span class="k">1</span></button>
        <button id="o" onclick="save('organic')">Organic<span class="k">2</span></button>
        <button id="m" onclick="save('mixed')">Mixed<span class="k">3</span></button>
        <button id="s" onclick="save('cant_judge')">Can't judge<span class="k">4</span></button>
      </div>
      <button class="back" onclick="back()">&larr; Back</button>
      <div class="guide">
        <p><b>Mixed</b> = both fabrics visible. <b>Can't judge</b> = too little road
          drawn to tell. These are not the same answer.</p>
      </div>
    </div>`;
}

function done(){
  let csv = 'rater,item_id,label\\n';
  ITEMS.forEach(it => { if(ans[it.id]) csv += rater + ',' + it.id + ',' + ans[it.id] + '\\n'; });
  window._csv = csv;
  const c = {grid:0, organic:0, mixed:0, cant_judge:0};
  Object.values(ans).forEach(v => c[v]++);
  app.innerHTML = `
    <div class="card done">
      <h2>All ${ITEMS.length} labelled</h2>
      <p class="tally"><span>grid <b>${c.grid}</b></span>
        <span>organic <b>${c.organic}</b></span>
        <span>mixed <b>${c.mixed}</b></span>
        <span>can't judge <b>${c.cant_judge}</b></span></p>
      <div class="acts">
        <button id="copy" onclick="copyCsv()">Copy labels</button>
        <button onclick="dl()" title="Only works when this file is opened directly in a browser">Download&nbsp;.csv <span style="color:var(--muted);font-weight:400">(local file only)</span></button>
      </div>
      <textarea readonly onclick="this.select()">${esc(csv)}</textarea>
      <div class="guide"><p>Save as <b>labels_v2.csv</b> in
        <b>15_human_validation</b>, then run <b>score_v2.py</b>. If more than one
        person labels, append their rows to the same file.</p></div>
    </div>`;
}

function copyCsv(){
  const b = document.getElementById('copy');
  const ok = () => { b.textContent='Copied \\u2713'; setTimeout(()=>{b.textContent='Copy labels';},1800); };
  if(navigator.clipboard){ navigator.clipboard.writeText(window._csv).then(ok, fb); } else fb();
  function fb(){ const t=document.querySelector('textarea'); t.select();
    try{ document.execCommand('copy'); ok(); }catch(e){ b.textContent='Select the text below'; } }
}
function dl(){ const b=new Blob([window._csv],{type:'text/csv'}); const a=document.createElement('a');
  a.href=URL.createObjectURL(b); a.download='labels_v2.csv'; a.click(); }

document.addEventListener('keydown', e => {
  if(!rater || i >= ITEMS.length) return;
  if(e.key==='1') save('grid');
  if(e.key==='2') save('organic');
  if(e.key==='3') save('mixed');
  if(e.key==='4') save('cant_judge');
  if(e.key==='Backspace'){ e.preventDefault(); back(); }
});
render();
</script>"""


if __name__ == "__main__":
    sys.exit(main())
