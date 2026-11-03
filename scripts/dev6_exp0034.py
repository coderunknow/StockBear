#!/usr/bin/env python3
"""exp-0034 pilot: SEE bad-capture pruning, ONE binary / ONE UCI switch.
Frozen design: docs/DEV6_PREREG_EXP0034.md. 2 disjoint 400-opening batches x
400 games = 800 paired games, fixed-node 6000 +/- 15%. Pilot, NOT a gate test."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats
PY = ROOT / ".venv/bin/python"; POS = ROOT/"benchmarks/positions"
EXP = ROOT/"benchmarks/exp-runs"; OUT = ROOT/"benchmarks/dev6-baseline/exp0034_results.json"
BIN = str(ROOT/"build-exp0034/stockbear"); ABC = "research-data/params_abc.txt"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def suite():
    p = POS/"openings_exp0034.txt"
    if not p.exists():
        subprocess.run([str(PY), str(ROOT/"scripts/exp_confirmation_openings.py"),
                        "--name","exp0034","--seed","2026111501","--count","800"],
                       cwd=ROOT, check=True, capture_output=True)
        (POS/"openings_exp0034_confirmation.txt").rename(p)
    return p, [l for l in p.read_text().splitlines() if l and not l.startswith("#")]

def run(tag, slice_path, seed):
    d = EXP/f"exp0034-{tag}"; d.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), str(ROOT/"scripts/tournament.py"), "--engine-a", BIN,
           "--engine-b", BIN, "--games","400","--base-ms","40","--inc-ms","4",
           "--hash","16","--threads","1","--max-plies","240",
           "--nodes","6000","--nodes-jitter","0.15",
           "--openings",str(slice_path),"--seed",str(seed),
           "--a-option",f"EvalParams={ABC}","--a-option","TTEval=true",
           "--a-option","BadCapturePruning=true",
           "--b-option",f"EvalParams={ABC}","--b-option","TTEval=true",
           "--b-option","BadCapturePruning=false",
           "--pgn",str(d/"match.pgn"),"--jsonl",str(d/"match.jsonl"),
           "--csv",str(d/"match.csv")]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode: return {"tag":tag,"error":r.stderr[-800:]}
    recs=[json.loads(l) for l in (d/"match.jsonl").read_text().splitlines() if '"game"' in l]
    recs.sort(key=lambda x:x["game"])
    pairs=[];terms={}
    for k in range(0,len(recs)-1,2):
        a,b=recs[k],recs[k+1]
        if a["score_a"] is not None and b["score_a"] is not None:
            pairs.append(a["score_a"]+b["score_a"])
    for x in recs: terms[x.get("termination","?")]=terms.get(x.get("termination","?"),0)+1
    g=[x["score_a"] for x in recs if x["score_a"] is not None]
    s=match_stats.summarise(g,pairs,match_stats.lmr_step(pairs,0.0,5.0))
    cl=s.get("opening_clustered",{})
    return {"tag":tag,"dir":str(d.relative_to(ROOT)),"games":len(g),
            "unadjudicated":len(recs)-len(g),"wins":s["wins"],"draws":s["draws"],
            "losses":s["losses"],"score":(s["wins"]+0.5*s["draws"])/max(1,len(g)),
            "elo":cl.get("elo_difference"),"ci95":cl.get("elo_ci95"),
            "clusters":cl.get("clusters"),"terminations":terms,
            "time_forfeit":sum(v for k,v in terms.items() if "FORFEIT" in k.upper()),
            "illegal":sum(v for k,v in terms.items() if "ILLEGAL" in k.upper())}

def main():
    master,lines=suite(); assert len(lines)==800,len(lines)
    slices=[]
    for i,t in enumerate(("batchA","batchB")):
        p=POS/f"openings_exp0034_{t}.txt"
        p.write_text("\n".join(lines[i*400:(i+1)*400])+"\n"); slices.append(p)
    out=[]
    for i,t in enumerate(("batchA","batchB")):
        r=run(t,slices[i],2026111600+i); out.append(r)
        print(t, f"ERROR {r['error'][:120]}" if "error" in r else
              f"score {r['score']:.4f} +{r['wins']}={r['draws']}-{r['losses']} "
              f"Elo {r['elo']:+.2f} {r['ci95']} forfeits {r['time_forfeit']}", flush=True)
    ok=[r for r in out if "error" not in r]; combined=None
    if len(ok)==2:
        g=[];pairs=[]
        for r in ok:
            recs=[json.loads(l) for l in (ROOT/r["dir"]/"match.jsonl").read_text().splitlines() if '"game"' in l]
            recs.sort(key=lambda x:x["game"])
            v=[x["score_a"] for x in recs if x["score_a"] is not None]; g+=v
            pairs+= [v[k]+v[k+1] for k in range(0,len(v)-1,2)]
        s=match_stats.summarise(g,pairs,match_stats.lmr_step(pairs,0.0,5.0))
        combined={"games":len(g),"wins":s["wins"],"draws":s["draws"],"losses":s["losses"],
                  "score":(s["wins"]+0.5*s["draws"])/max(1,len(g)),
                  "elo":s.get("opening_clustered",{}).get("elo_difference"),
                  "ci95":s.get("opening_clustered",{}).get("elo_ci95")}
        print("combined:",json.dumps(combined),flush=True)
    OUT.write_text(json.dumps({"experiment":"exp-0034","prereg":"docs/DEV6_PREREG_EXP0034.md",
        "control":"same binary, BadCapturePruning=true vs false",
        "binary_sha256":sha(BIN),"master_suite_sha256":sha(master),
        "results":out,"combined":combined},indent=2)+"\n")
    print("wrote",OUT)
if __name__=="__main__": main()
