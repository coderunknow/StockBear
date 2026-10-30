#include "uci/uci.hpp"
#include "utilities/bench.hpp"
#include "utilities/types.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc == 1) {
            stockbear::UciEngine uci(std::cin, std::cout);
            uci.loop();
            return 0;
        }
        const std::string command = argv[1];
        if (command == "--version") {
            std::cout << stockbear::kEngineName << ' ' << stockbear::kEngineVersion << '\n'; return 0;
        }
        if (command == "--help" || command == "-h") {
            std::cout << "StockBear " << stockbear::kEngineVersion << " (development prerelease)\n"
                      << "Usage:\n"
                      << "  stockbear                         UCI mode (default)\n"
                      << "  stockbear --version               Print version\n"
                      << "  stockbear perft DEPTH [--fen FEN] [--divide]\n"
                      << "  stockbear bench --perft           Run the verified perft suite\n"
                      << "  stockbear bench [--depth N | --nodes N] [--hash MB]\n";
            return 0;
        }
        if (command == "perft") return stockbear::perft_cli(argc - 2, argv + 2);
        if (command == "bench") return stockbear::benchmark_cli(argc - 2, argv + 2);
        std::cerr << "Unknown command: " << command << ". Use --help.\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "StockBear: " << e.what() << '\n';
        return 1;
    }
}
