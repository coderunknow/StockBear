#pragma once
#include "chess/fen.hpp"
#include "chess/position.hpp"
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace test {
struct Case { const char* group; const char* name; void (*run)(); };
inline std::vector<Case>& cases() { static std::vector<Case> all; return all; }
struct Register {
    Register(const char* group, const char* name, void (*run)()) { cases().push_back({group,name,run}); }
};
inline void require(bool condition, const char* expression, const char* file, int line) {
    if (!condition) throw std::runtime_error(std::string(file) + ':' + std::to_string(line) + ": " + expression);
}
inline stockbear::Position position(const std::string& fen) {
    stockbear::Position p;
    std::string error;
    if (!p.set(fen, &error)) throw std::runtime_error("test FEN " + fen + ": " + error);
    return p;
}
inline void play(stockbear::Position& p, const std::string& text) {
    stockbear::Move m = stockbear::move_from_uci(p, text);
    if (!stockbear::is_ok(m)) throw std::runtime_error("illegal test move " + text + " in " + p.fen());
    p.make_move(m);
}
inline void state_ok(const stockbear::Position& p) {
    std::string error;
    if (!p.verify_state(&error)) throw std::runtime_error("state invariant: " + error + " in " + p.fen());
}
}
#define TEST(group, name) \
    static void test_##group##_##name(); \
    static test::Register register_##group##_##name(#group, #name, test_##group##_##name); \
    static void test_##group##_##name()
#define CHECK(expr) test::require(bool(expr), #expr, __FILE__, __LINE__)
// Copies, not const references: `CHECK_EQ(x, default_params().field)` would
// otherwise bind a reference to a member of a temporary and read it after the
// temporary has been destroyed.
#define CHECK_EQ(a, b) do { const auto test_a = (a); const auto test_b = (b); \
    test::require(test_a == test_b, #a " == " #b, __FILE__, __LINE__); } while (false)
