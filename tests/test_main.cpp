#include "test.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    const std::string filter = argc > 1 ? argv[1] : "";
    int count = 0, failed = 0;
    for (const auto& c : test::cases()) {
        if (!filter.empty() && filter != c.group) continue;
        ++count;
        try { c.run(); std::cout << "PASS " << c.group << '/' << c.name << '\n'; }
        catch (const std::exception& e) {
            ++failed;
            std::cerr << "FAIL " << c.group << '/' << c.name << ": " << e.what() << '\n';
        }
    }
    std::cout << "Tests: " << count << ", failures: " << failed << '\n';
    return count == 0 || failed ? 1 : 0;
}
