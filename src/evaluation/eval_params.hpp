// ---------------------------------------------------------------------------
// eval_params.hpp - the tunable parameters of StockBear's handcrafted
// evaluation, as data rather than as literals scattered through the code.
//
// Every number the evaluation uses is an entry in one table. The table is also
// the feature order of the offline tuner, so it must only ever be appended to:
// reordering or removing an entry would silently reinterpret a recorded dataset.
//
// The shipped defaults are the dev2 evaluation exactly (the dev2 piece-square
// formulae had per-piece constant terms, which are folded into the material
// values here; see eval_params.cpp for the arithmetic).
// ---------------------------------------------------------------------------
#pragma once

#include <array>
#include <cstdint>
#include <string>

namespace stockbear {

class Position;

enum EvalParamId : int {
    // Material (already includes the piece-square constant of the dev2 formula).
    MatPawn = 0, MatKnight, MatBishop, MatRook, MatQueen,
    // Piece-square terms: value = f(rank, fileCenter, center).
    PstPawnRank, PstPawnFile,
    PstKnightCenter,
    PstBishopCenter,
    PstRookRank, PstRookFile, PstRookCenter,
    PstQueenCenter,
    PstKingRank, PstKingFile, PstKingCenter,
    // Pawn structure and pieces.
    BishopPair,
    IsolatedPawn, DoubledPawn, PassedPawnAdvance,
    MobilityKnight, MobilityBishop, MobilityRook, MobilityQueen,
    RookOpenFile, RookSemiOpenFile,
    PawnShield,
    // Enemy attacks into our king zone, per attacking piece type.
    KingDangerPawn, KingDangerKnight, KingDangerBishop, KingDangerRook, KingDangerQueen,
    EvalParamNB
};

// One row of the table: a stable name, the shipped value for each phase and the
// range the tuner is allowed to explore. `min`/`max` are also enforced when a
// parameter file is loaded, so a mistyped or hostile file cannot brick the
// evaluation.
struct EvalParamDef {
    const char* name;
    int mg;
    int eg;
    int min;
    int max;
};

const std::array<EvalParamDef, EvalParamNB>& eval_param_table();

struct EvalParams {
    std::array<int, EvalParamNB> mg{};
    std::array<int, EvalParamNB> eg{};
    bool operator==(const EvalParams& other) const { return mg == other.mg && eg == other.eg; }
};

// The values the engine was compiled to ship with.
EvalParams default_eval_params();

// The process-wide parameter set. `apply_eval_params` validates, stores and
// rebuilds the derived tables (material values and piece-square tables).
// It must be called before the first Position is constructed: Position keeps
// material+piece-square accumulators that are initialized from those tables.
const EvalParams& active_eval_params();
// Validates every value against the table's range, stores the set and rebuilds
// the derived material/piece-square tables. Must run before the first Position
// is constructed.
bool apply_eval_params(const EvalParams& params, std::string* error = nullptr);

// True once some parameter set has been installed, either the shipped default
// or an explicit experiment set. `init_evaluation` uses it to avoid resetting an
// experiment when the next FEN is parsed.
bool eval_params_installed();

// Provided by evaluation.cpp; the supported way to change tables is
// `apply_eval_params`, which calls this after validation.
void evaluation_rebuild_tables();

// Reads `name mg eg` (or `name = mg eg`) lines, one parameter per line; unknown
// names and out-of-range values are errors, never silently ignored.
bool load_eval_params_file(const std::string& path, EvalParams* params, std::string* error);
std::string format_eval_params(const EvalParams& params);
// Stable identity for a parameter set, recorded in tuning and benchmark output.
std::uint64_t eval_params_checksum(const EvalParams& params);

// Component counts of the evaluation, always from White's point of view:
// score = clamp(taper(sum(mg*counts_mg), sum(eg*counts_eg), phase)).
struct EvalBreakdown {
    std::array<int, EvalParamNB> mg{};
    std::array<int, EvalParamNB> eg{};
    int phase = 0;
};
EvalBreakdown eval_breakdown(const Position& position);
int eval_from_breakdown(const EvalBreakdown& breakdown, const EvalParams& params);
}
