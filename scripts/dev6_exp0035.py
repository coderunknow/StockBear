#!/usr/bin/env python3
"""exp-0035 larger fixed-node confirmation of SEE bad-capture pruning.
Frozen design: docs/DEV6_PREREG_EXP0035.md. 2 x 1000 primary games + 600
Track A context games. Robust None-safe pairing (fix for earlier crashes)."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
import match_stats
PY=ROOT/".venv/bin/python"; POS=ROOT/"benchmarks/positions"
EXP=ROOT/"benchmarks/exp-runs"; OUT=ROOT/"benchmarks/dev6-baseline/exp0035_results.json"
CAND=str(ROOT/"build-exp0034/stockbear"); A1=str(ROOT/"build-dev5/stockbear")
ABC="research-data/params_abc.txt"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def suite():
    p=POS/"openings_exp0035.txt"
    if not p.exists():
        subprocess.run([str(PY),str(ROOT/"scripts/exp_confirmation_openings.py"),
                        "--name","exp0035","--seed","2026111701","--count","2300"],
                       cwd=ROOT,check=True,capture_output=True)
        (POS/"openings_exp0035_confirmation.txt").rename(p)
    return p,[l for l in p.read_text().splitlines() if l and not l.startswith("#")]

def summarise(recs):
    recs.sort(key=lambda x:x["game"]); pairs=[];po=[];terms={}
    for k in range(0,len(recs)-1,2):
        a,b=recs[k],recs[k+1]
        if a["score_a"] is not None and b["score_a"] is not None:
            pairs.append(a["score_a"]+b["score_a"]); po.append(a["opening"])
    for x in recs: terms[x.get("termination","?")]=terms.get(x.get("termination","?"),0)+1
    g=[x["score_a"] for x in recs if x["score_a"] is not None]
    s=match_stats.summarise(g,pairs,match_stats.lmr_step(pairs,0.0,5.0),pair_openings=po)
    cl=s.get("opening_clustered",{})
    return {"games":len(g),"unadjudicated":len(recs)-len(g),"wins":s["wins"],
      "draws":s["draws"],"losses":s["losses"],
      "score":(s["wins"]+0.5*s["draws"])/max(1,len(g)),
      "elo":cl.get("elo_difference"),"ci95":cl.get("elo_ci95"),
      "clusters":cl.get("clusters"),"terminations":terms,
      "time_forfeit":sum(v for k,v in terms.items() if "FORFEIT" in k.upper()),
      "illegal":sum(v for k,v in terms.items() if "ILLEGAL" in k.upper())},recs

def run(tag,a,b,aopts,bopts,slice_path,games,seed):
    d=EXP/f"exp0035-{tag}"; d.mkdir(parents=True,exist_ok=True)
    cmd=[str(PY),str(ROOT/"scripts/tournament.py"),"--engine-a",a,"--engine-b",b,
      "--games",str(games),"--base-ms","40","--inc-ms","4","--hash","16",
      "--threads","1","--max-plies","240","--nodes","6000","--nodes-jitter","0.15",
      "--openings",str(slice_path),"--seed",str(seed)]
    for o in aopts: cmd+=["--a-option",o]
    for o in bopts: cmd+=["--b-option",o]
    cmd+=["--pgn",str(d/"match.pgn"),"--jsonl",str(d/"match.jsonl"),"--csv",str(d/"match.csv")]
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    if r.returncode: return {"tag":tag,"error":r.stderr[-800:]},None
    recs=[json.loads(l) for l in (d/"match.jsonl").read_text().splitlines() if '"game"' in l]
    s,recs=summarise(recs); s.update({"tag":tag,"dir":str(d.relative_to(ROOT)),"seed":seed,
      "openings_sha256":sha(slice_path)})
    return s,recs

def main():
    master,lines=suite(); assert len(lines)==2300,len(lines)
    slices=[]
    for i,t in enumerate(("batchA","batchB","trackA")):
        n=1000 if i<2 else 300
        off=0 if i==0 else (1000 if i==1 else 2000)
        p=POS/f"openings_exp0035_{t}.txt"
        p.write_text("\n".join(lines[off:off+n])+"\n"); slices.append(p)
    on=[f"EvalParams={ABC}","TTEval=true","BadCapturePruning=true"]
    off=[f"EvalParams={ABC}","TTEval=true","BadCapturePruning=false"]
    a1=[f"EvalParams={ABC}","TTEval=true"]
    specs=[("batchA",CAND,CAND,on,off,slices[0],1000,2026111800),
           ("batchB",CAND,CAND,on,off,slices[1],1000,2026111801),
           ("trackA",CAND,A1,on,a1,slices[2],600,2026111802)]
    results=[];allrecs=[]
    for sp in specs:
        r,recs=run(*sp); results.append(r)
        if recs is not None and sp[0]!="trackA": allrecs.append(recs)
        print(sp[0],f"ERROR {r['error'][:120]}" if "error" in r else
              f"score {r['score']:.4f} +{r['wins']}={r['draws']}-{r['losses']} "
              f"Elo {r['elo']} {r['ci95']} forfeits {r['time_forfeit']}",flush=True)
    combined=None
    if len(allrecs)==2:
        g=[];pairs=[];po=[]
        for rs in allrecs:
            g+=[x["score_a"] for x in rs if x["score_a"] is not None]
            for k in range(0,len(rs)-1,2):
                a,b=rs[k],rs[k+1]
                if a["score_a"] is not None and b["score_a"] is not None:
                    pairs.append(a["score_a"]+b["score_a"]);po.append(a["opening"])
        s=match_stats.summarise(g,pairs,match_stats.lmr_step(pairs,0.0,5.0),pair_openings=po)
        cl=s.get("opening_clustered",{})
        combined={"games":len(g),"wins":s["wins"],"draws":s["draws"],"losses":s["losses"],
          "score":(s["wins"]+0.5*s["draws"])/max(1,len(g)),
          "elo":cl.get("elo_difference"),"ci95":cl.get("elo_ci95"),"clusters":cl.get("clusters")}
        print("combined:",json.dumps(combined),flush=True)
    ta=next((r for r in results if r["tag"]=="trackA" and "error" not in r),None)
    ok=bool(combined and combined["elo"]>=10 and combined["ci95"][0]>0 and
            all(r.get("elo",-99)>=-5 for r in results if r["tag"].startswith("batch") and "error" not in r)
            and ta and ta["ci95"][0]>-10)
    print("DECISION:", "CONFIRMED (fixed-node only)" if ok else "NOT CONFIRMED",flush=True)
    OUT.write_text(json.dumps({"experiment":"exp-0035","prereg":"docs/DEV6_PREREG_EXP0035.md",
      "candidate_binary_sha256":sha(CAND),"trackA_dev5_rebuilt_sha256":sha(A1),
      "master_suite_sha256":sha(master),"results":results,"combined":combined,
      "decision":"CONFIRMED (fixed-node only)" if ok else "NOT CONFIRMED"},indent=2)+"\n")
    print("wrote",OUT)
if __name__=="__main__": main()
