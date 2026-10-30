#pragma once
#include <cstdint>
#include <cstddef>
namespace stockbear {
struct PerftCase { const char* name; const char* fen; int depth; std::uint64_t expected; };
inline constexpr PerftCase PerftCases[] = {
#define PERFT(name, fen, depth, expected) {name, fen, depth, expected},
#include "../../benchmarks/positions/perft.inc"
#undef PERFT
};
struct SearchCase { const char* name; const char* fen; };
inline constexpr SearchCase SearchCases[] = {
#define SEARCH(name, fen) {name, fen},
#include "../../benchmarks/positions/search.inc"
#undef SEARCH
};
}
