#include "evaluation/nnue_forward.hpp"

#include <algorithm>

namespace stockbear::nnue {

std::int32_t forward_scalar(const Network& net, const std::int16_t* stm, const std::int16_t* opp) {
    const std::int16_t* const acc[ColorNB] = {stm, opp};
    const int l1 = net.l1;
    const int l2 = net.l2;
    const int span = 2 * l1;
    // Clipped ReLU on the accumulator, both perspectives concatenated.
    // Round, do not truncate, when scaling down. Truncation is a *biased*
    // rounding: every unit loses on average half a step, and since the network
    // output is a weighted sum of all units the bias accumulates into a
    // systematic shrinkage of the score (measured at ~4% of the evaluation
    // before this was fixed). The loader rejects networks whose accumulator
    // could come within 767 of the int16 limit, so the added half-step cannot
    // overflow.
    const int actRound = net.actShift > 0 ? (1 << (net.actShift - 1)) : 0;
    std::int16_t act[2 * MaxL1];
    for (int p = 0; p < ColorNB; ++p)
        for (int i = 0; i < l1; ++i) {
            const int v = (int(acc[p][i]) + actRound) >> net.actShift;
            act[std::size_t(p * l1 + i)] = std::int16_t(std::clamp(v, 0, 127));
        }
    std::int16_t hid[MaxL2];
    for (int j = 0; j < l2; ++j) {
        std::int32_t sum = net.b2[std::size_t(j)];
        const std::int16_t* row = net.w2.data() + std::size_t(j) * std::size_t(span);
        for (int i = 0; i < span; ++i) sum += std::int32_t(act[i]) * std::int32_t(row[i]);
        const std::int32_t round2 = net.h2Shift > 0 ? (std::int32_t(1) << (net.h2Shift - 1)) : 0;
        hid[std::size_t(j)] = std::int16_t(std::clamp((sum + round2) >> net.h2Shift, 0, 127));
    }
    std::int32_t out = net.b3;
    for (int j = 0; j < l2; ++j) out += std::int32_t(hid[std::size_t(j)]) * std::int32_t(net.w3[std::size_t(j)]);
    return out;
}

namespace {
ForwardFn select_kernel() {
#if defined(STOCKBEAR_HAVE_AVX2)
    if (cpu_has_avx2()) return &forward_avx2;
#endif
    return &forward_scalar;
}
}

ForwardFn forward() {
    static const ForwardFn fn = select_kernel();
    return fn;
}

const char* forward_kernel_name() {
#if defined(STOCKBEAR_HAVE_AVX2)
    if (forward() == &forward_avx2) return "avx2";
#endif
    return "scalar";
}

} // namespace stockbear::nnue
