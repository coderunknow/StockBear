// ---------------------------------------------------------------------------
// move.cpp - move <-> string conversions.
// ---------------------------------------------------------------------------
#include "chess/move.hpp"

namespace stockbear {

std::string move_to_uci(Move m) {
    if (!is_ok(m)) return "(none)";
    std::string s;
    s += char('a' + file_of(move_from(m)));
    s += char('1' + rank_of(move_from(m)));
    s += char('a' + file_of(move_to(m)));
    s += char('1' + rank_of(move_to(m)));
    if (move_type(m) == PromotionMove) {
        static const char promoChars[] = { 'n', 'b', 'r', 'q' }; // Knight..Queen
        s += promoChars[int(promotion_type(m)) - int(Knight)];
    }
    return s;
}

Move move_from_uci(const std::string& s) {
    if (s.size() != 4 && s.size() != 5) return MOVE_NONE;
    if (s[0] < 'a' || s[0] > 'h' || s[1] < '1' || s[1] > '8') return MOVE_NONE;
    if (s[2] < 'a' || s[2] > 'h' || s[3] < '1' || s[3] > '8') return MOVE_NONE;

    Square from = make_square(s[0] - 'a', s[1] - '1');
    Square to   = make_square(s[2] - 'a', s[3] - '1');

    if (s.size() == 5) {
        PieceType pt;
        switch (s[4]) {
        case 'n': pt = Knight; break;
        case 'b': pt = Bishop; break;
        case 'r': pt = Rook;   break;
        case 'q': pt = Queen;  break;
        default: return MOVE_NONE;
        }
        return make_promotion(from, to, pt);
    }
    return make_move(from, to);
}

} // namespace stockbear
