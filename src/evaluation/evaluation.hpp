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
