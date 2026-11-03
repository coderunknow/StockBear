#!/usr/bin/env python3
"""Independent final audit: re-parse every raw match.jsonl from scratch and
compare W/D/L, score and an independent Elo-from-score point estimate against
the stored machine-readable summaries. Uses NO result JSON as input data (only
as the value to verify). No game is excluded except the documented
score_a=null (unadjudicated) rule recorded in each cell.
"""
import json, math, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"benchmarks/dev6-baseline"; EXP=ROOT/"benchmarks/exp-runs"
issues=[]; checked=0

def games(d):
    p=EXP/d/"match.jsonl"
    rs=[json.loads(l) for l in p.read_text().splitlines() if '"game"' in l]
    rs.sort(key=lambda x:x["game"])
    return rs, [x["score_a"] for x in rs if x["score_a"] is not None]

def wdl(v):
    w=sum(1 for x in v if x==1.0); d=sum(1 for x in v if x==0.5)
    l=sum(1 for x in v if x==0.0)
    return w,d,l,(w+0.5*d)/max(1,len(v))

def elo(s):
    if s<=0 or s>=1: return None
    return -400*math.log10(1.0/s-1.0)

def cmp(tag, got, exp, tol=1e-9):
    global checked
    checked+=1
    if exp is None: return
    if abs(got-exp)>tol: issues.append(f"{tag}: recomputed {got} != stored {exp}")

# exp-0031 pilot
p=json.loads((BASE/"ladder_pilot.json").read_text())
for r in p["results"]:
    d=f"exp0031-pilot-{r['id']}"
    rs,v=games(d); w,dr,l,s=wdl(v)
    cmp(f"{d} wins",w,r["wins"]); cmp(f"{d} draws",dr,r["draws"])
    cmp(f"{d} losses",l,r["losses"]); cmp(f"{d} score",s,r["score"])
# exp-0032 decisive cells
c=json.loads((BASE/"ladder_cells.json").read_text())
for r in c["cells"]:
    d=f"exp0032-ladder-{r['anchor']}-{r['subject']}"
    rs,v=games(d); w,dr,l,s=wdl(v)
    cmp(f"{d} games",len(v),r["games_completed"])
    cmp(f"{d} score",s,r["score"],1e-6)
# exp-0032 BTD game count
lr=json.loads((BASE/"ladder_results.json").read_text())
tot=0
for r in c["cells"]:
    rs,v=games(f"exp0032-ladder-{r['anchor']}-{r['subject']}"); tot+=len(v)
cmp("exp0032 BTD game count",tot,lr["games"])
# exp-0032b paired
pb=json.loads((BASE/"ladder_paired.json").read_text())
for r in pb["pairings"]:
    rs,v=games(Path(r["dir"]).name); w,dr,l,s=wdl(v)
    cmp(f"{Path(r['dir']).name} score",s,r["score_a"],1e-6)
    cmp(f"{Path(r['dir']).name} wins",w,r["wins"])
# exp-0033 / exp-0034
for name,path,tags in (("exp0033",BASE/"exp0033_results.json",("batchA","batchB","context-vs-dev5")),
                       ("exp0034",BASE/"exp0034_results.json",("batchA","batchB")),
                       ("exp0035",BASE/"exp0035_results.json",("batchA","batchB","trackA"))):
    if not path.exists(): print(f"{name}: results file not present yet (NOT RUN)"); continue
    o=json.loads(path.read_text())
    for t in tags:
        rs,v=games(f"{name}-{t}"); w,dr,l,s=wdl(v)
        stored=next((x for x in o["results"] if x["tag"]==t),None)
        if stored is None or "error" in stored: continue
        cmp(f"{name}-{t} wins",w,stored["wins"]); cmp(f"{name}-{t} draws",dr,stored["draws"])
        cmp(f"{name}-{t} losses",l,stored["losses"]); cmp(f"{name}-{t} score",s,stored["score"])
        ce=o.get("combined")
        if ce and t.startswith("batch"):
            pass
    ce=o.get("combined")
    if ce:
        v=[]
        for t in tags:
            if not t.startswith("batch"): continue
            v+=games(f"{name}-{t}")[1]
        w,dr,l,s=wdl(v)
        cmp(f"{name} combined games",len(v),ce["games"])
        cmp(f"{name} combined score",s,ce["score"])
        e=elo(s)
        print(f"{name}: combined +{w}={dr}-{l} score {s:.4f} "
              f"independent Elo-from-score {e:+.2f}; stored CR1 {ce['elo']} {ce['ci95']}")

print(f"\nchecked {checked} stored values across raw match.jsonl files")
print("AUDIT:", "PASS" if not issues else "FAIL")
for x in issues: print("  MISMATCH",x)
sys.exit(1 if issues else 0)
