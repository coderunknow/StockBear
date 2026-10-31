#include "uci/uci.hpp"
#include "chess/fen.hpp"
#include <algorithm>
#include <charconv>
#include <cctype>
#include <exception>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <vector>

namespace stockbear {
namespace {
std::string lower(std::string s) {
    for (char& c : s) c = char(std::tolower(static_cast<unsigned char>(c)));
    return s;
}
bool number(const std::string& text, std::uint64_t& result, std::uint64_t maximum) {
    if (text.empty()) return false;
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), result);
    return parsed.ec == std::errc() && parsed.ptr == text.data() + text.size() && result <= maximum;
}
std::string score_text(int score) {
    if (is_mate_value(score)) return "mate " + std::to_string(mate_value_to_moves(score));
    return "cp " + std::to_string(score);
}
std::string info_text(const SearchResult& r) {
    const std::uint64_t us = static_cast<std::uint64_t>(std::max<std::int64_t>(1, r.timeUs));
    const std::uint64_t nps = r.nodes > std::numeric_limits<std::uint64_t>::max() / 1000000
        ? std::numeric_limits<std::uint64_t>::max() : r.nodes * 1000000 / us;
    std::ostringstream out;
    out << "info depth " << r.depth << " seldepth " << r.selectiveDepth
        << " score " << score_text(r.score) << " nodes " << r.nodes
        << " nps " << nps << " hashfull " << r.hashfull << " time " << r.timeMs;
    if (!r.pv.empty()) {
        out << " pv";
        for (Move m : r.pv) out << ' ' << move_to_uci(m);
    }
    return out.str();
}
}

UciEngine::UciEngine(std::istream& input, std::ostream& output) : input_(input), output_(output) {
    std::string error;
    if (!position_.set(START_FEN, &error)) throw std::runtime_error("start position: " + error);
}
UciEngine::~UciEngine() { stop_and_join(); }
void UciEngine::emit(const std::string& line) {
    std::lock_guard<std::mutex> lock(outputMutex_);
    output_ << line << '\n' << std::flush;
}
void UciEngine::stop_and_join() {
    if (worker_.joinable()) {
        stop_.store(true, std::memory_order_relaxed);
        worker_.join();
    }
}

void UciEngine::handle_position(const std::string& arguments) {
    stop_and_join();
    std::istringstream in(arguments);
    std::string kind, fen, token, error;
    if (!(in >> kind)) { emit("info string position: missing startpos or fen"); return; }
    if (kind == "startpos") fen = START_FEN;
    else if (kind == "fen") {
        for (int i = 0; i < 6; ++i) {
            if (!(in >> token)) { emit("info string position: incomplete FEN"); return; }
            if (i) fen += ' ';
            fen += token;
        }
    } else { emit("info string position: expected startpos or fen"); return; }

    Position candidate;
    if (!candidate.set(fen, &error)) { emit("info string position: " + error); return; }
    if (in >> token) {
        if (token != "moves") { emit("info string position: expected moves"); return; }
        while (in >> token) {
            const Move move = move_from_uci(candidate, token);
            if (!is_ok(move)) { emit("info string position: illegal move " + token); return; }
            candidate.make_move(move);
        }
    }
    position_ = std::move(candidate);
}

void UciEngine::handle_setoption(const std::string& arguments) {
    stop_and_join();
    std::istringstream in(arguments);
    std::string token, name, value;
    if (!(in >> token) || lower(token) != "name") {
        emit("info string setoption: expected name"); return;
    }
    while (in >> token && lower(token) != "value") {
        if (!name.empty()) name += ' ';
        name += token;
    }
    if (lower(token) != "value" || !(in >> value)) {
        emit("info string setoption: expected name and value"); return;
    }
    std::string extra;
    const std::string key = lower(name);
    if (key == "hash") {
        std::uint64_t mb = 0;
        if ((in >> extra) || !number(value, mb, 512) || mb < 1) {
            emit("info string setoption: Hash must be 1..512 MB"); return;
        }
        try { table_.resize(static_cast<std::size_t>(mb)); }
        catch (const std::exception& e) { emit(std::string("info string Hash allocation failed: ") + e.what()); }
        return;
    }
    // Boolean ablation switches for the search features. They default to the
    // values the engine ships with, so a GUI that never sends them is
    // unaffected; matches can compare "all on" against a single feature off.
    bool* flag = nullptr;
    if (key == "nullmove") flag = &params_.nullMove;
    else if (key == "lmr") flag = &params_.lmr;
    else if (key == "aspiration") flag = &params_.aspiration;
    else if (key == "futility") flag = &params_.futility;
    else if (key == "reversefutility") flag = &params_.reverseFutility;
    else if (key == "seepruning") flag = &params_.seePruning;
    else if (key == "checkextension") flag = &params_.checkExtension;
    if (flag == nullptr) {
        emit("info string setoption: unknown option " + name); return;
    }
    if ((in >> extra)) { emit("info string setoption: unexpected value for " + name); return; }
    const std::string lowered = lower(value);
    if (lowered == "true" || lowered == "1") *flag = true;
    else if (lowered == "false" || lowered == "0") *flag = false;
    else { emit("info string setoption: " + name + " expects true or false"); return; }
}

void UciEngine::handle_go(const std::string& arguments) {
    stop_and_join();
    std::istringstream in(arguments);
    SearchLimits limits;
    std::string key, text;
    bool finite = false;
    while (in >> key) {
        if (key == "infinite") { limits.infinite = true; continue; }
        if (!(key == "depth" || key == "nodes" || key == "movetime" ||
              key == "wtime" || key == "btime" || key == "winc" || key == "binc" || key == "movestogo")) {
            // The UCI specification tells engines to ignore parameters they do
            // not understand (for example "ponder", "searchmoves" or a GUI
            // extension) instead of refusing the search. Malformed *values* of
            // the parameters we do understand are still rejected below, because
            // starting a search with a bogus clock or depth is worse than
            // ignoring the token.
            if (debug_) emit("info string go: ignoring unsupported token " + key);
            continue;
        }
        std::uint64_t n = 0;
        const std::uint64_t maximum = key == "nodes" ? std::numeric_limits<std::uint64_t>::max()
                                                      : 1000000000000ULL;
        if (!(in >> text)) { emit("info string go: invalid value for " + key); return; }
        // Some GUIs report a slightly negative remaining clock after a flag
        // falls. Clamp well-formed, bounded clocks to zero; other negative
        // parameters remain invalid. Do not start a search on malformed input.
        if ((key == "wtime" || key == "btime") && text.size() > 1 && text[0] == '-') {
            std::uint64_t magnitude = 0;
            if (!number(text.substr(1), magnitude, maximum)) {
                emit("info string go: invalid value for " + key); return;
            }
        } else if (!number(text, n, maximum)) {
            emit("info string go: invalid value for " + key); return;
        }
        if (key == "depth") {
            if (n < 1 || n > MAX_PLY - 2) { emit("info string go: depth out of range"); return; }
            limits.depth = int(n); finite = true;
        } else if (key == "nodes") { limits.hasNodes = true; limits.nodes = n; finite = true; }
        else if (key == "movetime") { limits.moveTimeMs = std::int64_t(n); finite = true; }
        else if (key == "wtime") { limits.whiteTimeMs = std::int64_t(n); finite = true; }
        else if (key == "btime") { limits.blackTimeMs = std::int64_t(n); finite = true; }
        else if (key == "winc") limits.whiteIncMs = std::int64_t(n);
        else if (key == "binc") limits.blackIncMs = std::int64_t(n);
        else if (key == "movestogo") {
            if (n < 1 || n > 10000) { emit("info string go: movestogo out of range"); return; }
            limits.movesToGo = int(n);
        }
    }
    // A clock only for the other side cannot time our search; absent any
    // applicable bound UCI go behaves like go infinite.
    const bool applicableTime = position_.side_to_move() == White ? limits.whiteTimeMs >= 0
                                                                 : limits.blackTimeMs >= 0;
    if (!finite || (!applicableTime && limits.moveTimeMs < 0 && !limits.hasNodes && limits.depth == 0))
        limits.infinite = true;

    Position root = position_;
    MoveList legal;
    generate_moves(root, legal);
    const Move fallback = legal.empty() ? MOVE_NONE : legal[0].move;
    stop_.store(false, std::memory_order_relaxed);
    try {
        worker_ = std::thread([this, root = std::move(root), limits, fallback]() mutable {
            try {
                auto search = std::make_unique<Search>(table_, params_);
                const SearchResult result = search->run(std::move(root), limits, stop_,
                    [this](const SearchResult& r) { emit(info_text(r)); });
                emit("bestmove " + (is_ok(result.bestMove) ? move_to_uci(result.bestMove) : "0000"));
            } catch (const std::exception& e) {
                emit(std::string("info string search error: ") + e.what());
                emit("bestmove " + (is_ok(fallback) ? move_to_uci(fallback) : "0000"));
            }
        });
    } catch (const std::exception& e) {
        emit(std::string("info string could not start search: ") + e.what());
        emit("bestmove " + (is_ok(fallback) ? move_to_uci(fallback) : "0000"));
    }
}

void UciEngine::loop() {
    std::string line;
    while (std::getline(input_, line)) {
        std::istringstream in(line);
        std::string command;
        if (!(in >> command)) continue;
        std::string arguments;
        std::getline(in, arguments);
        if (command == "uci") {
            emit(std::string("id name ") + kEngineName + " " + kEngineVersion);
            emit(std::string("id author ") + kEngineAuthors);
            emit("option name Hash type spin default 16 min 1 max 512");
            emit("option name NullMove type check default true");
            emit("option name LMR type check default true");
            emit("option name Aspiration type check default true");
            emit("option name Futility type check default true");
            emit("option name ReverseFutility type check default true");
            emit("option name SEEPruning type check default true");
            emit("option name CheckExtension type check default true");
            emit("uciok");
        } else if (command == "isready") emit("readyok");
        else if (command == "position") handle_position(arguments);
        else if (command == "go") handle_go(arguments);
        else if (command == "stop") stop_and_join();
        else if (command == "setoption") handle_setoption(arguments);
        else if (command == "ucinewgame") {
            stop_and_join(); table_.clear();
            std::string error;
            if (!position_.set(START_FEN, &error)) emit("info string ucinewgame: " + error);
        } else if (command == "debug") {
            std::istringstream arg(arguments);
            std::string mode;
            if (arg >> mode) debug_ = (mode == "on");
        } else if (command == "quit") { stop_and_join(); return; }
        else if (debug_) emit("info string ignoring unknown command " + command);
    }
    stop_and_join();
}
}
