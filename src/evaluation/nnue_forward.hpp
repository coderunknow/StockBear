// ---------------------------------------------------------------------------
// nnue_forward.hpp - the integer forward pass, split out so that a SIMD build
// of one translation unit can be selected at run time.
//
// `forward()` consumes the two perspective accumulators (already summed) and
// returns the raw layer-3 integer output; the caller applies `net.outShift` and
// the mate clamp.
//
// The two arguments are ordered **side-to-move first**: `stm` is the accumulator
// of the perspective of the side to move and `opp` the opponent's. That ordering
// is what makes the output a score for the side to move. The accumulators
// themselves are stored colour-indexed (White, Black) because that is the only
// indexing the incremental update can maintain across a move; `evaluate()`
// performs the (free) pointer swap. Getting this ordering wrong is invisible at
// test time but makes the network unable to learn anything (the same position
// then maps to the same input with opposite targets), so it is asserted in
// `test_nnue.cpp`.
//
// Every implementation must return bit-identical values, which `test_nnue.cpp`
// checks by running all available kernels on the same input.
// ---------------------------------------------------------------------------
#pragma once

#include "evaluation/nnue.hpp"

#include <cstdint>

namespace stockbear::nnue {

// Written so that the compiler can auto-vectorise it; always available.
std::int32_t forward_scalar(const Network& net, const std::int16_t* stm, const std::int16_t* opp);

// AVX2 kernel (fastest available on this project's CI machines). Only ever
// called after `cpu_has_avx2()` returned true.
#if defined(STOCKBEAR_HAVE_AVX2)
std::int32_t forward_avx2(const Network& net, const std::int16_t* stm, const std::int16_t* opp);
bool cpu_has_avx2();
#else
inline bool cpu_has_avx2() { return false; }
#endif

// The selected implementation. Resolved once on first use.
using ForwardFn = std::int32_t (*)(const Network&, const std::int16_t*, const std::int16_t*);
ForwardFn forward();
// Name of the selected kernel, for bench/uci provenance output.
const char* forward_kernel_name();

} // namespace stockbear::nnue
