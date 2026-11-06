cmake_minimum_required(VERSION 3.16)

# ---------------------------------------------------------------------------
# StockBear - an independent chess engine.
#
# The single source of truth for the release version is the top-level VERSION
# file; it is injected into the binary as STOCKBEAR_VERSION so the executable,
# the UCI id string and the CMake project metadata can never drift apart.
# ---------------------------------------------------------------------------

file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" STOCKBEAR_VERSION_RAW)
string(STRIP "${STOCKBEAR_VERSION_RAW}" STOCKBEAR_VERSION_FULL)

string(REGEX MATCH "^[0-9]+[.][0-9]+[.][0-9]+" STOCKBEAR_VERSION_NUMBER "${STOCKBEAR_VERSION_FULL}")
if(NOT STOCKBEAR_VERSION_NUMBER)
    message(FATAL_ERROR "VERSION must begin with a numeric major.minor.patch")
endif()
project(StockBear
        VERSION ${STOCKBEAR_VERSION_NUMBER}
        DESCRIPTION "StockBear - an independent UCI chess engine"
        LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(STOCKBEAR_BUILD_TESTS "Build the StockBear test suite" ON)
option(STOCKBEAR_REQUIRE_PYTHON_TESTS "Fail configuration if Python UCI tests cannot run" OFF)
option(STOCKBEAR_NATIVE      "Enable -march=native (NOT used for released binaries)" OFF)
set(STOCKBEAR_SANITIZE "" CACHE STRING "Comma separated sanitizers, e.g. 'address,undefined'")

# --- Compiler flags ---------------------------------------------------------
if(MSVC)
    # /MT (and /MTd in Debug) avoids requiring a separate VC++ runtime on a
    # normal Windows machine. The OS and its standard system DLLs remain needed.
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    add_compile_options(/W4 /EHsc /utf-8)
    # /O2 is already the CMake default for Release with MSVC.
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS NOMINMAX)
else()
    add_compile_options(-Wall -Wextra -Wshadow -Wpedantic)
    set(CMAKE_CXX_FLAGS_RELEASE "-O3")
    set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g")
    if(STOCKBEAR_NATIVE)
        add_compile_options(-march=native)
    endif()
    if(STOCKBEAR_SANITIZE)
        add_compile_options(-fsanitize=${STOCKBEAR_SANITIZE} -fno-omit-frame-pointer -g)
        add_link_options(-fsanitize=${STOCKBEAR_SANITIZE})
    endif()
endif()

find_package(Threads REQUIRED)

# --- Engine core (everything except main) -----------------------------------
set(STOCKBEAR_CORE_SOURCES
    src/chess/bitboard.cpp
    src/chess/dead_position.cpp
    src/chess/fen.cpp
    src/chess/move.cpp
    src/chess/position.cpp
    src/chess/zobrist.cpp
    src/evaluation/eval_params.cpp
    src/evaluation/evaluation.cpp
    src/evaluation/nnue.cpp
    src/evaluation/nnue_forward.cpp
    src/evaluation/nnue_net_data.cpp
    src/search/search.cpp
    src/search/timeman.cpp
    src/search/transposition_table.cpp
    src/uci/uci.cpp
    src/utilities/bench.cpp
    src/utilities/evaldata.cpp
    src/utilities/nnuecli.cpp
    src/utilities/selfplay.cpp
)

add_library(stockbear_core STATIC ${STOCKBEAR_CORE_SOURCES})
target_include_directories(stockbear_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_compile_definitions(stockbear_core PUBLIC
    STOCKBEAR_VERSION="${STOCKBEAR_VERSION_FULL}"
    STOCKBEAR_VERSION_MAJOR=${PROJECT_VERSION_MAJOR}
    STOCKBEAR_VERSION_MINOR=${PROJECT_VERSION_MINOR}
    STOCKBEAR_VERSION_PATCH=${PROJECT_VERSION_PATCH})
target_link_libraries(stockbear_core PUBLIC Threads::Threads)

# Research-only ablation. Keep the dev4 evaluator as the default until an
# untouched fixed-time confirmation supports promoting this candidate.
option(STOCKBEAR_SAFE_MOBILITY "Experimental pawn-safe mobility evaluation" OFF)
if(STOCKBEAR_SAFE_MOBILITY)
    target_compile_definitions(stockbear_core PUBLIC STOCKBEAR_SAFE_MOBILITY=1)
endif()

# --- Optional AVX2 neural-network kernel -------------------------------------
# The engine must run on machines without AVX2, so the vectorised forward pass
# lives in its own translation unit that is compiled with AVX2 enabled and is
# entered only after a run-time CPUID check. When the compiler does not support
# the flag, the portable scalar kernel is used and STOCKBEAR_HAVE_AVX2 is not
# defined, so there is exactly one definition of the entry points either way.
include(CheckCXXCompilerFlag)
if(MSVC)
    set(STOCKBEAR_SIMD_FLAG "/arch:AVX2")
else()
    set(STOCKBEAR_SIMD_FLAG "-mavx2")
endif()
check_cxx_compiler_flag("${STOCKBEAR_SIMD_FLAG}" STOCKBEAR_HAS_SIMD_FLAG)
if(STOCKBEAR_HAS_SIMD_FLAG AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64|i.86)$")
    target_sources(stockbear_core PRIVATE src/evaluation/nnue_forward_avx2.cpp)
    set_source_files_properties(src/evaluation/nnue_forward_avx2.cpp PROPERTIES
        COMPILE_OPTIONS "${STOCKBEAR_SIMD_FLAG}")
    target_compile_definitions(stockbear_core PUBLIC STOCKBEAR_HAVE_AVX2=1)
    message(STATUS "StockBear: AVX2 neural kernel enabled (${STOCKBEAR_SIMD_FLAG}), run-time detected")
else()
    message(STATUS "StockBear: AVX2 neural kernel unavailable, scalar kernel only")
endif()

# --- Engine executable -------------------------------------------------------
add_executable(stockbear src/main.cpp)
target_link_libraries(stockbear PRIVATE stockbear_core)
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND CMAKE_SYSTEM_NAME STREQUAL "Linux" AND NOT STOCKBEAR_SANITIZE)
    # Avoid a separately installed libstdc++/libgcc runtime; glibc remains a
    # system dependency. The portable build does not select native CPU flags.
    target_link_options(stockbear PRIVATE -static-libstdc++ -static-libgcc)
endif()

# --- Magic-number generator (development tool) --------------------------------
add_executable(stockbear_genmagics tools/gen_magics.cpp)

# --- Tests --------------------------------------------------------------------
if(STOCKBEAR_BUILD_TESTS)
    enable_testing()

    add_executable(stockbear_tests
        tests/test_main.cpp
        tests/unit/test_bitboard.cpp
        tests/unit/test_dead_position.cpp
        tests/unit/test_draws.cpp
        tests/unit/test_eval.cpp
        tests/unit/test_eval_baseline.cpp
        tests/unit/test_fen.cpp
        tests/unit/test_move.cpp
        tests/unit/test_nnue.cpp
        tests/unit/test_position.cpp
        tests/unit/test_position_extra.cpp
        tests/unit/test_pst.cpp
        tests/unit/test_search.cpp
        tests/unit/test_timeman.cpp
        tests/unit/test_uci_parsing.cpp
        tests/unit/test_zobrist.cpp
        tests/perft/test_perft.cpp
        tests/regression/test_regression.cpp
        tests/stress/test_stress.cpp
    )
    target_link_libraries(stockbear_tests PRIVATE stockbear_core)
    target_include_directories(stockbear_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    target_compile_definitions(stockbear_tests PRIVATE
        STOCKBEAR_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")

    add_test(NAME unit        COMMAND stockbear_tests unit)
    # The neural-evaluation group has its own entry: it installs and clears the
    # process-wide network, so it is kept separate from the rest of `unit`.
    add_test(NAME nnue        COMMAND stockbear_tests nnue)
    # exp-0048 PST loader mutates process-wide evaluation tables, so it runs in
    # its own entry, isolated from the rest of `unit`.
    add_test(NAME pst         COMMAND stockbear_tests pst)
    # The runner filters by group name, so every group needs its own entry;
    # without this the position_extra group would never run under CTest.
    add_test(NAME position_extra COMMAND stockbear_tests position_extra)
    add_test(NAME regression  COMMAND stockbear_tests regression)
    add_test(NAME perft_quick COMMAND stockbear_tests perft_quick)
    add_test(NAME stress      COMMAND stockbear_tests stress)
    add_test(NAME perft_full  COMMAND stockbear_tests perft_full)
    set_tests_properties(perft_full PROPERTIES LABELS slow)
    # FIDE Article 5.2.2 dead-position analysis, including the exhaustive
    # two- and three-piece state-space sweeps; these are slower than the rest of
    # the unit suite, so they get their own CTest entry.
    add_test(NAME deadpos     COMMAND stockbear_tests deadpos)
    set_tests_properties(deadpos PROPERTIES LABELS slow)

    # UCI integration test (requires a Python 3 interpreter; skipped otherwise).
    if(STOCKBEAR_REQUIRE_PYTHON_TESTS)
        find_package(Python3 REQUIRED COMPONENTS Interpreter)
    else()
        find_package(Python3 COMPONENTS Interpreter)
    endif()
    if(Python3_Interpreter_FOUND)
        add_test(NAME uci_integration
                 COMMAND ${Python3_EXECUTABLE}
                         ${CMAKE_CURRENT_SOURCE_DIR}/tests/integration/test_uci_integration.py
                         $<TARGET_FILE:stockbear>)
        add_test(NAME uci_fuzz
                 COMMAND ${Python3_EXECUTABLE}
                         ${CMAKE_CURRENT_SOURCE_DIR}/tests/integration/test_uci_fuzz.py
                         $<TARGET_FILE:stockbear>)
        # The engine's feature function against an independent re-implementation;
        # a mismatch here means the training pipeline and the engine disagree
        # about what a network input is, which is invisible without this test.
        add_test(NAME nnue_features
                 COMMAND ${Python3_EXECUTABLE}
                         ${CMAKE_CURRENT_SOURCE_DIR}/tests/integration/test_nnue_features.py
                         $<TARGET_FILE:stockbear>)
        set_tests_properties(uci_integration uci_fuzz nnue_features PROPERTIES
            ENVIRONMENT "PYTHONUNBUFFERED=1" TIMEOUT 30)
    else()
        message(WARNING "Python3 not found - UCI integration test will not be registered")
    endif()
endif()

# --- Install -------------------------------------------------------------------
include(GNUInstallDirs)
install(TARGETS stockbear RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

message(STATUS "StockBear version: ${STOCKBEAR_VERSION_FULL}")
