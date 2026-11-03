#!/bin/bash
# Wipe recovery: rebuild .venv and both pinned binaries from git, then verify
# their SHA-256 fingerprints and bench signature. Safe to re-run.
set -e
cd "$(dirname "$0")/.."
export PATH="$PWD/.venv/bin:$PATH"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip -q install cmake ninja chess numpy
fi
# dev4 immutable baseline from the tag (worktree because the branch must stay put)
if [ ! -x build-dev4/stockbear ] || [ "$(sha256sum build-dev4/stockbear | cut -d' ' -f1)" != "1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae" ]; then
  rm -rf /tmp/dev4src
  git worktree add --force /tmp/dev4src v0.1.0-dev4 > /dev/null
  (cd /tmp/dev4src && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release > /dev/null 2>&1 \
     && cmake --build build -j 2 --target stockbear > /dev/null 2>&1)
  mkdir -p build-dev4
  cp /tmp/dev4src/build/stockbear build-dev4/stockbear
fi
# research champion build (bit-exact speedups only; bench must stay 243f9a1c1ba5b36f)
if [ ! -x build-dev6/stockbear ]; then
  cmake -S . -B build-dev6 -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1" > /dev/null 2>&1
  cmake --build build-dev6 -j 2 --target stockbear > /dev/null 2>&1
fi
echo "dev4  sha256: $(sha256sum build-dev4/stockbear | cut -d' ' -f1)  (expect 1c5b61a7...)"
echo "dev4  bench:  $(./build-dev4/stockbear bench 2>&1 | tail -1)  (expect 243f9a1c1ba5b36f)"
echo "champ sha256: $(sha256sum build-dev6/stockbear | cut -d' ' -f1)"
echo "champ bench:  $(./build-dev6/stockbear bench 2>&1 | tail -1)  (expect 243f9a1c1ba5b36f)"
