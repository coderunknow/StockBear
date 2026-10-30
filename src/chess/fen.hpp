#pragma once
#include <string>

namespace stockbear {
class Position;
inline constexpr const char* START_FEN =
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

// Transactional: on failure, `position` is left unchanged.
bool parse_fen(const std::string& fen, Position& position, std::string* error = nullptr);
}
