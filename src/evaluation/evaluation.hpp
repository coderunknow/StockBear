// Independent, handcrafted tapered evaluation. Values are centipawns.
#pragma once
#include "evaluation/eval_params.hpp"
#include "utilities/types.hpp"

namespace stockbear {
class Position;

// Material values and piece-square tables derived from the active parameter
// set. They are rebuilt by `apply_eval_params`, so they must not be cached
// across a parameter change.
extern int PieceValueMg[PieceTypeNB];
extern int PieceValueEg[PieceTypeNB];
extern int PieceSquareMg[PieceTypeNB][SQ_NB];
extern int PieceSquareEg[PieceTypeNB][SQ_NB];

// Install the shipped defaults. Called once at startup, before any Position
// exists, because Position accumulators are initialized from these tables.
void init_evaluation();

// --- DEV6 exp-0048: full per-square piece-square tables (default OFF) --------
// A research evaluator variant. When a PST file is loaded, the formulaic
// piece-square tables (rank/file/centre coefficients) are replaced by explicit
// per-square middlegame/endgame values for every piece type. The material and
// all non-PST features are unchanged, so the variant differs from the champion
// ONLY in its piece-placement term. With no file loaded the tables are exactly
// the shipped formulaic ones and the engine is bit-identical (bench
// 243f9a1c1ba5b36f). The file is original StockBear data fitted to StockBear
// self-play; no external engine's tables are embedded.
//
// Format (text): first line `SBPST1`, then for each piece in the order
// Pawn, Knight, Bishop, Rook, Queen, King, 64 lines of `mg eg` integers in
// table-index order (index 0 = a8, index 63 = h1, White's viewpoint). Values
// are centipawns added to the material accumulator and tapered by phase.
// Loading rebuilds the derived tables; it must happen before Positions are
// constructed (UCI setoption precedes `position`). Returns false + error on a
// malformed or out-of-range file, leaving the previous state untouched.
bool load_pst_file(const std::string& path, std::string* error = nullptr);
void clear_pst_file();
bool pst_file_active();

// Relative to the side to move; never returns a mate score.
int evaluate(const Position& position);

// Research variant (SB_QEVAL_LITE): same tapered pipeline, but the expensive
// mobility and king-danger terms are skipped. Intended for qsearch stand-pat,
// where node count dominates. The full evaluate() is unchanged.
int evaluate_lite(const Position& position);

// Raw per-parameter feature counts for one side (EvalParamNB entries; the
// Mat*/Pst* slots stay zero — material and piece-square terms live in the
// Position accumulators). These mirror features() term for term, so
// sum(count[id] * param[id]) == features().mg/.eg exactly. Used by the
// incremental evaluator: Position keeps the counts in its StateInfo and
// evaluate() reads them instead of recomputing features().
void all_feature_counts(const Position& p, Color us, std::int16_t* out);
void cheap_feature_counts(const Position& p, Color us, std::int16_t* out);
// Single-piece counts with explicit occupancy/ownership, for delta updates.
int mobility_count_at(const Position& p, Color us, PieceType pt, Square sq,
                      Bitboard occ, Bitboard own);
int king_danger_count_at(const Position& p, Color them, PieceType pt, Square sq,
                         Bitboard occ, Bitboard zone);
EvalParamId mobility_param_id(PieceType pt);
EvalParamId king_danger_param_id(PieceType pt);
}
