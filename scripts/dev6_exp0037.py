#!/usr/bin/env python3
"""exp-0037 Stage 1: frozen fixed-node screen of ProbCut (same-binary ablation).
See docs/DEV6_PREREG_EXP0037.md + docs/DEV6_PREREG_EXP0037_ADDENDUM.md.
FIXED NODE only; never presented as fixed-time strength evidence."""
import json, hashlib, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
import match_stats
PY=ROOT/'.venv/bin/python'; BIN=ROOT/'build-exp0037/stockbear'
POS=ROOT/'benchmarks/positions'; EXP=ROOT/'benchmarks/exp-runs'
OUT=ROOT/'benchmarks/dev6-baseline/exp0037_results.json'
CHAMP=['EvalParams=research-data/params_abc.txt','TTEval=true']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def summarise(recs):
    recs.sort(key=lambda x:x['game']); pairs=[];po=[];terms={}
    for k in range(0,len(recs)-1,2):
        x,y=recs[k],recs[k+1]
        if x['score_a'] is not None and y['score_a'] is not None:
            pairs.append(x['score_a']+y['score_a']); po.append(x['opening'])
    for x in recs: t=x.get('termination','?'); terms[t]=terms.get(t,0)+1
    g=[x['score_a'] for x in recs if x['score_a'] is not None]
    s=match_stats.summarise(g,pairs,match_stats.lmr_step(pairs,0.0,5.0),pair_openings=po)
    cl=s.get('opening_clustered',{})
    score=(s['wins']+0.5*s['draws'])/max(1,len(g))
    return {'games':len(g),'unadjudicated':len(recs)-len(g),'wins':s['wins'],
      'draws':s['draws'],'losses':s['losses'],'score':score,'elo':cl.get('elo_difference'),
      'ci95':cl.get('elo_ci95'),'clusters':cl.get('clusters'),'terminations':terms,
      'time_forfeit':sum(v for k,v in terms.items() if 'FORFEIT' in k.upper()),
      'illegal':sum(v for k,v in terms.items() if 'ILLEGAL' in k.upper()),
      'engine_failure':sum(v for k,v in terms.items() if 'FAILURE' in k.upper()),
      'independent_elo_from_score':match_stats.score_to_elo(score)}

def run(tag, games, seed, slice_name, null):
    d=EXP/f'exp0037-{tag}'; d.mkdir(parents=True,exist_ok=True)
    op=POS/f'openings_exp0037_{slice_name}.txt'
    a=CHAMP+([] if null else ['ProbCut=true'])
    b=list(a) if null else CHAMP
    cmd=[str(PY),str(ROOT/'scripts/tournament.py'),'--engine-a',str(BIN),'--engine-b',str(BIN),
         '--games',games,'--nodes','6000','--nodes-jitter','0.15','--hash','16',
         '--threads','1','--max-plies','240','--openings',str(op),'--seed',seed]
    for o in a: cmd+=['--a-option',o]
    for o in b: cmd+=['--b-option',o]
    cmd+=['--pgn',str(d/'match.pgn'),'--jsonl',str(d/'match.jsonl'),'--csv',str(d/'match.csv')]
    r=subprocess.run([str(c) for c in cmd],cwd=ROOT,capture_output=True,text=True)
    if r.returncode: raise RuntimeError(f'{tag}: {r.stderr[-800:]}')
    recs=[json.loads(l) for l in (d/'match.jsonl').read_text().splitlines() if '"game"' in l]
    s=summarise(recs); s.update({'tag':tag,'null':null,'seed':seed,'games_requested':games,
      'control':'FIXED NODE go nodes 6000 --nodes-jitter 0.15 (NOT fixed-time)',
      'openings':str(op.relative_to(ROOT)),'openings_sha256':sha(op),
      'a_options':a,'b_options':b,'binary_sha256':sha(BIN),'command':' '.join(map(str,cmd))})
    return s,recs

def main():
    arms=[('stage1A',600,2026112100,'stage1A',False),
          ('stage1B',600,2026112101,'stage1B',False),
          ('null',400,2026112102,'null',True)]
    results=[]; batch=[]
    for tag,g,seed,sl,nu in arms:
        s,recs=run(tag,g,seed,sl,nu); results.append(s)
        if not nu: batch.append(recs)
        print(tag,f"+{s['wins']}={s['draws']}-{s['losses']}",f'Elo {s["elo"]} {s["ci95"]}',
              'forfeits',s['time_forfeit'],flush=True)
    g=[];pairs=[];po=[]
    for rs in batch:
        g+=[x['score_a'] for x in rs if x['score_a'] is not None]
        for k in range(0,len(rs)-1,2):
            x,y=rs[k],rs[k+1]
            if x['score_a'] is not None and y['score_a'] is not None:
                pairs.append(x['score_a']+y['score_a']); po.append(x['opening'])
    s=match_stats.summarise(g,pairs,match_stats.lmr_step(pairs,0.0,5.0),pair_openings=po)
    cl=s.get('opening_clustered',{})
    comb={'games':len(g),'wins':s['wins'],'draws':s['draws'],'losses':s['losses'],
          'score':(s['wins']+0.5*s['draws'])/max(1,len(g)),'elo':cl.get('elo_difference'),
          'ci95':cl.get('elo_ci95'),'clusters':cl.get('clusters')}
    r={x['tag']:x for x in results}; nullok=r['null']['ci95'] and r['null']['ci95'][0]<=0<=r['null']['ci95'][1]
    batchok=r['stage1A']['elo']>=-5 and r['stage1B']['elo']>=-5
    clean=all(x['time_forfeit']==0 and x['illegal']==0 and x['engine_failure']==0 for x in results)
    advance=(comb['elo'] is not None and comb['elo']>=10 and comb['ci95'][0]>-10
             and batchok and nullok and clean)
    decision='ADVANCE to Tier-1 Stage 2a' if advance else 'CLOSED at frozen Stage-1 rule (no advance)'
    print('combined',json.dumps(comb),flush=True); print('DECISION',decision,flush=True)
    OUT.write_text(json.dumps({'experiment':'exp-0037','stage':'Stage 1 fixed-node screen',
      'prereg':['docs/DEV6_PREREG_EXP0037.md','docs/DEV6_PREREG_EXP0037_ADDENDUM.md'],
      'prereg_sha256':{p:sha(ROOT/p) for p in ['docs/DEV6_PREREG_EXP0037.md','docs/DEV6_PREREG_EXP0037_ADDENDUM.md']},
      'binary_sha256':sha(BIN),'runner':'LOCAL Tier-2 (fixed-node screen; NOT gate evidence)',
      'control':'FIXED NODE 6000 +-15% jitter; NEVER fixed-time evidence',
      'frozen_advance_rule':'combined point >= +10 AND LCB > -10 AND both batches >= -5 AND null includes 0 AND clean correctness',
      'results':results,'combined':comb,'gate3_null_includes_zero':nullok,
      'advance':advance,'decision':decision},indent=2)+'\n')
    print('wrote',OUT,flush=True)
if __name__=='__main__': main()
