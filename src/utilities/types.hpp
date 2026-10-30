// ---------------------------------------------------------------------------
// types.hpp - fundamental types, enums and constants shared by all modules.
// ---------------------------------------------------------------------------
#pragma once

#include <cstdint>
#include <string>

#ifndef STOCKBEAR_VERSION
#define STOCKBEAR_VERSION "0.0.0-custom-build"
#endif

namespace stockbear {

using Bitboard = std::uint64_t;
using Key      = std::uint64_t;

// Engine identity -----------------------------------------------------------
inline constexpr const char* kEngineName    = "StockBear";
inline constexpr const char* kEngineVersion = STOCKBEAR_VERSION;
inline constexpr const char* kEngineAuthors = "The StockBear developers";

// Colors ---------------------------------------------------------------------
enum Color : int { White = 0, Black = 1, ColorNB = 2 };

inline constexpr Color operator~(Color c) { return Color(c ^ int(Black)); }

// Pieces ---------------------------------------------------------------------
enum PieceType : int {
    NoPieceType = 0,
    Pawn   = 1,
    Knight = 2,
    Bishop = 3,
    Rook   = 4,
    Queen  = 5,
    King   = 6,
    PieceTypeNB = 7
};

// Piece encoding: bit 3 = color, bits 0-2 = type.
// White pieces are 1..6, black pieces are 9..14, NoPiece is 0.
enum Piece : int {
    NoPiece = 0,
    WhitePawn = 1, WhiteKnight = 2, WhiteBishop = 3, WhiteRook = 4, WhiteQueen = 5, WhiteKing = 6,
    BlackPawn = 9, BlackKnight = 10, BlackBishop = 11, BlackRook = 12, BlackQueen = 13, BlackKing = 14,
    PieceNB = 16
};

inline Piece     make_piece(Color c, PieceType pt) { return Piece((int(c) << 3) | int(pt)); }
inline PieceType type_of(Piece p)  { return PieceType(int(p) & 7); }
inline Color     color_of(Piece p) { return Color(int(p) >> 3); }
inline bool      is_ok(Piece p)    { return p != NoPiece; }

// Squares --------------------------------------------------------------------
// Square 0 = a1, 1 = b1, ..., 63 = h8. file = sq & 7, rank = sq >> 3.
enum Square : int {
    SQ_A1, SQ_B1, SQ_C1, SQ_D1, SQ_E1, SQ_F1, SQ_G1, SQ_H1,
    SQ_A2, SQ_B2, SQ_C2, SQ_D2, SQ_E2, SQ_F2, SQ_G2, SQ_H2,
    SQ_A3, SQ_B3, SQ_C3, SQ_D3, SQ_E3, SQ_F3, SQ_G3, SQ_H3,
    SQ_A4, SQ_B4, SQ_C4, SQ_D4, SQ_E4, SQ_F4, SQ_G4, SQ_H4,
    SQ_A5, SQ_B5, SQ_C5, SQ_D5, SQ_E5, SQ_F5, SQ_G5, SQ_H5,
    SQ_A6, SQ_B6, SQ_C6, SQ_D6, SQ_E6, SQ_F6, SQ_G6, SQ_H6,
    SQ_A7, SQ_B7, SQ_C7, SQ_D7, SQ_E7, SQ_F7, SQ_G7, SQ_H7,
    SQ_A8, SQ_B8, SQ_C8, SQ_D8, SQ_E8, SQ_F8, SQ_G8, SQ_H8,
    SQ_NB = 64,
    SQ_NONE = 64
};

enum File : int { FileA = 0, FileB, FileC, FileD, FileE, FileF, FileG, FileH, FileNB = 8 };
enum Rank : int { Rank1 = 0, Rank2, Rank3, Rank4, Rank5, Rank6, Rank7, Rank8, RankNB = 8 };

inline constexpr int file_of(Square s) { return int(s) & 7; }
inline constexpr int rank_of(Square s) { return int(s) >> 3; }
inline constexpr Square make_square(int f, int r) { return Square(r * 8 + f); }
inline constexpr bool is_ok(Square s) { return s >= SQ_A1 && s <= SQ_H8; }

// Flip a square vertically (a1 <-> a8). Used to mirror piece-square tables
// (tables are stored from White's point of view, rank 8 first).
inline constexpr Square flip_square(Square s) { return Square(int(s) ^ 56); }

// Index into a piece-square table stored rank-8-first from White's viewpoint:
// White pieces use the vertically flipped square, Black pieces the raw square.
inline constexpr int pst_index(Color c, Square s) {
    return int(c == White ? flip_square(s) : s);
}

// Castling --------------------------------------------------------------------
enum CastlingRight : std::uint8_t {
    NoCastling   = 0,
    WhiteOO      = 1,
    WhiteOOO     = 2,
    BlackOO      = 4,
    BlackOOO     = 8,
    WhiteCastling = WhiteOO | WhiteOOO,
    BlackCastling = BlackOO | BlackOOO,
    AnyCastling  = WhiteCastling | BlackCastling
};

// Score constants (centipawns). Mate scores are encoded relative to the search
// ply so that faster mates are preferred: mate in `ply` plies from the current
// node scores VALUE_MATE - ply.
inline constexpr int MAX_PLY = 246;  // hard search horizon (incl. extensions)

inline constexpr int VALUE_ZERO     = 0;
inline constexpr int VALUE_DRAW     = 0;
inline constexpr int VALUE_KNOWN_WIN = 10000;   // "clearly winning" heuristic bound
inline constexpr int VALUE_MATE     = 30000;
inline constexpr int VALUE_MATE_IN_MAX_PLY = VALUE_MATE - MAX_PLY;
inline constexpr int VALUE_INFINITE = 32001;
inline constexpr int VALUE_NONE     = 32002;

// Any |value| at or above MATE_BOUND encodes a proven mate rather than a
// heuristic evaluation. Heuristic eval is clamped well below this bound.
inline constexpr int MATE_BOUND = VALUE_MATE_IN_MAX_PLY;

inline constexpr bool is_mate_value(int v) { return v >= MATE_BOUND || v <= -MATE_BOUND; }

// Convert a mate value found at search ply `ply` to "mate in N moves" for UCI
// output (positive N = side to move mates, negative N = side to move is mated).
inline int mate_value_to_moves(int value) {
    if (value >= MATE_BOUND)  return  (VALUE_MATE - value + 1) / 2;
    if (value <= -MATE_BOUND) return -(VALUE_MATE + value) / 2;
    return 0;
}

} // namespace stockbear
