// Independent, handcrafted tapered evaluation. Values are centipawns.
#pragma once
#include "utilities/types.hpp"

namespace stockbear {
class Position;

extern const int PieceValueMg[PieceTypeNB];
extern const int PieceValueEg[PieceTypeNB];
extern int PieceSquareMg[PieceTypeNB][SQ_NB];
extern int PieceSquareEg[PieceTypeNB][SQ_NB];

// Initialize the original, formula-derived piece-square tables once.
void init_evaluation();

// Relative to the side to move; never returns a mate score.
int evaluate(const Position& position);
}
