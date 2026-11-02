// AVX2 build of the integer forward pass. This translation unit is compiled
// with AVX2 enabled by CMake only when the compiler accepts the flag; it is
// only ever entered after a run-time CPUID check, so the released binaries keep
// running on machines without AVX2 through `forward_scalar`.
//
// Shape of the work at the sizes this project ships (l1 = 128, l2 = 32):
//
//   activation   256 int16 -> 256 int8-ish int16, ~4 instructions per 16 values
//   layer 2     32 rows x 256 int16 MACs = 8192 MACs, 16 MACs per instruction
//   layer 3     32 MACs
//
// The evaluation runs at every leaf, so the constant factor here is worth
// attacking: the first version of this kernel was ~3x slower than the classical
// evaluation and cost more strength than a better evaluation bought back.
#if defined(STOCKBEAR_HAVE_AVX2)

#include "evaluation/nnue_forward.hpp"

#include <algorithm>
#include <immintrin.h>

#if defined(_MSC_VER)
#include <intrin.h>
#endif

namespace stockbear::nnue {

bool cpu_has_avx2() {
#if defined(_MSC_VER)
    int regs[4] = {0, 0, 0, 0};
    __cpuid(regs, 0);
    if (regs[0] < 7) return false;
    __cpuidex(regs, 1, 0);
    // OSXSAVE and AVX must both be present, otherwise the OS is not saving
    // YMM state and executing AVX2 would fault.
    const bool osxsave = (regs[2] & (1 << 27)) != 0;
    const bool avx = (regs[2] & (1 << 28)) != 0;
    if (!osxsave || !avx) return false;
    if ((_xgetbv(0) & 0x6) != 0x6) return false;
    __cpuidex(regs, 7, 0);
    return (regs[1] & (1 << 5)) != 0;
#else
    return __builtin_cpu_supports("avx2") != 0;
#endif
}

namespace {

// Sum the eight int32 lanes of `v` without going through memory.
inline std::int32_t horizontal_sum(__m256i v) {
    const __m128i lo = _mm256_castsi256_si128(v);
    const __m128i hi = _mm256_extracti128_si256(v, 1);
    __m128i sum = _mm_add_epi32(lo, hi);
    sum = _mm_hadd_epi32(sum, sum);
    sum = _mm_hadd_epi32(sum, sum);
    return _mm_cvtsi128_si32(sum);
}

// act = clamp((acc + round) >> shift, 0, 127) for one perspective, 16 values at
// a time. Rounded, not truncated: truncation biases every activation downward.
inline void activate(const std::int16_t* acc, std::int16_t* act, int count, int shift,
                     std::int16_t round) {
    const __m256i roundv = _mm256_set1_epi16(round);
    const __m128i shiftv = _mm_cvtsi32_si128(shift);
    const __m256i zero = _mm256_setzero_si256();
    const __m256i top = _mm256_set1_epi16(127);
    int i = 0;
    for (; i + 16 <= count; i += 16) {
        __m256i v = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(acc + i));
        v = _mm256_adds_epi16(v, roundv);
        v = _mm256_sra_epi16(v, shiftv);
        v = _mm256_max_epi16(v, zero);
        v = _mm256_min_epi16(v, top);
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(act + i), v);
    }
    for (; i < count; ++i) {
        const int v = (int(acc[i]) + round) >> shift;
        act[i] = std::int16_t(std::clamp(v, 0, 127));
    }
}

} // namespace

std::int32_t forward_avx2(const Network& net, const std::int16_t* stm, const std::int16_t* opp) {
    const int l1 = net.l1;
    const int l2 = net.l2;
    // The vector loops read sixteen int16 elements at a time, so the layer width
    // must be a multiple of eight. Anything else (only reachable by loading a
    // hand-made network) goes through the scalar kernel instead of reading past
    // the activation buffer.
    const int span = 2 * l1;
    if (span % 16 != 0) return forward_scalar(net, stm, opp);
    alignas(32) std::int16_t act[2 * MaxL1];
    const std::int16_t actRound = net.actShift > 0 ? std::int16_t(1 << (net.actShift - 1)) : 0;
    activate(stm, act, l1, net.actShift, actRound);
    activate(opp, act + l1, l1, net.actShift, actRound);

    alignas(32) std::int16_t hid[MaxL2];
    const std::int32_t round2 = net.h2Shift > 0 ? (std::int32_t(1) << (net.h2Shift - 1)) : 0;
    int j = 0;
    // Two output rows per pass over the activations: the activation block is
    // 512 bytes at l1 = 128, so loading it twice for two rows is a real cost.
    for (; j + 2 <= l2; j += 2) {
        const std::int16_t* rowA = net.w2.data() + std::size_t(j) * std::size_t(span);
        const std::int16_t* rowB = rowA + span;
        __m256i accumA = _mm256_setzero_si256();
        __m256i accumB = _mm256_setzero_si256();
        for (int i = 0; i < span; i += 16) {
            const __m256i a = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(act + i));
            const __m256i wa = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(rowA + i));
            const __m256i wb = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(rowB + i));
            accumA = _mm256_add_epi32(accumA, _mm256_madd_epi16(a, wa));
            accumB = _mm256_add_epi32(accumB, _mm256_madd_epi16(a, wb));
        }
        hid[std::size_t(j)] = std::int16_t(std::clamp((horizontal_sum(accumA) + net.b2[std::size_t(j)] + round2) >> net.h2Shift, 0, 127));
        hid[std::size_t(j) + 1] = std::int16_t(std::clamp((horizontal_sum(accumB) + net.b2[std::size_t(j) + 1] + round2) >> net.h2Shift, 0, 127));
    }
    for (; j < l2; ++j) {
        const std::int16_t* row = net.w2.data() + std::size_t(j) * std::size_t(span);
        __m256i accum = _mm256_setzero_si256();
        for (int i = 0; i < span; i += 16) {
            const __m256i a = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(act + i));
            const __m256i w = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(row + i));
            accum = _mm256_add_epi32(accum, _mm256_madd_epi16(a, w));
        }
        hid[std::size_t(j)] = std::int16_t(std::clamp((horizontal_sum(accum) + net.b2[std::size_t(j)] + round2) >> net.h2Shift, 0, 127));
    }

    std::int32_t out = net.b3;
    for (int k = 0; k < l2; ++k) out += std::int32_t(hid[std::size_t(k)]) * std::int32_t(net.w3[std::size_t(k)]);
    return out;
}

} // namespace stockbear::nnue

#endif // STOCKBEAR_HAVE_AVX2
