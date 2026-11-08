import chess, chess.pgn, json, random
from pathlib import Path
import numpy as np
src=Path('benchmarks/exp-runs/tier1-export/run-42434718590')
pgn=next(src.glob('*batchA*/match.pgn'))
rng=random.Random(2026110667)
bad=[]; mob=[]; sp=[]; totmob=[]; n=0
with open(pgn) as fh:
    while n<2500:
        g=chess.pgn.read_game(fh)
        if g is None: break
        b=g.board(); ply=0
        for m in g.mainline_moves():
            b.push(m); ply+=1
            if ply%7: continue
            if rng.random()>0.25: continue
            for c in (chess.WHITE,chess.BLACK):
                bs=list(b.pieces(chess.BISHOP,c))
                if len(bs)!=1: continue
                sq=bs[0]; dark=bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[sq])
                own=b.pieces(chess.PAWN,c)
                # bad bishop: own pawns on the bishop's square colour
                nb=sum(1 for s in own if bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[s])==dark)
                # existing MobilityBishop = attacks & ~own  (blocked by ALL pieces)
                mb=bin(int(b.attacks_mask(sq)) & ~int(b.occupied_co[c])).count("1")
                bad.append(nb); mob.append(mb)
            # space: safe centre squares behind own pawns (SF-like), vs total mobility
            for c in (chess.WHITE,chess.BLACK):
                own=b.pieces(chess.PAWN,c); them=~c
                enemy_pawn_att=0
                for s in b.pieces(chess.PAWN,them): enemy_pawn_att |= int(b.attacks_mask(s))
                safe = ~enemy_pawn_att & ~b.occupied_co[c]
                behind = sum(chess.BB_RANKS[1:4]) if c==chess.WHITE else sum(chess.BB_RANKS[4:7])
                centre = sum(chess.BB_FILES[2:6])
                region = safe & behind & centre
                sp.append(bin(int(region)).count("1"))
                tm=sum(bin(int(b.attacks_mask(s)) & ~int(b.occupied_co[c])).count("1")
                       for pt in (chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN)
                       for s in b.pieces(pt,c))
                totmob.append(tm)
            n+=1
            if n>=2500: break
bad,mob,sp,totmob=map(np.array,(bad,mob,sp,totmob))
print(json.dumps({"sampled_positions":n,"bishop_samples":len(bad),
 "bad_bishop_mean":round(float(bad.mean()),3),"bad_bishop_sd":round(float(bad.std()),3),
 "corr_bad_bishop_vs_existing_bishop_mobility":round(float(np.corrcoef(bad,mob)[0,1]),4),
 "space_mean":round(float(sp.mean()),3),"space_sd":round(float(sp.std()),3),
 "corr_space_vs_existing_total_mobility":round(float(np.corrcoef(sp,totmob)[0,1]),4)},indent=2))
