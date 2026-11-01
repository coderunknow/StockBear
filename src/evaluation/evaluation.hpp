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
}
