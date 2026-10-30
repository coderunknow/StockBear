// name, FEN, depth, independently verified nodes (python-chess 1.11.2).
// These are compiled into the binary so benchmarking needs no checkout/files.
PERFT("Start position", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 4, 197281ULL)
PERFT("Kiwipete: castling and pins", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 4, 4085603ULL)
PERFT("Rook/pawn endgame: checks and ep", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 5, 674624ULL)
PERFT("Promotions and castling", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 4, 422333ULL)
PERFT("Promotions and check evasions", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 4, 2103487ULL)
PERFT("En passant pinned", "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", 4, 8130ULL)
PERFT("En passant captures checker", "7k/8/8/3pP3/4K3/8/8/8 w - d6 0 2", 4, 1234ULL)
PERFT("Promotion choices", "n1n1n1nk/1P1P1P1P/8/8/8/8/p1p1p1p1/K1N1N1N1 w - - 0 1", 4, 432422ULL)
PERFT("Middlegame activity", "r4rk1/1pp1qppp/p1np1n2/8/2B1P1b1/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 10", 4, 2238608ULL)
