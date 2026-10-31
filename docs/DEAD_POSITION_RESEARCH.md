# Dead-position investigation — dev2 work in progress

**Release gate remains UNSATISFIED.** The existing engine's material test is a
sound subset, not a general detector. The new bounded research probe is not
used by search or adjudication. It does not meet the mandatory release gate.

## Semantics and state

FIDE [Article 5.2.2](https://rcc.fide.com/wp-content/uploads/2022/12/20230101Laws-of-Chess_final.pdf)
asks whether **either** player can mate by **any** legal sequence, not whether
one can force mate against opposition. Checkmate, stalemate, optional claims,
automatic fivefold repetition and 75-move termination are separate concepts;
checkmate takes precedence over the 75-move rule. Article 6.9 asks a different,
one-sided mate-possibility question for flag fall. Interactions between automatic
rules and the meaning of “any series of legal moves” must be resolved explicitly
against authoritative interpretations before a FIDE-complete claim.

A proposed input is a structurally valid standard-chess position with board,
side, castling rights and raw en-passant target, plus the actual reversible
history and halfmove clock where available. Moves include every promotion,
capture, pawn double push, legal en passant and castling, with king safety.
A FEN does not contain prior repetitions and does not prove reachability from the
initial array: neither facts may be invented. Distinguish the known-history
problem, the movement-only problem, and any treatment of unknown history. If
classification depends on unknown history, return unknown rather than assert a
FIDE conclusion. Dev1's parser checks structure, not full retrograde legality.

## Research and algorithm

[Brunner et al., *Complexity of Retrograde and Helpmate Chess Problems*](https://arxiv.org/abs/2010.09271)
prove generalized n-by-n cooperative helpmate PSPACE-complete (this does not
imply the fixed 8-by-8 problem is undecidable). [Ambrona, *A Practical Algorithm
for Chess Unwinnability*](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.FUN.2022.2)
describes conservative analysis followed by search. The independently studied
[Basic Helpmate Existence](https://github.com/dlbbld/basic-helpmate-existence/tree/8713284090507e7057adffd946065ab60a7f19b9)
uses retrograde reachability and independently verified witnesses in selected
material classes, including a promotion trap. Ordinary WDL tablebases solve a
forced-play problem and limited material scope, not this general cooperative
reachability problem. No third-party implementation was incorporated.

An exact but impractical decision procedure for the movement-only problem is
finite graph traversal: vertices contain piece placement, side, castling rights,
and EP target; edges are legal moves. Seed with the given position and traverse
all reachable vertices. If a checkmate is found, the recorded path is a witness;
if the frontier empties without one, no path to mate exists by induction on
path length. Exact identities, not hash values alone, are needed to avoid hash
collision errors. Promotions and captures change material but do not make this
finite graph infinite; castling and EP must remain part of state. A checkmate
must not be expanded and stalemate has no outgoing edges. An automatic-draw-aware
variant must represent all relevant known history and stop at automatic draws;
proof and handling of unknown history still require careful specification.

The independent C++ experimental `movement_mate_reachability` implements a
budgeted breadth-first search of this movement-only graph. It retains raw EP,
uses complete FEN-derived identities, and produces a legal-move witness. It
ignores clocks, repetition, dead-position termination and claims: therefore a
movement-only **NoMate** is a sufficient negative certificate, while a
**MateFound** witness is not necessarily realizable before an automatic draw.
**Unknown** on exhaustion is not a classification. The max-position budget
bounds vertices and asymptotic work/memory but a caller must choose a practical
limit; traversal is not appropriate at every search node. The proof is
conditional on the legality of the move generator and correct serialization;
it is not a proof of this code's correctness. The probe is not connected to
normal engine search or UCI.

## Evidence and open work

A python-chess 1.11.2 movement-only BFS independently enumerated 7,225 states
from a forced rook capture to KvK and 436,665 from a promotion trap, each with
zero checkmates; corresponding C++ tests match the counts. Count equality is
not a full edge-by-edge proof. A mate-in-one witness is replayed using legal
moves; a one-state budget returns unknown for both a mating and a locked pawn
position. Tests do not establish general correctness. The Python reproduction
is `scripts/reference_reachability.py`; on the measured machine its promotion
case took about 110 seconds. Worst-case state and memory requirements are
astronomical, and a budget is essential in practice. No full locked-pawn graph,
complete seven-piece or whole-board verification was conducted.

Remaining: settle the governing FIDE semantics and incomplete history contract;
implement a general operational detector without classifying unknown as dead;
prove its termination and results for the declared full domain; independently
verify transitions, exact-state closure, both sides' mate witnesses and
negative certificates; test locked material, promotions, castling, en passant,
repetition and rule-75 interactions; measure worst-case resources and integrate
without damaging UCI responsiveness. A bounded probe alone cannot satisfy this.
