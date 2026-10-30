// Strict standard-chess FEN parsing. Parsing is transactional: a failed parse
// never changes the live position, which is important for malformed UCI input.
#include "chess/fen.hpp"
#include "chess/position.hpp"
#include "evaluation/evaluation.hpp"

#include <charconv>
#include <sstream>
#include <string>
#include <utility>

namespace stockbear {
namespace {
Piece parse_piece(char c) {
    switch (c) {
    case 'P': return WhitePawn; case 'N': return WhiteKnight;
    case 'B': return WhiteBishop; case 'R': return WhiteRook;
    case 'Q': return WhiteQueen; case 'K': return WhiteKing;
    case 'p': return BlackPawn; case 'n': return BlackKnight;
    case 'b': return BlackBishop; case 'r': return BlackRook;
    case 'q': return BlackQueen; case 'k': return BlackKing;
    default: return NoPiece;
    }
}

bool parse_number(const std::string& str, std::uint64_t& n) {
    if (str.empty()) return false;
    const auto res = std::from_chars(str.data(), str.data() + str.size(), n);
    // Reserve ample headroom for subsequent search and game moves.
    return res.ec == std::errc() && res.ptr == str.data() + str.size()
        && n <= 1000000000000ULL;
}
}

bool parse_fen(const std::string& fen, Position& position, std::string* error) {
    auto fail = [error](const std::string& why) {
        if (error) *error = why;
        return false;
    };
    init_bitboards();
    Zobrist::init();
    init_evaluation();

    std::istringstream in(fen);
    std::string placement, side, castling, ep, halfmove, fullmove, extra;
    if (!(in >> placement >> side >> castling >> ep >> halfmove >> fullmove) || (in >> extra))
        return fail("FEN must have exactly six fields");

    Position p;
    p.history_.push_back(StateInfo{});
    p.st().epSquare = SQ_NONE;
    int rank = 7, file = 0;
    bool lastWasDigit = false;
    for (char c : placement) {
        if (c == '/') {
            if (file != 8 || rank == 0) return fail("invalid FEN rank width or count");
            --rank; file = 0; lastWasDigit = false;
        } else if (c >= '1' && c <= '8') {
            if (lastWasDigit) return fail("adjacent FEN empty-run digits");
            file += c - '0';
            if (file > 8) return fail("FEN rank is too long");
            lastWasDigit = true;
        } else {
            const Piece pc = parse_piece(c);
            if (pc == NoPiece || file >= 8) return fail("invalid FEN piece or rank width");
            if (type_of(pc) == Pawn && (rank == 0 || rank == 7))
                return fail("pawn on promotion rank");
            p.put_piece(pc, make_square(file++, rank));
            lastWasDigit = false;
        }
    }
    if (rank != 0 || file != 8) return fail("FEN must have eight complete ranks");
    for (Color c : {White, Black}) {
        if (p.count(c, King) != 1) return fail("FEN requires one king per side");
        if (p.count(c, Pawn) > 8 || popcount(p.pieces(c)) > 16)
            return fail("too many pieces or pawns for standard chess");
    }
    if (side == "w") p.sideToMove_ = White;
    else if (side == "b") p.sideToMove_ = Black;
    else return fail("invalid FEN active color");

    std::uint8_t rights = NoCastling;
    if (castling != "-") {
        for (char c : castling) {
            int bit = 0;
            switch (c) {
            case 'K': bit = WhiteOO; break; case 'Q': bit = WhiteOOO; break;
            case 'k': bit = BlackOO; break; case 'q': bit = BlackOOO; break;
            default: return fail("invalid FEN castling rights");
            }
            if (rights & bit) return fail("duplicate FEN castling right");
            rights = std::uint8_t(rights | bit);
        }
    }
    if ((rights & WhiteCastling) && p.piece_on(SQ_E1) != WhiteKing)
        return fail("white castling right without king on e1");
    if ((rights & BlackCastling) && p.piece_on(SQ_E8) != BlackKing)
        return fail("black castling right without king on e8");
    if (((rights & WhiteOO) && p.piece_on(SQ_H1) != WhiteRook) ||
        ((rights & WhiteOOO) && p.piece_on(SQ_A1) != WhiteRook) ||
        ((rights & BlackOO) && p.piece_on(SQ_H8) != BlackRook) ||
        ((rights & BlackOOO) && p.piece_on(SQ_A8) != BlackRook))
        return fail("castling right without the corresponding rook");
    p.st().castlingRights = rights;

    std::uint64_t hm = 0, fm = 0;
    if (!parse_number(halfmove, hm) || !parse_number(fullmove, fm) || fm == 0)
        return fail("invalid FEN move counters");
    p.st().rule50 = hm;
    p.fullmoveNumber_ = fm;

    if (ep != "-") {
        if (ep.size() != 2 || ep[0] < 'a' || ep[0] > 'h' ||
            ep[1] != (p.sideToMove_ == White ? '6' : '3'))
            return fail("invalid FEN en-passant square");
        const Square sq = make_square(ep[0] - 'a', ep[1] - '1');
        const Square victim = Square(int(sq) ^ 8);
        const Square origin = Square(int(sq) + (p.sideToMove_ == White ? 8 : -8));
        if (!p.empty(sq) || !p.empty(origin) ||
            p.piece_on(victim) != make_piece(~p.sideToMove_, Pawn) || hm != 0)
            return fail("FEN en-passant target is inconsistent with a double pawn push");
        p.st().epSquare = std::uint8_t(sq);
    }

    // Adjacent kings and a position where the player who just moved remains
    // in check cannot arise in legal standard chess.
    if (KingAttacksBB[p.king_square(White)] & square_bb(p.king_square(Black)))
        return fail("adjacent kings");
    if (p.attacked_by(p.sideToMove_, p.king_square(~p.sideToMove_)))
        return fail("side not to move is in check");

    StateInfo& st = p.st();
    st.key = Zobrist::castling[rights];
    if (p.sideToMove_ == Black) st.key ^= Zobrist::side;
    for (Square s = SQ_A1; s <= SQ_H8; s = Square(int(s) + 1)) {
        const Piece pc = p.piece_on(s);
        if (pc == NoPiece) continue;
        const Color c = color_of(pc);
        const PieceType pt = type_of(pc);
        const int idx = pst_index(c, s);
        st.key ^= Zobrist::psq[pc][s];
        st.accMg[c] += PieceValueMg[pt] + PieceSquareMg[pt][idx];
        st.accEg[c] += PieceValueEg[pt] + PieceSquareEg[pt][idx];
    }
    if (p.legal_en_passant_capturers()) st.key ^= Zobrist::epFile[file_of(p.ep_square())];
    st.historyContext = Zobrist::context_seed(st.key);
    p.set_check_info();
    position = std::move(p);
    if (error) error->clear();
    return true;
}
}
