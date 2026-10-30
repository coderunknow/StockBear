// ---------------------------------------------------------------------------
// move.hpp - move encoding.
//
// A move is a 16-bit value:
//   bits  0- 5 : origin square
//   bits  6-11 : destination square
//   bits 12-13 : promotion piece (type - Knight), promotion moves only
//   bits 14-15 : move type (Normal, Promotion, Castling, EnPassant)
//
// Castling is encoded king-start to king-destination (e1g1 / e1c1 / e8g8 /
// e8c8), which is exactly the UCI wire format; make_move() derives the rook
// squares from the destination.
// ---------------------------------------------------------------------------
#pragma once

#include "utilities/types.hpp"

#include <string>

namespace stockbear {

using Move = std::uint16_t;

inline constexpr Move MOVE_NONE = 0;

enum MoveType : int {
    NormalMove = 0,
    PromotionMove = 1,
    CastlingMove = 2,
    EnPassantMove = 3
};

inline constexpr Move MOVE_TYPE_BITS = 14;

inline Square move_from(Move m) { return Square(int(m) & 0x3F); }
inline Square move_to(Move m)   { return Square((int(m) >> 6) & 0x3F); }
inline MoveType move_type(Move m) { return MoveType((int(m) >> MOVE_TYPE_BITS) & 3); }

// Promotion piece encoded as (PieceType - Knight): 0=N, 1=B, 2=R, 3=Q.
inline PieceType promotion_type(Move m) { return PieceType(Knight + ((int(m) >> 12) & 3)); }

inline Move make_move(Square from, Square to) {
    return Move(int(from) | (int(to) << 6));
}

inline Move make_promotion(Square from, Square to, PieceType pt) {
    return Move(int(from) | (int(to) << 6) | ((int(pt) - int(Knight)) << 12)
                | (PromotionMove << MOVE_TYPE_BITS));
}

inline Move make_castling(Square kingFrom, Square kingTo) {
    return Move(int(kingFrom) | (int(kingTo) << 6) | (CastlingMove << MOVE_TYPE_BITS));
}

inline Move make_en_passant(Square from, Square to) {
    return Move(int(from) | (int(to) << 6) | (EnPassantMove << MOVE_TYPE_BITS));
}

inline bool is_ok(Move m) { return m != MOVE_NONE; }

// UCI long-algebraic form, e.g. "e2e4", "e7e8q", "e1g1".
std::string move_to_uci(Move m);

// Parse the coordinate part of a UCI move string. Promotion/castling/en-passant
// typing is resolved by matching the result against the position's legal moves,
// so this function only needs from/to/promotion-piece. Returns MOVE_NONE for
// malformed input.
Move move_from_uci(const std::string& s);

} // namespace stockbear
