// DEV6 exp-0048: full per-square piece-square table loader.
//
// Verifies the research evaluator variant is (a) bit-exact when the loaded
// tables equal the shipped formulaic ones, (b) actually changes the evaluation
// when the tables differ, (c) restored exactly by clear_pst_file(), and
// (d) rejects malformed files without mutating state. The group is kept
// separate from `unit` because it mutates process-wide evaluation tables.
#include "test.hpp"
#include "evaluation/evaluation.hpp"
#include "evaluation/eval_params.hpp"
#include <cstdio>
#include <fstream>
#include <string>

using namespace stockbear;

namespace {
const char* kSampleFens[] = {
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "r4rk1/1pp1qppp/p1np1n2/8/2B1P1b1/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 10",
};

std::string temp_path(const char* tag) {
    return std::string("pst_test_") + tag + ".sbpst";
}

void write_file(const std::string& path, const std::string& content) {
    std::ofstream out(path);
    out << content;
}

// Serialise the current derived tables into the SBPST1 file format.
std::string tables_to_file() {
    const PieceType order[6] = {Pawn, Knight, Bishop, Rook, Queen, King};
    std::string s = "SBPST1\n";
    for (PieceType pt : order)
        for (int idx = 0; idx < SQ_NB; ++idx)
            s += std::to_string(PieceSquareMg[pt][idx]) + " " +
                 std::to_string(PieceSquareEg[pt][idx]) + "\n";
    return s;
}
} // namespace

TEST(pst, formulaic_roundtrip_is_bit_exact) {
    init_evaluation();
    CHECK(!pst_file_active());
    int before[4];
    for (int i = 0; i < 4; ++i) before[i] = evaluate(test::position(kSampleFens[i]));
    const std::string path = temp_path("roundtrip");
    write_file(path, tables_to_file());
    std::string error;
    CHECK(load_pst_file(path, &error));
    CHECK(error.empty());
    CHECK(pst_file_active());
    for (int i = 0; i < 4; ++i)
        CHECK_EQ(evaluate(test::position(kSampleFens[i])), before[i]);
    clear_pst_file();
    CHECK(!pst_file_active());
    for (int i = 0; i < 4; ++i)
        CHECK_EQ(evaluate(test::position(kSampleFens[i])), before[i]);
    std::remove(path.c_str());
}

TEST(pst, zero_tables_change_evaluation_and_clear_restores) {
    init_evaluation();
    const int before = evaluate(test::position(kSampleFens[1]));
    std::string zeros = "SBPST1\n";
    for (int i = 0; i < 6 * 64; ++i) zeros += "0 0\n";
    const std::string path = temp_path("zeros");
    write_file(path, zeros);
    std::string error;
    CHECK(load_pst_file(path, &error));
    CHECK(pst_file_active());
    for (int idx = 0; idx < SQ_NB; ++idx) {
        CHECK_EQ(PieceSquareMg[Knight][idx], 0);
        CHECK_EQ(PieceSquareEg[King][idx], 0);
    }
    // Material is unchanged; only the piece-square term is removed, so a
    // middlegame position with developed pieces must evaluate differently.
    CHECK(evaluate(test::position(kSampleFens[1])) != before);
    clear_pst_file();
    CHECK(!pst_file_active());
    CHECK_EQ(evaluate(test::position(kSampleFens[1])), before);
    std::remove(path.c_str());
}

TEST(pst, malformed_files_are_rejected_without_mutation) {
    init_evaluation();
    const int before = evaluate(test::position(kSampleFens[0]));
    const std::string path = temp_path("bad");
    std::string error;
    // Wrong magic.
    write_file(path, "NOTPST\n");
    CHECK(!load_pst_file(path, &error));
    CHECK(!error.empty());
    CHECK(!pst_file_active());
    // Truncated.
    write_file(path, "SBPST1\n1 2\n");
    CHECK(!load_pst_file(path, &error));
    CHECK(!pst_file_active());
    // Out of range.
    std::string big = "SBPST1\n";
    for (int i = 0; i < 6 * 64; ++i) big += "99999 0\n";
    write_file(path, big);
    CHECK(!load_pst_file(path, &error));
    CHECK(!pst_file_active());
    // Trailing content.
    write_file(path, tables_to_file() + "extra\n");
    CHECK(!load_pst_file(path, &error));
    CHECK(!pst_file_active());
    // Missing file.
    CHECK(!load_pst_file(temp_path("does_not_exist"), &error));
    CHECK_EQ(evaluate(test::position(kSampleFens[0])), before);
    std::remove(path.c_str());
}

// The explicit table must survive a parameter reload: apply_eval_params()
// rebuilds the derived tables, and a naive implementation would silently drop
// the override and leave the caller believing the candidate is still loaded.
TEST(pst, override_survives_parameter_rebuild_and_reset) {
    init_evaluation();
    const EvalParams champion = default_eval_params();
    std::string error;
    CHECK(apply_eval_params(champion, &error));
    const int before = evaluate(test::position(kSampleFens[3]));
    std::string zeros = "SBPST1\n";
    for (int i = 0; i < 6 * 64; ++i) zeros += "0 0\n";
    const std::string path = temp_path("rebuild");
    write_file(path, zeros);
    CHECK(load_pst_file(path, &error));
    CHECK(pst_file_active());
    const int loaded = evaluate(test::position(kSampleFens[3]));
    CHECK(loaded != before);
    // Re-installing the same parameters must not clear the override.
    CHECK(apply_eval_params(champion, &error));
    CHECK(pst_file_active());
    CHECK_EQ(evaluate(test::position(kSampleFens[3])), loaded);
    // Explicitly clearing must restore the formulaic evaluation exactly.
    clear_pst_file();
    CHECK(!pst_file_active());
    CHECK_EQ(evaluate(test::position(kSampleFens[3])), before);
    std::remove(path.c_str());
}
