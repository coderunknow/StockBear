#pragma once

namespace stockbear {

// `stockbear selfplay --games N --out FILE [--nodes N] [--seed N]
//                      [--maxplies N] [--hash MB]`
//
// Deterministic self-play corpus generation used to train the neural
// evaluation. See src/utilities/selfplay.cpp and docs/DEV4_TRAINING.md.
int selfplay_cli(int argc, char** argv);

} // namespace stockbear
