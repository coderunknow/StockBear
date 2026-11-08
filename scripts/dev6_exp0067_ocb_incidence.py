import chess, chess.pgn, json, collections
from pathlib import Path
src=Path('benchmarks/exp-runs/tier1-export/run-42434718590')
pgn=next(src.glob('*batchA*/match.pgn'))
games=0; ocb_games=0; pure_pos=0; tot_pos=0
pawndiff=collections.Counter(); flank=collections.Counter(); first_ply=[]
with open(pgn) as fh:
    while True:
        g=chess.pgn.read_game(fh)
        if g is None: break
        games+=1
        b=g.board(); seen=False; fp=None
        for i,m in enumerate(g.mainline_moves()):
            b.push(m); tot_pos+=1
            # pure OCB: exactly one bishop each, opposite colours, no N/R/Q either side
            if (len(b.pieces(chess.BISHOP,chess.WHITE))==1 and
                len(b.pieces(chess.BISHOP,chess.BLACK))==1 and
                not any(b.pieces(pt,c) for pt in (chess.KNIGHT,chess.ROOK,chess.QUEEN)
                        for c in (chess.WHITE,chess.BLACK))):
                wb=b.pieces(chess.BISHOP,chess.WHITE).pop(); bb=b.pieces(chess.BISHOP,chess.BLACK).pop()
                if bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[wb]) != bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[bb]):
                    pure_pos+=1
                    if not seen: seen=True; fp=i+1
                    wp=b.pieces(chess.PAWN,chess.WHITE); bp=b.pieces(chess.PAWN,chess.BLACK)
                    d=abs(len(wp)-len(bp)); pawndiff[min(d,4)]+=1
                    allp=wp|bp
                    files={chess.square_file(s) for s in allp}
                    one_flank = (max(files)<=3 or min(files)>=4) if files else True
                    flank[(min(d,2),one_flank)]+=1
        if seen: ocb_games+=1; first_ply.append(fp)
print(json.dumps({"games":games,"games_reaching_pure_OCB":ocb_games,
  "fraction_games":round(ocb_games/games,4),"positions":tot_pos,"pure_OCB_positions":pure_pos,
  "fraction_positions":round(pure_pos/tot_pos,4),
  "pawn_abs_diff_hist":dict(sorted(pawndiff.items())),
  "diff<=1_and_one_flank":flank.get((1,True),0)+flank.get((0,True),0),
  "diff<=2_one_flank_total":sum(v for (d,o),v in flank.items() if o),
  "median_first_ply":sorted(first_ply)[len(first_ply)//2] if first_ply else None},indent=2))
