// ---------------------------------------------------------------------------
// position.hpp - board representation and position management.
//
// Representation:
//   * Bitboards: one per piece type (index 0 holds ALL pieces), one per color,
//     plus a mailbox array for O(1) square lookups.
//   * Square 0 = a1 ... 63 = h8.
//   * All volatile per-ply state (hash key, accumulators, clocks, ep square,
//     castling rights, captured piece, checkers, pins, repetition info) lives
//     in StateInfo. Position keeps the whole game history as a vector of
//     StateInfo; make_move() pushes, unmake_move() pops. Because nothing holds
//     pointers into that vector, a Position is copyable and safe to
//     hand between threads by value.
// ---------------------------------------------------------------------------
#pragma once

#include "chess/bitboard.hpp"
#include "chess/move.hpp"
#include "chess/zobrist.hpp"
#include "utilities/types.hpp"

#include <cstdint>
#include <string>
#include <stdexcept>
#include <vector>

namespace stockbear {

struct StateInfo {
    Key key;                     // Zobrist hash of the position
    Key historyContext;          // signature of known reversible history
    std::int32_t accMg[ColorNB]; // material + piece-square accumulator (middlegame), cp
    std::int32_t accEg[ColorNB]; // material + piece-square accumulator (endgame), cp
    Bitboard checkers;           // enemy pieces checking the side to move
    Bitboard pinned;             // side-to-move pieces pinned against their king
    std::uint64_t rule50;        // halfmove clock (plies since last pawn move/capture)
    std::size_t pliesFromStart;  // number of moves since the history was initialized
    std::size_t repetition;      // plies back to the most recent earlier occurrence
                                 // of `key` (0 = no earlier occurrence)
    std::uint8_t castlingRights; // combination of CastlingRight
    std::uint8_t epSquare;       // en-passant target square, SQ_NONE if none
    std::uint8_t capturedPiece;  // piece captured by the move leading here
    std::uint8_t padding_;
};

class Position;

enum class GenType {
    All,      // every legal move
    QSearch   // captures, en passant and all promotion choices
};

struct ExtMove {
    Move move = MOVE_NONE;
    int  score = 0;
};

class MoveList {
public:
    static constexpr int Capacity = 256; // legal chess moves never exceed 218

    void add(Move m, int score = 0) {
        if (count_ >= Capacity) throw std::overflow_error("legal move list capacity exceeded");
        list_[count_++] = ExtMove{ m, score };
    }
    int  size()  const { return count_; }
    bool empty() const { return count_ == 0; }
    void clear() { count_ = 0; }

    const ExtMove* begin() const { return list_; }
    const ExtMove* end()   const { return list_ + count_; }
    ExtMove&       operator[](int i)       { return list_[i]; }
    const ExtMove& operator[](int i) const { return list_[i]; }

    bool contains(Move m) const {
        for (int i = 0; i < count_; ++i) if (list_[i].move == m) return true;
        return false;
    }

private:
    ExtMove list_[Capacity];
    int count_ = 0;
};

// Generates all legal moves of the requested type.
void generate_moves(const Position& pos, MoveList& ml, GenType type = GenType::All);

enum class DrawStatus {
    None, ClaimableThreefold, ClaimableFiftyMove,
    AutomaticFivefold, AutomaticSeventyFiveMove,
    AutomaticInsufficientMaterial, AutomaticStalemate
};

class Position {
public:
    Position() = default;

    // Sets the position from a FEN string. Returns false on malformed input
    // (with *error filled when provided); the position is left unchanged.
    bool set(const std::string& fen, std::string* error = nullptr);

    // Serializes the full position state back to FEN.
    std::string fen() const;

    // --- Piece accessors -----------------------------------------------------
    Bitboard pieces() const { return byTypeBB[NoPieceType]; }
    Bitboard pieces(Color c) const { return byColorBB[c]; }
    Bitboard pieces(PieceType pt) const { return byTypeBB[pt]; }
    Bitboard pieces(PieceType pt1, PieceType pt2) const { return byTypeBB[pt1] | byTypeBB[pt2]; }
    Bitboard pieces(Color c, PieceType pt) const { return byColorBB[c] & byTypeBB[pt]; }
    Bitboard pieces(Color c, PieceType pt1, PieceType pt2) const {
        return byColorBB[c] & (byTypeBB[pt1] | byTypeBB[pt2]);
    }
    Piece   piece_on(Square s) const { return board_[s]; }
    bool    empty(Square s) const { return board_[s] == NoPiece; }
    Square  king_square(Color c) const { return kingSquare_[c]; }
    Color   side_to_move() const { return sideToMove_; }
    std::uint64_t fullmove_number() const { return fullmoveNumber_; }
    int     count(Color c, PieceType pt) const { return popcount(pieces(c, pt)); }

    // --- State accessors ------------------------------------------------------
    Key      key() const { return st().key; }
    Key      history_context() const { return st().historyContext; }
    std::uint64_t rule50() const { return st().rule50; }
    std::uint8_t castling_rights() const { return st().castlingRights; }
    Square   ep_square() const { return Square(st().epSquare); }
    Bitboard checkers() const { return st().checkers; }
    Bitboard pinned() const { return st().pinned; }
    bool     in_check() const { return st().checkers != 0; }
    bool     can_castle(CastlingRight cr) const { return bool(st().castlingRights & cr); }
    bool     can_castle(Color c) const {
        return bool(st().castlingRights & (c == White ? WhiteCastling : BlackCastling));
    }

    // Material + piece-square accumulators (cp), used by the evaluation.
    int acc_mg(Color c) const { return st().accMg[c]; }
    int acc_eg(Color c) const { return st().accEg[c]; }

    // --- Attacks --------------------------------------------------------------
    Bitboard attackers_to(Square s) const { return attackers_to(s, pieces()); }
    Bitboard attackers_to(Square s, Bitboard occ) const;
    bool attacked_by(Color c, Square s) const { return bool(attackers_to(s, pieces()) & pieces(c)); }
    // Attack test with a hypothetical occupancy (pieces stay as on the board).
    bool attacked_by(Color c, Square s, Bitboard occ) const {
        return bool(attackers_to(s, occ) & pieces(c));
    }

    // --- Make / unmake ---------------------------------------------------------
    // Precondition: m was generated as a legal move for this position. The
    // public entry point additionally rejects attempts to capture either king.
    void make_move(Move m);
    void unmake_move(Move m);

    // --- Draw / terminal detection ----------------------------------------------
    // Recognizes provably dead material configurations (bare kings, one minor,
    // or bishops only with all bishops on the same square color).
    bool insufficient_material() const;

    // Actual current-position draw status, distinguishing claims from automatic
    // draws. Checkmate takes precedence over the 75-move rule.
    DrawStatus draw_status() const;

    // FIDE claims may also be made by declaring an intended legal move which
    // produces the third occurrence or the 100th reversible halfmove.
    bool can_claim_threefold() const;
    bool can_claim_fifty_moves() const;

    // Pawns that can legally capture the current en-passant target. Used for
    // both move generation and repetition-equivalent Zobrist hashing.
    Bitboard legal_en_passant_capturers() const;

    // Generates legal moves to answer this (relatively expensive).
    bool has_legal_moves() const;

    // Draw detection for use inside search. `plyFromRoot` is the distance in
    // plies from the search root (0 at the root position). Handles:
    //   * fifty-move rule (claimable) and seventy-five-move rule (automatic),
    //   * insufficient material (automatic),
    //   * repetitions: occurrences inside the search subtree or equal to the
    //     root position count as draws; occurrences entirely before the root
    //     require a full threefold repetition (fivefold is covered by it).
    // Checkmate always takes precedence: a mated position is never a draw.
    bool is_search_draw(int plyFromRoot) const;

    // How many times the current position (same key) appears in the stored
    // history, including the current state.
    int repetition_count() const;

    // --- Testing helpers ---------------------------------------------------------
    // Recomputes derived state (hash key, accumulators, checkers, pins,
    // bitboard/mailbox consistency) from scratch and compares. Used by the
    // stress tests after every move.
    bool verify_state(std::string* error) const;

    // Classical performance test: number of leaf nodes of the legal move tree.
    std::uint64_t perft(int depth);

    // Number of stored plies of history (states), including the current one.
    size_t history_size() const { return history_.size(); }

private:
    friend bool parse_fen(const std::string& fen, Position& pos, std::string* error);
    friend void generate_moves(const Position& pos, MoveList& ml, GenType type);

    StateInfo&       st()       { return history_.back(); }
    const StateInfo& st() const { return history_.back(); }

    void put_piece(Piece pc, Square s);
    void remove_piece(Square s);
    void move_piece(Square from, Square to);
    void set_check_info();
    Bitboard compute_checkers() const;
    Bitboard compute_pinned() const;

    Bitboard byTypeBB[PieceTypeNB] = {};  // index 0 (NoPieceType) = all pieces
    Bitboard byColorBB[ColorNB] = {};
    Piece board_[SQ_NB] = {};
    Square kingSquare_[ColorNB] = { SQ_NONE, SQ_NONE };
    Color sideToMove_ = White;
    std::uint64_t fullmoveNumber_ = 1;
    std::vector<StateInfo> history_;
};

// Resolves a UCI move string (e.g. "e2e4", "e7e8q") against the position's
// legal moves. Returns MOVE_NONE when the string is malformed or illegal.
Move move_from_uci(const Position& pos, const std::string& s);

} // namespace stockbear
