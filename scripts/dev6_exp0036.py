#!/usr/bin/env python3
"""exp-0036 FIXED-TIME confirmation, prereg docs/DEV6_PREREG_EXP0036.md.
Stage 0 (400-game null, dedicated core) is a frozen VALIDITY GATE; Stage 1 is
NOT run unless it passes. Uses 40+4 ms, never --nodes. One authorized push only,
so GitHub isolated-VM lane is NOT used (see prereg §1)."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/"scripts"))
import match_stats
PY = ROOT/".venv/bin/python"; POS = ROOT/"benchmarks/positions"
EXP = ROOT/"benchmarks/exp-runs"; OUT = ROOT/"benchmarks/dev6-baseline/exp0036_results.json"
CAND = str(ROOT/"build-exp0034/stockbear"); DEV5 = str(ROOT/"benchmarks/binaries/stockbear-dev5-release")
A1 = str(ROOT/"build-dev5/stockbear"); ABC = "research-data/params_abc.txt"
BASE_OPTS = [f"EvalParams={ABC}", "TTEval=true"]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def suites():
    master = POS/"openings_exp0036.txt"
    if not master.exists():
        subprocess.run([str(PY), str(ROOT/"scripts/exp_confirmation_openings.py"),
                        "--name","exp0036","--seed","2026111901","--count","1600"],
                       cwd=ROOT, check=True, capture_output=True)
        (POS/"openings_exp0036_confirmation.txt").rename(master)
    lines=[l for l in master.read_text().splitlines() if l and not l.startswith("#")]
    assert len(lines)==1600, len(lines)
    sizes=[("stage0",200),("batchA",500),("batchB",500),("null",200),("trackA",200)]
    out={}; off=0
    for name,n in sizes:
        p=POS/f"openings_exp0036_{name}.txt"
        p.write_text("\n".join(lines[off:off+n])+"\n"); out[name]=p; off+=n
    return master,out

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
      "illegal":sum(v for k,v in terms.items() if "ILLEGAL" in k.upper()),
      "uci_fail":sum(v for k,v in terms.items() if "UCI" in k.upper())},recs

def run(tag,a,b,aopts,bopts,slice_path,games,seed):
    d=EXP/f"exp0036-{tag}"; d.mkdir(parents=True,exist_ok=True)
    # dedicated-core: CPU 1 for harness + both engines, CPU 0 left for OS/other
    cmd=["taskset","-c","1",str(PY),str(ROOT/"scripts/tournament.py"),
      "--engine-a",a,"--engine-b",b,"--games",str(games),
      "--base-ms","40","--inc-ms","4","--hash","16","--threads","1",
      "--max-plies","240","--openings",str(slice_path),"--seed",str(seed)]
    for o in aopts: cmd+=["--a-option",o]
    for o in bopts: cmd+=["--b-option",o]
    cmd+=["--pgn",str(d/"match.pgn"),"--jsonl",str(d/"match.jsonl"),"--csv",str(d/"match.csv")]
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    if r.returncode: return {"tag":tag,"error":r.stderr[-1000:]},None
    recs=[json.loads(l) for l in (d/"match.jsonl").read_text().splitlines() if '"game"' in l]
    s,recs=summarise(recs)
    s.update({"tag":tag,"dir":str(d.relative_to(ROOT)),"seed":seed,
      "control":"FIXED TIME 40+4 ms (no --nodes)","openings_sha256":sha(slice_path),
      "command":" ".join(cmd)})
    return s,recs

def nps_ratio():
    import csv
    def one(binary):
        best=None
        for _ in range(3):
            p=subprocess.run([binary,"bench","--depth","12","--params",ABC],
                             cwd=ROOT,capture_output=True,text=True)
            rows=[next(csv.reader([l])) for l in p.stdout.splitlines()
                  if l and not l.startswith('#') and not l.startswith('name,')]
            n=sum(int(r[5]) for r in rows); t=sum(int(r[6]) for r in rows)
            rate=n/max(1,t)*1e6
            best=rate if best is None else max(best,rate)
        return best
    c,d=one(CAND),one(DEV5)
    return {"candidate_nps":c,"dev5_nps":d,"ratio":c/d if d else None}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--all",action="store_true",
      help="run Stage 1 only if Stage 0 validity gate passes"); a=ap.parse_args()
    master,S=suites(); nps=nps_ratio()
    print("NPS",json.dumps(nps),flush=True)
    stage0,recs0=run("stage0",CAND,CAND,BASE_OPTS+["BadCapturePruning=false"],
                     BASE_OPTS+["BadCapturePruning=false"],S["stage0"],400,2026112000)
    if "error" in stage0: print("STAGE0 ERROR",stage0["error"],flush=True); return
    gate=(stage0["time_forfeit"]==0 and stage0["illegal"]==0 and stage0["uci_fail"]==0
          and stage0["ci95"] is not None and stage0["ci95"][0]<=0<=stage0["ci95"][1]
          and nps["ratio"] is not None and 0.97<=nps["ratio"]<=1.03)
    stage0["validity_gate"]="PASS" if gate else "FAIL"
    print("STAGE0",f"+{stage0['wins']}={stage0['draws']}-{stage0['losses']}",
          f"Elo {stage0['elo']} {stage0['ci95']}","forfeits",stage0["time_forfeit"],
          "illegal",stage0["illegal"],"GATE",stage0["validity_gate"],flush=True)
    results=[stage0]; combined=None; gated=None
    if not gate:
        gated="INVALID MEASUREMENT (Stage 0 validity gate FAILED); Stage 1 NOT RUN"
        print(gated,flush=True)
    elif a.all:
        on=BASE_OPTS+["BadCapturePruning=true"]; off=BASE_OPTS+["BadCapturePruning=false"]
        specs=[("batchA",CAND,DEV5,on,BASE_OPTS,S["batchA"],1000,2026112100),
               ("batchB",CAND,DEV5,on,BASE_OPTS,S["batchB"],1000,2026112101),
               ("null",CAND,CAND,off,off,S["null"],400,2026112102),
               ("trackA",CAND,A1,on,BASE_OPTS,S["trackA"],400,2026112103)]
        batch_recs=[]
        for sp in specs:
            r,recs=run(*sp); results.append(r)
            if recs is not None and sp[0] in ("batchA","batchB"): batch_recs.append(recs)
            print(sp[0],"ERROR "+r["error"][:120] if "error" in r else
                  f"score {r['score']:.4f} +{r['wins']}={r['draws']}-{r['losses']} "
                  f"Elo {r['elo']} {r['ci95']} forfeits {r['time_forfeit']}",flush=True)
        if len(batch_recs)==2:
            g=[];pairs=[];po=[]
            for rs in batch_recs:
                g+=[x["score_a"] for x in rs if x["score_a"] is not None]
                for k in range(0,len(rs)-1,2):
                    x,y=rs[k],rs[k+1]
                    if x["score_a"] is not None and y["score_a"] is not None:
                        pairs.append(x["score_a"]+y["score_a"]);po.append(x["opening"])
            s=match_stats.summarise(g,pairs,match_stats.lmr_step(pairs,0.0,5.0),pair_openings=po)
            cl=s.get("opening_clustered",{})
            combined={"games":len(g),"wins":s["wins"],"draws":s["draws"],"losses":s["losses"],
              "score":(s["wins"]+0.5*s["draws"])/max(1,len(g)),
              "elo":cl.get("elo_difference"),"ci95":cl.get("elo_ci95"),"clusters":cl.get("clusters")}
            print("combined:",json.dumps(combined),flush=True)
    else:
        gated="Stage 0 PASSED; Stage 1 not requested in this invocation"
    OUT.write_text(json.dumps({
      "experiment":"exp-0036","prereg":"docs/DEV6_PREREG_EXP0036.md",
      "prereg_sha256":sha(ROOT/"docs/DEV6_PREREG_EXP0036.md"),
      "pushed_source_sha":"03868dafc6f644abb5b53caf2ef6ef1dda14e830",
      "ci_run_id":41770918367,
      "candidate_binary_sha256":sha(CAND),"official_dev5_sha256":sha(DEV5),
      "trackA_dev5_rebuilt_sha256":sha(A1),"master_suite_sha256":sha(master),
      "runner":"LOCAL dedicated core (taskset -c 1); NOT a GitHub-hosted isolated VM",
      "tier1_status":"BLOCKED by one-push authorization boundary (see prereg §1)",
      "control":"FIXED TIME 40+4 ms, hash 16, threads 1, max-plies 240; NEVER --nodes",
      "nps_integrity":nps,"stage0":stage0,"results":results,"combined":combined,
      "decision":gated},indent=2)+"\n")
    print("wrote",OUT,flush=True)
if __name__=="__main__": main()
