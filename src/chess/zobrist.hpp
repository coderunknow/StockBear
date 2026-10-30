// ---------------------------------------------------------------------------
// zobrist.hpp - Zobrist hashing keys.
//
// Keys are generated once from a fixed-seed splitmix64 stream so every run of
// the engine (and every machine) uses identical hash keys; search results stay
// reproducible.
// ---------------------------------------------------------------------------
#pragma once

#include "utilities/types.hpp"

namespace stockbear {

namespace Zobrist {

extern Key psq[PieceNB][SQ_NB];   // piece on square
extern Key side;                  // XOR when Black is to move
extern Key castling[16];          // one key per castling-rights combination
extern Key epFile[FileNB];        // one key per en-passant file

void init();
// A deterministic rolling signature of the known reversible history. Used in
// transposition keys because repetition outcomes depend on the path, not just
// the board. This trades some transpositions for draw-score correctness.
Key context_seed(Key key);
Key context_next(Key previous, Key key);

} // namespace Zobrist

} // namespace stockbear
