#pragma once

namespace stockbear {

// `stockbear nnue [--net FILE] [--info] [--features|--eval] [--input FILE]`
// Development/diagnostic entry point for the neural evaluation. See
// src/utilities/nnuecli.cpp.
int nnue_cli(int argc, char** argv);

} // namespace stockbear
