// Evaluation parameter table, validation and the derived lookup tables.
#include "evaluation/eval_params.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>

namespace stockbear {
namespace {

// The shipped table. `mg` and `eg` reproduce dev2 exactly: dev2 derived the
// piece-square tables from closed-form expressions with a per-piece constant,
// and those constants are folded into the material rows here (knight 320-24 =
// 296, bishop 335-12 = 323, queen 975-6 = 969; endgame likewise). The king's
// endgame constant -30 applied to both kings and therefore cancelled in the
// difference, so it is simply dropped. `stockbear evaldata --check` verifies on
// real positions that this representation evaluates bit-identically to dev2.
// These are also the values dev3 ships: three tuned candidate sets were measured
// by matches and none was stronger (see docs/TUNING.md and
// benchmarks/results/0.1.0-dev3/), so the release keeps the dev2 evaluation.
constexpr std::array<EvalParamDef, EvalParamNB> kTable = {{
    {"MaterialPawn", 100, 120, 50, 200},
    {"MaterialKnight", 296, 287, 200, 500},
    {"MaterialBishop", 323, 320, 200, 520},
    {"MaterialRook", 500, 520, 400, 800},
    {"MaterialQueen", 969, 938, 700, 1600},
    {"PstPawnRank", 5, 9, -12, 24},
    {"PstPawnFile", 3, 2, -8, 12},
    {"PstKnightCenter", 9, 6, -6, 24},
    {"PstBishopCenter", 5, 4, -6, 20},
    {"PstRookRank", 2, 0, -8, 12},
    {"PstRookFile", 1, 0, -8, 8},
    {"PstRookCenter", 0, 2, -8, 12},
    {"PstQueenCenter", 2, 4, -6, 12},
    {"PstKingRank", -8, 0, -24, 8},
    {"PstKingFile", -5, 0, -16, 6},
    {"PstKingCenter", 0, 10, -8, 24},
    {"BishopPair", 28, 38, -20, 90},
    {"IsolatedPawn", -11, -9, -60, 10},
    {"DoubledPawn", -8, -12, -60, 10},
    {"PassedPawnAdvance", 2, 5, -4, 24},
    {"MobilityKnight", 4, 3, -2, 14},
    {"MobilityBishop", 4, 4, -2, 14},
    {"MobilityRook", 2, 3, -2, 14},
    {"MobilityQueen", 1, 2, -2, 10},
    {"RookOpenFile", 20, 12, -10, 60},
    {"RookSemiOpenFile", 10, 6, -10, 40},
    {"PawnShield", 8, 0, -8, 30},
    {"KingDangerPawn", 2, 0, 0, 14},
    {"KingDangerKnight", 3, 0, 0, 18},
    {"KingDangerBishop", 3, 0, 0, 18},
    {"KingDangerRook", 3, 0, 0, 18},
    {"KingDangerQueen", 5, 0, 0, 30},
}};

EvalParams gActive{};
bool gInstalled = false;

bool in_range(int value, const EvalParamDef& def, std::string* error, const char* name) {
    if (value < def.min || value > def.max) {
        if (error != nullptr) {
            *error = std::string("parameter ") + name + " out of range [" +
                     std::to_string(def.min) + ", " + std::to_string(def.max) +
                     "]: " + std::to_string(value);
        }
        return false;
    }
    return true;
}

std::string lower(std::string s) {
    for (char& c : s) c = char(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

int index_of(const std::string& name) {
    const std::string key = lower(name);
    for (int i = 0; i < EvalParamNB; ++i)
        if (key == lower(kTable[std::size_t(i)].name)) return i;
    return -1;
}
} // namespace

const std::array<EvalParamDef, EvalParamNB>& eval_param_table() { return kTable; }

EvalParams default_eval_params() {
    EvalParams p;
    for (int i = 0; i < EvalParamNB; ++i) {
        p.mg[std::size_t(i)] = kTable[std::size_t(i)].mg;
        p.eg[std::size_t(i)] = kTable[std::size_t(i)].eg;
    }
    return p;
}

const EvalParams& active_eval_params() { return gActive; }
bool eval_params_installed() { return gInstalled; }

bool apply_eval_params(const EvalParams& params, std::string* error) {
    for (int i = 0; i < EvalParamNB; ++i) {
        const auto& def = kTable[std::size_t(i)];
        if (!in_range(params.mg[std::size_t(i)], def, error, def.name) ||
            !in_range(params.eg[std::size_t(i)], def, error, def.name))
            return false;
    }
    gActive = params;
    gInstalled = true;
    evaluation_rebuild_tables();
    return true;
}

namespace {
// Strict integer parse: the whole token must be a number.
bool parse_int(const std::string& text, long long& out) {
    std::size_t used = 0;
    try {
        out = std::stoll(text, &used);
    } catch (const std::exception&) {
        return false;
    }
    return used == text.size();
}
} // namespace

bool load_eval_params_file(const std::string& path, EvalParams* params, std::string* error) {
    std::ifstream in(path);
    if (!in) {
        if (error != nullptr) *error = "cannot open parameter file " + path;
        return false;
    }
    EvalParams loaded = default_eval_params();
    std::array<bool, EvalParamNB> seen{};
    std::string line;
    int lineNo = 0;
    while (std::getline(in, line)) {
        ++lineNo;
        // Strip comments and whitespace; blank lines are allowed.
        const std::size_t hash = line.find('#');
        if (hash != std::string::npos) line.resize(hash);
        std::istringstream fields(line);
        std::string name, token;
        long long mg = 0, eg = 0;
        if (!(fields >> name)) continue;
        // Accept both "Name mg eg" and "Name = mg eg", plus a single value that
        // applies to both phases. Numbers must be consumed completely, so a
        // typo like "120junk" is rejected instead of silently meaning 120.
        if (!(fields >> token)) {
            if (error != nullptr) *error = "line " + std::to_string(lineNo) + ": missing value";
            return false;
        }
        if (token == "=" && !(fields >> token)) {
            if (error != nullptr) *error = "line " + std::to_string(lineNo) + ": missing value";
            return false;
        }
        if (!parse_int(token, mg)) {
            if (error != nullptr) *error = "line " + std::to_string(lineNo) + ": bad value " + token;
            return false;
        }
        eg = mg;
        if (fields >> token) {
            if (token == "=") {
                if (!(fields >> token) || !parse_int(token, eg)) {
                    if (error != nullptr) *error = "line " + std::to_string(lineNo) + ": bad value";
                    return false;
                }
            } else if (!parse_int(token, eg)) {
                if (error != nullptr) *error = "line " + std::to_string(lineNo) + ": bad value " + token;
                return false;
            }
        }
        if (fields >> token) {
            if (error != nullptr)
                *error = "line " + std::to_string(lineNo) + ": unexpected extra field " + token;
            return false;
        }
        const int id = index_of(name);
        if (id < 0) {
            if (error != nullptr) *error = "line " + std::to_string(lineNo) + ": unknown parameter " + name;
            return false;
        }
        if (mg < -100000 || mg > 100000 || eg < -100000 || eg > 100000) {
            if (error != nullptr) *error = "line " + std::to_string(lineNo) + ": value out of range";
            return false;
        }
        const auto& def = kTable[std::size_t(id)];
        if (!in_range(int(mg), def, error, def.name) || !in_range(int(eg), def, error, def.name))
            return false;
        loaded.mg[std::size_t(id)] = int(mg);
        loaded.eg[std::size_t(id)] = int(eg);
        seen[std::size_t(id)] = true;
    }
    // A partially specified file is accepted (the rest keeps the shipped
    // value) but reported, so an experiment cannot mistake a typo'd name for a
    // deliberate default.
    int missing = 0;
    for (bool s : seen) missing += s ? 0 : 1;
    if (missing != 0 && error != nullptr && error->empty())
        *error = std::to_string(missing) + " parameter(s) not present in the file; defaults kept";
    if (params != nullptr) *params = loaded;
    return true;
}

std::string format_eval_params(const EvalParams& params) {
    std::ostringstream out;
    out << "# StockBear evaluation parameters; " << EvalParamNB << " entries\n";
    for (int i = 0; i < EvalParamNB; ++i)
        out << kTable[std::size_t(i)].name << ' '
            << params.mg[std::size_t(i)] << ' ' << params.eg[std::size_t(i)] << '\n';
    return out.str();
}

std::uint64_t eval_params_checksum(const EvalParams& params) {
    // FNV-1a over the value pairs: a stable, endian-independent identity.
    std::uint64_t h = 1469598103934665603ULL;
    for (int i = 0; i < EvalParamNB; ++i) {
        for (int v : {params.mg[std::size_t(i)], params.eg[std::size_t(i)]}) {
            const std::uint32_t u = static_cast<std::uint32_t>(v);
            for (int byte = 0; byte < 4; ++byte) {
                h ^= (u >> (8 * byte)) & 0xFFU;
                h *= 1099511628211ULL;
            }
        }
    }
    return h;
}
} // namespace stockbear
