// ---------------------------------------------------------------------------
// position.cpp - board management, make/unmake, legal move generation, perft.
//
// Legal move generation strategy (no make/unmake per candidate move):
//   * StateInfo carries precomputed `checkers` and `pinned` for the side to
//     move, refreshed on every make_move().
//   * Double check  -> only king moves are generated.
//   * Single check  -> non-king moves must capture the checker or interpose
//                      on BetweenBB[king][checker].
//   * Pinned pieces -> may only move along LineBB[ownKing][piece] (which
//                      covers blocking and capturing the pinner; pinned
//                      knights are skipped entirely).
//   * King moves    -> destination must not be attacked with the king removed
//                      from the occupancy (handles x-rays through the vacated
//                      square). The enemy king is never a target, so a king
//                      can never be "captured" as an ordinary move.
//   * En passant    -> legality verified with the real post-capture occupancy
//                      (both pawns removed, capturing pawn on the ep square).
//   * Castling      -> only when not in check; path empty; king origin,
//                      transit and destination squares unattacked.
// ---------------------------------------------------------------------------
#include "chess/position.hpp"
#include "evaluation/evaluation.hpp"
#include "chess/fen.hpp"
#include "chess/dead_position.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <cstdlib>

namespace stockbear {

namespace {

// Castling rights that survive a move from/to each square: moving a king clears
// both of its rights, moving or capturing a rook on its home square clears that
// side's right.
const std::array<std::uint8_t, SQ_NB> CastlingRightsMask = [] {
    std::array<std::uint8_t, SQ_NB> masks{};
    masks.fill(AnyCastling);
    masks[SQ_E1] = std::uint8_t(AnyCastling & ~WhiteCastling);
    masks[SQ_E8] = std::uint8_t(AnyCastling & ~BlackCastling);
    masks[SQ_A1] = std::uint8_t(AnyCastling & ~WhiteOOO);
    masks[SQ_H1] = std::uint8_t(AnyCastling & ~WhiteOO);
    masks[SQ_A8] = std::uint8_t(AnyCastling & ~BlackOOO);
    masks[SQ_H8] = std::uint8_t(AnyCastling & ~BlackOO);
    return masks;
}();

inline void acc_add(StateInfo& s, Piece pc, Square sq) {
    const Color c = color_of(pc);
    const PieceType pt = type_of(pc);
    const int idx = pst_index(c, sq);
    s.accMg[c] += PieceValueMg[pt] + PieceSquareMg[pt][idx];
    s.accEg[c] += PieceValueEg[pt] + PieceSquareEg[pt][idx];
}

inline void acc_sub(StateInfo& s, Piece pc, Square sq) {
    const Color c = color_of(pc);
    const PieceType pt = type_of(pc);
    const int idx = pst_index(c, sq);
    s.accMg[c] -= PieceValueMg[pt] + PieceSquareMg[pt][idx];
    s.accEg[c] -= PieceValueEg[pt] + PieceSquareEg[pt][idx];
}

// ---------------------------------------------------------------------------
// Pawn move generation. `evasions` is the set of squares a non-king move may
// land on when in check (capture-the-checker or block); it is all-squares when
// not in check.
// ---------------------------------------------------------------------------
template <Color Us>
void generate_pawn_moves(const Position& pos, MoveList& ml, Bitboard evasions, bool qsearch) {
    constexpr Color Them = ~Us;
    constexpr int   Up = (Us == White ? 8 : -8);
    constexpr Bitboard PromoRank = (Us == White ? Rank8BB : Rank1BB);
    constexpr Bitboard StartRank = (Us == White ? Rank2BB : Rank7BB);
    constexpr int   EastDelta = (Us == White ? 9 : -7);  // from -> to (file +1)
    constexpr int   WestDelta = (Us == White ? 7 : -9);  // from -> to (file -1)

    const Square ksq = pos.king_square(Us);
    const Bitboard pinned = pos.pinned();
    const Bitboard checkers = pos.checkers();
    const Bitboard empty = ~pos.pieces();
    const Bitboard theirPieces = pos.pieces(Them) & ~pos.pieces(Them, King);
    const Bitboard pawns = pos.pieces(Us, Pawn);

    // --- quiet pushes --------------------------------------------------------
    if (!qsearch) {
        Bitboard push1 = shift_bb<Up>(pawns) & empty;
        if (checkers) push1 &= evasions;

        Bitboard push1promo = push1 & PromoRank;
        push1 &= ~PromoRank;

        while (push1) {
            Square to = pop_lsb(push1);
            Square from = Square(int(to) - Up);
            if ((pinned & square_bb(from)) && !(LineBB[ksq][from] & square_bb(to))) continue;
            ml.add(make_move(from, to));
        }
        while (push1promo) {
            Square to = pop_lsb(push1promo);
            Square from = Square(int(to) - Up);
            if ((pinned & square_bb(from)) && !(LineBB[ksq][from] & square_bb(to))) continue;
            ml.add(make_promotion(from, to, Queen));
            ml.add(make_promotion(from, to, Rook));
            ml.add(make_promotion(from, to, Bishop));
            ml.add(make_promotion(from, to, Knight));
        }

        Bitboard push2 = shift_bb<Up>(shift_bb<Up>(pawns & StartRank) & empty) & empty;
        if (checkers) push2 &= evasions;
        while (push2) {
            Square to = pop_lsb(push2);
            Square from = Square(int(to) - 2 * Up);
            if ((pinned & square_bb(from)) && !(LineBB[ksq][from] & square_bb(to))) continue;
            ml.add(make_move(from, to));
        }
    } else {
        // Include all quiet promotions: an underpromotion may avoid stalemate
        // or give a decisive check that a queen cannot.
        Bitboard push1promo = shift_bb<Up>(pawns) & empty & PromoRank;
        if (checkers) push1promo &= evasions;
        while (push1promo) {
            Square to = pop_lsb(push1promo);
            Square from = Square(int(to) - Up);
            if ((pinned & square_bb(from)) && !(LineBB[ksq][from] & square_bb(to))) continue;
            ml.add(make_promotion(from, to, Queen));
            ml.add(make_promotion(from, to, Rook));
            ml.add(make_promotion(from, to, Bishop));
            ml.add(make_promotion(from, to, Knight));
        }
    }

    // --- captures -------------------------------------------------------------
    Bitboard capEast, capWest;
    if constexpr (Us == White) {
        capEast = (pawns << 9) & ~FileABB;
        capWest = (pawns << 7) & ~FileHBB;
    } else {
        capEast = (pawns >> 7) & ~FileABB;
        capWest = (pawns >> 9) & ~FileHBB;
    }
    capEast &= theirPieces;
    capWest &= theirPieces;
    if (checkers) { capEast &= evasions; capWest &= evasions; }

    while (capEast) {
        Square to = pop_lsb(capEast);
        Square from = Square(int(to) - EastDelta);
        if ((pinned & square_bb(from)) && !(LineBB[ksq][from] & square_bb(to))) continue;
        if (PromoRank & square_bb(to)) {
            ml.add(make_promotion(from, to, Queen));
            ml.add(make_promotion(from, to, Rook));
            ml.add(make_promotion(from, to, Bishop));
            ml.add(make_promotion(from, to, Knight));
        } else {
            ml.add(make_move(from, to));
        }
    }
    while (capWest) {
        Square to = pop_lsb(capWest);
        Square from = Square(int(to) - WestDelta);
        if ((pinned & square_bb(from)) && !(LineBB[ksq][from] & square_bb(to))) continue;
        if (PromoRank & square_bb(to)) {
            ml.add(make_promotion(from, to, Queen));
            ml.add(make_promotion(from, to, Rook));
            ml.add(make_promotion(from, to, Bishop));
            ml.add(make_promotion(from, to, Knight));
        } else {
            ml.add(make_move(from, to));
        }
    }

    // En passant can evade a check either by taking the checking pawn or by
    // blocking a slider's ray. The complete post-move king-safety test handles
    // both, as well as pins and discovered attacks caused by removing two pawns.
    Bitboard fromBB = pos.legal_en_passant_capturers();
    while (fromBB) ml.add(make_en_passant(pop_lsb(fromBB), pos.ep_square()));
}

template <Color Us>
void generate_castling(const Position& pos, MoveList& ml) {
    const Color Them = ~Us;
    const Square ksq = pos.king_square(Us);
    const Bitboard occ = pos.pieces();
    const Bitboard occNoKing = occ ^ square_bb(ksq);
    const std::uint8_t rights = pos.castling_rights();

    const CastlingRight oo  = (Us == White ? WhiteOO  : BlackOO);
    const CastlingRight ooo = (Us == White ? WhiteOOO : BlackOOO);
    const Square rookSqOO  = (Us == White ? SQ_H1 : SQ_H8);
    const Square rookSqOOO = (Us == White ? SQ_A1 : SQ_A8);
    const Square destOO    = (Us == White ? SQ_G1 : SQ_G8);
    const Square destOOO   = (Us == White ? SQ_C1 : SQ_C8);

    // King side.
    if ((rights & oo) && pos.piece_on(rookSqOO) == make_piece(Us, Rook)) {
        if (!(occ & BetweenBB[ksq][rookSqOO])) {
            Bitboard path = BetweenBB[ksq][destOO] | square_bb(destOO);
            bool safe = true;
            while (path) {
                Square s = pop_lsb(path);
                if (pos.attacked_by(Them, s, occNoKing)) { safe = false; break; }
            }
            if (safe) ml.add(make_castling(ksq, destOO));
        }
    }
    // Queen side: b1/b8 need not be attack-free, only empty.
    if ((rights & ooo) && pos.piece_on(rookSqOOO) == make_piece(Us, Rook)) {
        if (!(occ & BetweenBB[ksq][rookSqOOO])) {
            Bitboard path = BetweenBB[ksq][destOOO] | square_bb(destOOO);
            bool safe = true;
            while (path) {
                Square s = pop_lsb(path);
                if (pos.attacked_by(Them, s, occNoKing)) { safe = false; break; }
            }
            if (safe) ml.add(make_castling(ksq, destOOO));
        }
    }
}

} // namespace

// ---------------------------------------------------------------------------
// Position: piece placement helpers
// ---------------------------------------------------------------------------
void Position::put_piece(Piece pc, Square s) {
    board_[s] = pc;
    const Bitboard bb = square_bb(s);
    byTypeBB[NoPieceType] |= bb;
    byTypeBB[type_of(pc)] |= bb;
    byColorBB[color_of(pc)] |= bb;
    if (type_of(pc) == King) kingSquare_[color_of(pc)] = s;
}

void Position::remove_piece(Square s) {
    const Piece pc = board_[s];
    const Bitboard bb = square_bb(s);
    byTypeBB[NoPieceType] &= ~bb;
    byTypeBB[type_of(pc)] &= ~bb;
    byColorBB[color_of(pc)] &= ~bb;
    board_[s] = NoPiece;
    // The king is never captured during legal play; kingSquare_ stays valid.
}

void Position::move_piece(Square from, Square to) {
    const Piece pc = board_[from];
    const Bitboard b = square_bb(from) | square_bb(to);
    byTypeBB[NoPieceType] ^= b;
    byTypeBB[type_of(pc)] ^= b;
    byColorBB[color_of(pc)] ^= b;
    board_[from] = NoPiece;
    board_[to] = pc;
    if (type_of(pc) == King) kingSquare_[color_of(pc)] = to;
}

// ---------------------------------------------------------------------------
// Check / pin information for the side to move
// ---------------------------------------------------------------------------
Bitboard Position::compute_checkers() const {
    const Color us = sideToMove_;
    const Color them = ~us;
    const Square ksq = kingSquare_[us];
    const Bitboard occ = pieces();
    // The enemy king is deliberately excluded as a "checker": kings can never
    // be adjacent in a legal position, and including it could produce
    // king-capture pseudo-evasions.
    return (PawnAttacksBB[us][ksq] & pieces(them, Pawn))
         | (KnightAttacksBB[ksq] & pieces(them, Knight))
         | (rook_attacks_bb(ksq, occ) & pieces(them, Rook, Queen))
         | (bishop_attacks_bb(ksq, occ) & pieces(them, Bishop, Queen));
}

Bitboard Position::compute_pinned() const {
    const Color us = sideToMove_;
    const Color them = ~us;
    const Square ksq = kingSquare_[us];
    const Bitboard occ = pieces();
    Bitboard pinned = 0;

    // Rook-direction pins (rooks and queens on the same rank/file).
    Bitboard rq = pieces(them, Rook, Queen);
    while (rq) {
        const Square sq = pop_lsb(rq);
        if (file_of(sq) != file_of(ksq) && rank_of(sq) != rank_of(ksq)) continue;
        const Bitboard b = BetweenBB[ksq][sq] & occ;
        if (b && !more_than_one(b) && (b & pieces(us))) pinned |= b;
    }
    // Bishop-direction pins (bishops and queens on the same diagonal).
    Bitboard bq = pieces(them, Bishop, Queen);
    while (bq) {
        const Square sq = pop_lsb(bq);
        const int df = std::abs(file_of(sq) - file_of(ksq));
        const int dr = std::abs(rank_of(sq) - rank_of(ksq));
        if (df != dr || df == 0) continue;
        const Bitboard b = BetweenBB[ksq][sq] & occ;
        if (b && !more_than_one(b) && (b & pieces(us))) pinned |= b;
    }
    return pinned;
}

void Position::set_check_info() {
    st().checkers = compute_checkers();
    st().pinned = compute_pinned();
}

Bitboard Position::attackers_to(Square s, Bitboard occ) const {
    return ((PawnAttacksBB[Black][s] & pieces(White, Pawn))
         | (PawnAttacksBB[White][s] & pieces(Black, Pawn))
         | (KnightAttacksBB[s] & pieces(Knight))
         | (KingAttacksBB[s] & pieces(King))
         | (rook_attacks_bb(s, occ) & pieces(Rook, Queen))
         | (bishop_attacks_bb(s, occ) & pieces(Bishop, Queen))) & occ;
}

Bitboard Position::legal_en_passant_capturers() const {
    const Square ep = ep_square();
    if (ep == SQ_NONE || !empty(ep)) return 0;
    const Color us = sideToMove_, them = ~us;
    if ((us == White && rank_of(ep) != Rank6) ||
        (us == Black && rank_of(ep) != Rank3)) return 0;
    const Square captured = Square(int(ep) ^ 8);
    if (piece_on(captured) != make_piece(them, Pawn)) return 0;
    Bitboard candidates = PawnAttacksBB[them][ep] & pieces(us, Pawn);
    Bitboard legal = 0;
    while (candidates) {
        const Square from = pop_lsb(candidates);
        const Bitboard after = (pieces() & ~square_bb(from) & ~square_bb(captured)) | square_bb(ep);
        if (!attacked_by(them, king_square(us), after)) legal |= square_bb(from);
    }
    return legal;
}

// ---------------------------------------------------------------------------
// Make / unmake
// ---------------------------------------------------------------------------
void Position::make_move(Move m) { make_move_impl(m, true); }

void Position::make_move_without_repetition(Move m) { make_move_impl(m, false); }

void Position::make_move_impl(Move m, bool trackRepetition) {
    if (history_.empty() || !is_ok(m)) throw std::invalid_argument("move requires an initialized position");
    const Square from = move_from(m), to = move_to(m);
    const Piece pc = board_[from];
    const MoveType mt = move_type(m);
    const Square capturedSquare = mt == EnPassantMove ? Square(int(to) ^ 8) : to;
    if (pc == NoPiece || color_of(pc) != sideToMove_ || type_of(board_[capturedSquare]) == King)
        throw std::invalid_argument("invalid move or attempt to capture a king");
    // The FEN ep square is retained even if uncapturable, but only a legally
    // available capture distinguishes positions for repetition and hashing.
    const bool oldEpHasLegalCapture = legal_en_passant_capturers() != 0;

    // Copy-then-push: never pass a reference to a vector element into push_back
    // (reallocation would invalidate it).
    StateInfo newState = st();
    history_.push_back(newState);
    StateInfo& newSt = history_.back();
    const StateInfo& oldSt = history_[history_.size() - 2];

    const Color us = sideToMove_;
    const Color them = ~us;

    newSt.capturedPiece = NoPiece;
    newSt.rule50 = oldSt.rule50 + 1;
    newSt.pliesFromStart = oldSt.pliesFromStart + 1;
    newSt.repetition = 0;

    // 1) Clear the old en-passant square from the key.
    if (oldEpHasLegalCapture)
        newSt.key ^= Zobrist::epFile[file_of(Square(oldSt.epSquare))];
    newSt.epSquare = SQ_NONE;

    // 2) Castling rights (king moves, rook moves, rook captures).
    if (oldSt.castlingRights) {
        const std::uint8_t newRights =
            std::uint8_t(oldSt.castlingRights & CastlingRightsMask[from] & CastlingRightsMask[to]);
        if (newRights != oldSt.castlingRights) {
            newSt.castlingRights = newRights;
            newSt.key ^= Zobrist::castling[oldSt.castlingRights] ^ Zobrist::castling[newRights];
        }
    }

    // 3) Captures (including en passant).
    if (mt == EnPassantMove || board_[to] != NoPiece) {
        const Square capSq = (mt == EnPassantMove) ? Square(int(to) ^ 8) : to;
        const Piece captured = board_[capSq];
        newSt.capturedPiece = captured;
        newSt.rule50 = 0;
        newSt.key ^= Zobrist::psq[captured][capSq];
        acc_sub(newSt, captured, capSq);
        remove_piece(capSq);
    }

    // 4) Move the piece.
    newSt.key ^= Zobrist::psq[pc][from] ^ Zobrist::psq[pc][to];
    acc_sub(newSt, pc, from);
    acc_add(newSt, pc, to);
    move_piece(from, to);

    // 5) Promotions: swap the arrived pawn for the promotion piece.
    if (mt == PromotionMove) {
        const Piece promo = make_piece(us, promotion_type(m));
        newSt.rule50 = 0;
        newSt.key ^= Zobrist::psq[pc][to] ^ Zobrist::psq[promo][to];
        acc_sub(newSt, pc, to);
        acc_add(newSt, promo, to);
        remove_piece(to);
        put_piece(promo, to);
    }

    // 6) Pawn specifics: double push sets the en-passant target.
    if (type_of(pc) == Pawn) {
        newSt.rule50 = 0;
        if (std::abs(int(to) - int(from)) == 16) {
            const Square epSq = Square((int(from) + int(to)) / 2);
            newSt.epSquare = std::uint8_t(epSq);
        }
    }

    // 7) Castling: also move the rook.
    if (mt == CastlingMove) {
        const bool kingSide = (file_of(to) == FileG);
        const Square rfrom = kingSide ? (us == White ? SQ_H1 : SQ_H8)
                                      : (us == White ? SQ_A1 : SQ_A8);
        const Square rto = kingSide ? Square(int(to) - 1) : Square(int(to) + 1);
        const Piece rook = make_piece(us, Rook);
        newSt.key ^= Zobrist::psq[rook][rfrom] ^ Zobrist::psq[rook][rto];
        acc_sub(newSt, rook, rfrom);
        acc_add(newSt, rook, rto);
        move_piece(rfrom, rto);
    }

    // 8) Hand over the move.
    sideToMove_ = them;
    newSt.key ^= Zobrist::side;
    if (us == Black) ++fullmoveNumber_;
    if (legal_en_passant_capturers())
        newSt.key ^= Zobrist::epFile[file_of(Square(newSt.epSquare))];

    // Once a pawn move, capture, or loss of castling rights occurs, none of
    // the preceding positions can repeat. Otherwise retain the path context.
    newSt.historyContext = (newSt.rule50 == 0 || newSt.castlingRights != oldSt.castlingRights)
        ? Zobrist::context_seed(newSt.key) : Zobrist::context_next(oldSt.historyContext, newSt.key);

    // 9) Check/pin info for the new side to move.
    set_check_info();

    if (!trackRepetition) return;
    // Only scan the stored, reversible history; a FEN can have a large clock
    // even though we do not know the preceding game positions.
    const size_t idx = history_.size() - 1;
    const size_t end = std::min<std::size_t>(idx,
        std::min<std::uint64_t>(newSt.rule50, newSt.pliesFromStart));
    for (size_t d = 4; d <= end; d += 2) {
        if (history_[idx - d].key == newSt.key) {
            newSt.repetition = d;
            break;
        }
    }
}

void Position::make_null_move() {
    if (history_.empty()) throw std::invalid_argument("null move requires an initialized position");
    StateInfo newState = st();
    history_.push_back(newState);
    StateInfo& newSt = history_.back();
    if (legal_en_passant_capturers())
        newSt.key ^= Zobrist::epFile[file_of(Square(newState.epSquare))];
    newSt.epSquare = SQ_NONE;
    newSt.repetition = 0;
    newSt.pliesFromStart = newState.pliesFromStart + 1;
    sideToMove_ = ~sideToMove_;
    newSt.key ^= Zobrist::side;
    newSt.historyContext = Zobrist::context_seed(newSt.key);
    set_check_info();
}

void Position::unmake_null_move() {
    if (history_.size() < 2) throw std::invalid_argument("no null move to unmake");
    // make_null_move() never touches fullmoveNumber_, so unmaking must not
    // either: doing so drifted the counter (and the FEN) after every null move,
    // which null-move pruning performs many times per search.
    sideToMove_ = ~sideToMove_;
    history_.pop_back();
}

void Position::unmake_move(Move m) {
    // The captured piece belongs to the state being removed, not its parent.
    const Piece captured = Piece(st().capturedPiece);
    history_.pop_back(); // restores key, accumulators, checkers, pins, clocks

    const Color us = ~sideToMove_;
    sideToMove_ = us;
    if (us == Black) --fullmoveNumber_;

    const Square from = move_from(m);
    const Square to = move_to(m);
    const MoveType mt = move_type(m);

    if (mt == CastlingMove) {
        const bool kingSide = (file_of(to) == FileG);
        const Square rfrom = kingSide ? (us == White ? SQ_H1 : SQ_H8)
                                      : (us == White ? SQ_A1 : SQ_A8);
        const Square rto = kingSide ? Square(int(to) - 1) : Square(int(to) + 1);
        move_piece(rto, rfrom);
    }
    if (mt == PromotionMove) {
        remove_piece(to);
        put_piece(make_piece(us, Pawn), to);
    }
    move_piece(to, from);

    if (captured != NoPiece) {
        const Square capSq = (mt == EnPassantMove) ? Square(int(to) ^ 8) : to;
        put_piece(captured, capSq);
    }
}

// ---------------------------------------------------------------------------
// Move generation
// ---------------------------------------------------------------------------
void generate_moves(const Position& pos, MoveList& ml, GenType type) {
    ml.clear();

    const Color us = pos.side_to_move();
    const Color them = ~us;
    const bool qsearch = (type == GenType::QSearch);
    const Square ksq = pos.king_square(us);
    const Bitboard occ = pos.pieces();
    const Bitboard checkers = pos.checkers();
    const Bitboard pinned = pos.pinned();

    // Squares a move may land on. The enemy king is never a target: a king must
    // never be capturable as an ordinary move.
    const Bitboard target = qsearch
        ? (pos.pieces(them) & ~pos.pieces(them, King))
        : (~pos.pieces(us) & ~pos.pieces(them, King));

    // --- King moves (never restricted by `evasions`; each destination is
    // tested for attacks with the king removed from the occupancy).
    const Bitboard occNoKing = occ ^ square_bb(ksq);
    Bitboard b = KingAttacksBB[ksq] & target;
    while (b) {
        const Square to = pop_lsb(b);
        if (!pos.attacked_by(them, to, occNoKing)) ml.add(make_move(ksq, to));
    }

    // --- Castling (quiet moves only, never out of check).
    if (!qsearch && !checkers) {
        if (us == White) generate_castling<White>(pos, ml);
        else             generate_castling<Black>(pos, ml);
    }

    // Double check: only the king may move.
    if (more_than_one(checkers)) return;

    // Legal landing squares for non-king moves when in check.
    Bitboard evasions = AllSquaresBB;
    if (checkers)
        evasions = BetweenBB[ksq][lsb_square(checkers)] | checkers;

    // --- Pawns.
    if (us == White) generate_pawn_moves<White>(pos, ml, evasions, qsearch);
    else             generate_pawn_moves<Black>(pos, ml, evasions, qsearch);

    // --- Knights (a pinned knight can never move legally).
    b = pos.pieces(us, Knight) & ~pinned;
    while (b) {
        const Square from = pop_lsb(b);
        Bitboard att = KnightAttacksBB[from] & target;
        if (checkers) att &= evasions;
        while (att) ml.add(make_move(from, pop_lsb(att)));
    }

    // --- Sliders.
    for (PieceType pt : { Bishop, Rook, Queen }) {
        b = pos.pieces(us, pt);
        while (b) {
            const Square from = pop_lsb(b);
            Bitboard att = slider_attacks_bb(pt, from, occ) & target;
            if (checkers) att &= evasions;
            if (pinned & square_bb(from)) att &= LineBB[ksq][from];
            while (att) ml.add(make_move(from, pop_lsb(att)));
        }
    }
}

Move move_from_uci(const Position& pos, const std::string& s) {
    const Move raw = move_from_uci(s);
    if (!is_ok(raw)) return MOVE_NONE;

    MoveList ml;
    generate_moves(pos, ml, GenType::All);
    const Square from = move_from(raw);
    const Square to = move_to(raw);
    const bool hasPromo = (s.size() == 5);

    for (const ExtMove& em : ml) {
        if (move_from(em.move) == from && move_to(em.move) == to) {
            if (hasPromo) {
                if (move_type(em.move) == PromotionMove && promotion_type(em.move) == promotion_type(raw))
                    return em.move;
            } else if (move_type(em.move) != PromotionMove) {
                return em.move;
            }
        }
    }
    return MOVE_NONE;
}

// ---------------------------------------------------------------------------
// Draws / terminal detection
// ---------------------------------------------------------------------------
bool Position::insufficient_material() const {
    if (pieces(Pawn) || pieces(Rook) || pieces(Queen)) return false;
    const int knights = popcount(pieces(Knight));
    const Bitboard bishops = pieces(Bishop);
    const int bishopCount = popcount(bishops);
    if (knights + bishopCount <= 1) return true;
    // Any number of same-colored bishops without other material cannot mate.
    if (knights == 0) {
        constexpr Bitboard darkSquares = 0xAA55AA55AA55AA55ULL;
        return (bishops & darkSquares) == 0 || (bishops & ~darkSquares) == 0;
    }
    return false;
}

bool Position::has_legal_moves() const {
    MoveList ml;
    generate_moves(*this, ml, GenType::All);
    return !ml.empty();
}

int Position::repetition_count() const {
    const Key k = st().key;
    int n = 0;
    for (size_t i = history_.size() - 1;; i -= 2) {
        if (history_[i].key == k) ++n;
        if (i < 2) break;
    }
    return n;
}

bool Position::can_claim_threefold() const {
    if (repetition_count() >= 3) return has_legal_moves();
    Position copy = *this;
    MoveList moves; generate_moves(copy, moves);
    for (const ExtMove& em : moves) {
        copy.make_move(em.move);
        const bool claim = copy.repetition_count() >= 3;
        copy.unmake_move(em.move);
        if (claim) return true;
    }
    return false;
}

bool Position::can_claim_fifty_moves() const {
    if (rule50() >= 100) return has_legal_moves();
    if (rule50() < 99) return false;
    Position copy = *this;
    MoveList moves; generate_moves(copy, moves);
    for (const ExtMove& em : moves) {
        copy.make_move(em.move);
        // The announced move has to leave the game playable; a move ending it
        // by checkmate/stalemate cannot create a later claim.
        const bool claim = copy.rule50() >= 100 && copy.has_legal_moves();
        copy.unmake_move(em.move);
        if (claim) return true;
    }
    return false;
}

DrawStatus Position::draw_status() const {
    // Checkmate takes precedence, including on the 150th halfmove.
    if (!has_legal_moves())
        return in_check() ? DrawStatus::None : DrawStatus::AutomaticStalemate;
    if (insufficient_material()) return DrawStatus::AutomaticInsufficientMaterial;
    // Article 5.2.2 ends the game immediately, before any move-count rule can
    // apply. Only a proved verdict is reported; an inconclusive analysis leaves
    // the position alive for the remaining rules.
    if (analyze_dead_position(*this, fast_dead_limits()).status == DeadStatus::Dead)
        return DrawStatus::AutomaticDeadPosition;
    if (rule50() >= 150) return DrawStatus::AutomaticSeventyFiveMove;
    const int repetitions = repetition_count();
    if (repetitions >= 5) return DrawStatus::AutomaticFivefold;
    if (can_claim_fifty_moves()) return DrawStatus::ClaimableFiftyMove;
    if (can_claim_threefold()) return DrawStatus::ClaimableThreefold;
    return DrawStatus::None;
}

bool Position::is_search_draw(int plyFromRoot) const {
    // Search treats claimable draws as claimed. A repeated position inside the
    // search tree is a standard cycle-breaking heuristic, not a FIDE claim; a
    // repetition that lies entirely before the search root must be a genuine
    // threefold occurrence to count.
    const StateInfo& s = st();
    bool repetition = false;
    if (s.repetition) {
        if (s.repetition <= static_cast<size_t>(std::max(0, plyFromRoot)))
            repetition = true;
        else
            repetition = repetition_count() >= 3;
    }
    if (s.rule50 < 100 && !repetition && !insufficient_material()) return false;
    // Checkmate always takes precedence over a move-count or repetition draw.
    return !in_check() || has_legal_moves();
}

// ---------------------------------------------------------------------------
// Perft
// ---------------------------------------------------------------------------
std::uint64_t Position::perft(int depth) {
    if (depth <= 0) return 1;

    MoveList ml;
    generate_moves(*this, ml, GenType::All);
    if (depth == 1) return std::uint64_t(ml.size());

    std::uint64_t nodes = 0;
    for (const ExtMove& em : ml) {
        make_move(em.move);
        nodes += perft(depth - 1);
        unmake_move(em.move);
    }
    return nodes;
}

// ---------------------------------------------------------------------------
// Debug verification (used by stress tests)
// ---------------------------------------------------------------------------
bool Position::verify_state(std::string* error) const {
    auto fail = [&](const char* msg) {
        if (error) *error = msg;
        return false;
    };

    // Mailbox vs bitboards consistency.
    Bitboard all = 0;
    for (Square s = SQ_A1; s <= SQ_H8; s = Square(int(s) + 1)) {
        const Piece pc = board_[s];
        if (pc == NoPiece) continue;
        all |= square_bb(s);
        if (!(byTypeBB[type_of(pc)] & square_bb(s))) return fail("type bitboard missing piece");
        if (!(byColorBB[color_of(pc)] & square_bb(s))) return fail("color bitboard missing piece");
    }
    if (all != byTypeBB[NoPieceType]) return fail("all-pieces bitboard mismatch");
    if ((byColorBB[White] | byColorBB[Black]) != all) return fail("color union mismatch");
    if ((byColorBB[White] & byColorBB[Black]) != 0) return fail("color overlap");
    if (count(White, King) != 1 || count(Black, King) != 1) return fail("king count");
    if (board_[kingSquare_[White]] != WhiteKing) return fail("white king square");
    if (board_[kingSquare_[Black]] != BlackKing) return fail("black king square");

    // Hash key recomputation.
    Key k = 0;
    for (Square s = SQ_A1; s <= SQ_H8; s = Square(int(s) + 1))
        if (board_[s] != NoPiece) k ^= Zobrist::psq[board_[s]][s];
    if (sideToMove_ == Black) k ^= Zobrist::side;
    k ^= Zobrist::castling[st().castlingRights];
    if (legal_en_passant_capturers()) k ^= Zobrist::epFile[file_of(Square(st().epSquare))];
    if (k != st().key) return fail("zobrist key mismatch");
    Key context = Zobrist::context_seed(history_.front().key);
    for (size_t i = 1; i < history_.size(); ++i) {
        context = (history_[i].rule50 == 0 ||
                   history_[i].castlingRights != history_[i - 1].castlingRights)
            ? Zobrist::context_seed(history_[i].key)
            : Zobrist::context_next(context, history_[i].key);
    }
    if (context != st().historyContext) return fail("history context mismatch");

    // Accumulator recomputation.
    int mg[ColorNB] = { 0, 0 }, eg[ColorNB] = { 0, 0 };
    for (Square s = SQ_A1; s <= SQ_H8; s = Square(int(s) + 1)) {
        const Piece pc = board_[s];
        if (pc == NoPiece) continue;
        const int idx = pst_index(color_of(pc), s);
        mg[color_of(pc)] += PieceValueMg[type_of(pc)] + PieceSquareMg[type_of(pc)][idx];
        eg[color_of(pc)] += PieceValueEg[type_of(pc)] + PieceSquareEg[type_of(pc)][idx];
    }
    if (mg[White] != st().accMg[White] || mg[Black] != st().accMg[Black])
        return fail("mg accumulator mismatch");
    if (eg[White] != st().accEg[White] || eg[Black] != st().accEg[Black])
        return fail("eg accumulator mismatch");

    // Checkers / pinned recomputation.
    if (compute_checkers() != st().checkers) return fail("checkers mismatch");
    if (compute_pinned() != st().pinned) return fail("pinned mismatch");

    return true;
}

// ---------------------------------------------------------------------------
// FEN delegation (implemented in fen.cpp, which is a friend of Position)
// ---------------------------------------------------------------------------
bool Position::set(const std::string& fen, std::string* error) {
    return parse_fen(fen, *this, error);
}

std::string Position::fen() const {
    // Implemented in fen.cpp via friendship-free public accessors only.
    std::string out;

    for (int r = Rank8; r >= Rank1; --r) {
        int emptyRun = 0;
        for (int f = FileA; f <= FileH; ++f) {
            const Piece pc = piece_on(make_square(f, r));
            if (pc == NoPiece) { ++emptyRun; continue; }
            if (emptyRun) { out += char('0' + emptyRun); emptyRun = 0; }
            static const char* names = " PNBRQK  pnbrqk";
            out += names[int(pc)];
        }
        if (emptyRun) out += char('0' + emptyRun);
        if (r > Rank1) out += '/';
    }

    out += (sideToMove_ == White) ? " w " : " b ";

    const std::uint8_t cr = castling_rights();
    if (cr == NoCastling) out += '-';
    else {
        if (cr & WhiteOO)  out += 'K';
        if (cr & WhiteOOO) out += 'Q';
        if (cr & BlackOO)  out += 'k';
        if (cr & BlackOOO) out += 'q';
    }
    out += ' ';

    if (ep_square() == SQ_NONE) out += '-';
    else {
        out += char('a' + file_of(ep_square()));
        out += char('1' + rank_of(ep_square()));
    }

    out += ' ' + std::to_string(rule50());
    out += ' ' + std::to_string(fullmove_number());
    return out;
}

} // namespace stockbear
