#!/bin/sh
# usage: nps.sh <binary> [depth]
BIN=$1; D=${2:-16}
(printf 'uci\nposition fen r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1\ngo depth %s\n' "$D"; sleep 30; printf 'quit\n') | "$BIN" 2>/dev/null | grep -E "^info depth" | tail -1 | sed -E 's/.*nodes ([0-9]+) nps ([0-9]+).*/nodes=\1 nps=\2/'
