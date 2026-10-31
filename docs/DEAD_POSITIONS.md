# FIDE dead positions (Article 5.2.2)

This document specifies StockBear's general dead-position detector
(`src/chess/dead_position.{hpp,cpp}`), its correctness argument, the evidence
that it works, and its documented resource limits. It is the document the
dev2 release gate is judged against, so it states plainly what is proved and
what is merely bounded.

## 1. The rule and its formalisation

> **Article 5.2.2** — The game is drawn when a position has arisen in which
> neither player can checkmate the opponent's king with any series of legal
> moves. The game is said to end in a 'dead position'.

For a position `P` define

* `mate_reachable(P)` — there exists a finite sequence of legal moves starting
  at `P` that ends in a position where the side to move is checkmated;
* `dead(P) := not mate_reachable(P)`.

`P` is dead exactly when no such sequence exists for either side, because any
sequence ending in checkmate has exactly one mating side. The implementation
therefore decides one question, `mate_reachable`, and negates it.

Four consequences drive the design:

1. **Deadness is a property of the position, not of the game history.** The
   state is the piece placement, the side to move, the castling rights and the
   en-passant right. Earlier positions cannot change which mates are reachable,
   so a FEN is sufficient input. (Repetition claims are the opposite: they need
   history, which is why the two are handled by different code.)
2. **Move counters are irrelevant.** Article 5.2.2 quantifies over series of
   legal moves with no move-count limit, so the fifty-move and seventy-five-move
   rules are *not* part of the definition. A detector that consulted the
   halfmove counter would answer a different question.
3. **Deadness is closed under legal moves.** Legal moves are not reversible
   (captures, pawn pushes and castling cannot be undone), but the closure follows
   differently: any legal continuation from a successor `B` of `A` can be
   prefixed with the move `A -> B`, so `mate_reachable(B)` implies
   `mate_reachable(A)`, hence `dead(A)` implies `dead(B)`. The unit test
   `locked_pawn_structure_is_dead` verifies the property over every successor of
   a locked position.
4. **Checkmate and stalemate are decided by other articles.** Articles 5.1.1
   and 5.2.1 terminate such positions before 5.2.2 can apply. The detector
   reports them as `terminal` and never claims them for 5.2.2.

## 2. Why no material table can satisfy the requirement

The classical "insufficient material" list is a *subset* of the dead positions,
and the natural generalisations of it are wrong in both directions. Every row
below is a corpus case (`scripts/dead_position_corpus.py`) whose verdict the
detector proves and the reference implementation confirms:

| Position | Verdict | Reason |
|---|---|---|
| bare kings, `KB` v `K`, `KN` v `K` | dead | a lone minor can never mate: the mated king always has a flight square |
| bishops only, all on one square colour | dead | a bishop cannot attack the opposite-coloured flight squares and cannot occupy them either |
| two knights v bare king | **alive** | with cooperation the defender's king can be driven into a corner and mated by two knights |
| `KB` v `KN`, `KN` v `KN` | **alive** | the defender's own knight blocks a flight square while the attacker gives a protected check |
| 14 blocked pawns plus kings | **dead** | no pawn can ever move, capture or promote; only king moves exist and kings cannot mate |
| locked pawn chains plus a bishop each | **dead** | the bishops roam freely, but the entire reachable component (152,352 distinct states, reached by 1,268,497 move applications) contains no checkmate |

The last two rows are the reason the requirement cannot be met by signatures:
they are dead with 16 and 12 pieces on the board respectively, and any
material-only rule calls them alive.

## 3. Algorithm

`analyze_dead_position(pos, limits)` runs up to four stages and returns
`Alive`, `Dead` or `Unknown`, plus the evidence it used.

**Stage 0 — terminal positions.** No legal move and in check: checkmate
(Article 5.1.1). No legal move and not in check: stalemate (Article 5.2.1).
Reported as `terminal`, excluded from the 5.2.2 question.

**Stage 1 — static proof.** `Position::insufficient_material()` proves deadness
for material that cannot mate by any legal continuation: no pawns, rooks or
queens and at most one minor piece in total, or bishops only on one square
colour. This is sound and *complete for that class*, and costs nothing; the
exhaustive tests in §6 confirm it over the whole two- and three-piece space.

**Stage 2 — short helpmate witness.** A depth-limited depth-first search in
which both sides cooperate (they may choose any legal move); a checkmate
position is a certificate that the position is alive. Moves are ordered by
checks, by reduction of the defending king's flight squares and by approach of
the pieces, so ordinary middlegames resolve in a few milliseconds.

**Stage 3 — bounded exhaustive enumeration.** A depth-first traversal of the
*complete* reachable state component: every position reachable by any legal
sequence, including captured material, promotions, and every castling-rights and
en-passant variant. Each state is identified by a 128-bit fingerprint (the
Zobrist key plus an independent mix of placement, side, castling rights and
en-passant square) held in an open-addressing set. If any member of the
component is checkmate, the position is alive and the path is returned as a
witness. If the traversal finishes without finding one, the position is
**dead — proved**, because the component is exactly the set of positions
reachable by legal play.

**Stage 4 — full-budget repeat** of Stage 3 with the caller's budget, followed
by a deeper witness pass.

## 4. Correctness argument

**A `Dead` verdict is sound.** `Dead` is returned only after Stage 1's material
proof, or after Stage 3/4 enumerated every reachable state and found no
checkmate. The enumeration is exhaustive by construction: it applies every legal
move of every visited position and skips a state only when an identical state was
already visited. Two independent 64-bit fingerprints derived from different
functions of the position identify a state, and the en-passant square is mixed in
explicitly, so a Zobrist key that ignored it cannot merge two states with
different legal-move sets. The one assumption is that no two distinct states
share a fingerprint batch; the relevant bound is the birthday bound for a whole
run, about `n^2 / 2^129` — about `2^-65` for `n = 2^32` states and about `2^-77`
at the 50,000,000-state maximum. If such a collision happened, a state could be
skipped and a reachable mate missed, which would produce a wrong `Dead` verdict.
The probability is astronomically small but not zero, which is why this document
never claims absolute certainty.

**An `Alive` verdict is never wrong.** `Alive` is returned after a checkmate
state was found inside the reachable component, in which case the witness holds
an explicit legal move sequence ending in checkmate. Two documented exceptions
exist: a *terminal* position (checkmate or stalemate) is reported as `Alive` with
a `terminal: ...` reason and **no witness**, because Articles 5.1.1 and 5.2.1
decide it; and a static material proof returns `Dead` with `exhaustiveComplete`
set and no enumeration, because that class is settled without search. Callers
must therefore not assume every `Alive` result carries a witness — check
`witness.empty()` and `reason`. The unit tests replay every witness through the
engine's own legality checks and assert that the final position is checkmate;
the CLI prints `witness_ends_in_mate`.

**No silent guessing.** Budget or depth exhaustion yields `Unknown` with a
reason, and `Unknown` is never treated as `Dead`:

* `Position::draw_status()` reports `AutomaticDeadPosition` only for a proved
  `Dead` verdict;
* the search never calls the detector — it keeps the cheap, sound, incomplete
  `insufficient_material()` predicate — so search behaviour and strength do not
  depend on the analysis cost;
* the UCI layer never claims a draw at all: a GUI or arbiter remains responsible
  for adjudicating the game, exactly as Article 5.2.2 requires in practice.

The residual risks are therefore explicit: a wrong `Dead` verdict would require
a 128-bit fingerprint collision, and a missed verdict can only occur where the
resource limit bites, in which case the answer is `Unknown`.

**Completeness.** Deciding `mate_reachable` is PSPACE-complete ("Complexity of
Retrograde and Helpmate Chess Problems: Even Cooperative Chess is Hard",
arXiv:2010.09271), so no polynomial-time complete procedure can exist. Here
"complete" can only mean *exact until resources run out*, and that is what the
procedure is: for any position, if the enumeration completes, the verdict is the
truth, and the algorithm is a decision procedure for Article 5.2.2 whose worst
case is exponential in the number of pieces — like every published helpmate
analyzer (e.g. the `deadpos` analyzer and the Chasolver retrograde solver). This
is a general algorithm, not an approximation tied to material signatures or to
tablebase ranges.

## 5. Measured performance and documented limits

Two counters are reported, because they measure different things:

* **distinct states** — the size of the reachable component (each state is
  inserted into the 128-bit visited set once);
* **positions expanded** — legal moves applied plus the root. This is what the
  `componentStates` budget limits, so it exceeds the distinct-state count
  whenever a state is entered by more than one move.

Measured with the dev2 Release build (GCC 12.2, `-O3`), one thread, on the
2-vCPU benchmark machine:

| Position | Verdict | Distinct states | Expanded | Time | Peak RSS |
|---|---|---:|---:|---:|---:|
| bare kings, `KB` v `K`, `KN` v `K`, same-colour bishops | dead | 0 (static proof) | 0 | ≤ 0.02 ms | 10 MiB |
| 14 blocked pawns (either side to move) | dead | 768 | 3,809 | 4.7–11 ms | 10 MiB |
| locked pawn chains plus bishops (either side) | dead | 152,352 | 1,268,497 | 0.44–0.75 s | 46 MiB |
| `KQ` v `K` / `KR` v `K` / `KP` v `K` | alive | 17,846 / 21,904 / 25,500 | 70,914 / 80,995 / 90,870 | 22–55 ms | 13 MiB |
| `KNN` v `K` | alive | 100,745 | 300,000 (witness pass cap) | 136–185 ms | 13 MiB |
| starting position | alive | 44,368 | 135,973 | 38–73 ms | 13 MiB |
| Kiwipete, Italian middlegame | alive | 0 (witness) | 0 | 1–5 ms | 10 MiB |
| `KB` v `KB`, opposite colours | alive | 446,393 | 4,053,677 | 1.1–1.4 s | 46 MiB |
| `KN` v `KN` | alive | 1,194,884 | 7,908,228 | 1.9–3.3 s | 146 MiB |
| a 4-piece position that exhausts the default budget | unknown | 412,666 | 3,000,000 (budget hit) | 1.6 s | 86 MiB |

The generated table for every corpus case is written by
`scripts/dead_position_corpus.py --markdown`; the committed copy is
[benchmarks/results/0.1.0-dev2/dead-positions-corpus.md](../benchmarks/results/0.1.0-dev2/dead-positions-corpus.md).
Peak RSS was measured with `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` around
a single process run, so it is the whole process, not just the visited set. In
practice the default budget of 3,000,000 expanded positions needs 85–105 MiB and
about 1.3–1.6 s, depending on how many of those expansions are distinct states.
The visited set stores two 64-bit fingerprints per slot (24 bytes with alignment)
in an open-addressing table kept below a 0.7 load factor, and the traversal frames
add a few hundred bytes per ply.

Documented limits:

* A position whose reachable component exceeds the budget (large open
  middlegames, pawnless four-piece endings at the default budget) returns
  `Unknown`. It is reported as such, never as dead.
* States are identified by 128-bit fingerprints rather than stored positions, so
  a collision is theoretically possible. A collision can hide a mate and hence
  produce a wrong `Dead` verdict; the probability is bounded by the birthday
  argument above (≈2^-77 at the 50,000,000-state maximum) but is not zero.
* The `--depth` path cap and the witness depth cap are conservative: hitting
  either produces `Unknown`.
* The detector is an adjudication and analysis tool, deliberately not on the
  search hot path. The search uses the cheap, sound, incomplete
  `insufficient_material()` subset and never declares a FIDE draw by itself.

**Verdict exceptions.** A caller must not assume every `Alive` result carries a
witness: terminal positions (checkmate, stalemate) are reported as `Alive` with a
`terminal: ...` reason and an empty witness, because Articles 5.1.1 and 5.2.1
decide them. Conversely, the impossible-material class returns `Dead` without any
enumeration (`exhaustiveComplete` is set).

## 6. Verification evidence

1. **Unit tests** (`tests/unit/test_dead_position.cpp`, CTest entry `deadpos`),
   covering
   * dead cases: bare kings, `KB` v `K`, `KN` v `K`, same-coloured bishops, one
     bishop each on one colour, 14 blocked pawns, locked pawn chains with
     bishops (both sides to move);
   * alive cases: `KNN` v `K`, opposite-coloured bishops, `KQ`, `KR`, `KP`,
     starting position, Kiwipete, an en-passant position, a castling-rights
     position;
   * witnesses replayed move by move through the legality checks;
   * the closure property over all successors of a locked position;
   * terminal positions (checkmate/stalemate) excluded from 5.2.2;
   * budget exhaustion returning `Unknown` and never `Dead`;
   * **exhaustive reduced state spaces**: all legal two-king placements with
     either side to move, and all legal three-piece placements with a bishop or
     a knight and either side to move (about 250k placements each; stalemates
     are recognised as terminal, everything else must be `Dead`);
   * static exchange evaluation against hand-computed values, including the
     losing-capture case that a mis-folded exchange sequence would report as a
     win.
2. **Independent reference** (`scripts/dead_position_reference.py`): a second,
   from-scratch implementation on top of python-chess that enumerates the same
   component with a different move generator and decides the same question. It
   compares verdicts on bare kings, `KB`/`KQ`/`KR`, a blocked e6/e7 pawn structure
   and a locked pawn structure, each in both side-to-move variants. The recorded dev2 run compared
   10 positions with 0 failures and printed `SKIP` for the two `KN` v `K` rows,
   whose component exceeds the 400,000-state reference cap (StockBear decides
   those statically, and the exhaustive three-piece sweep covers them). The CI
   job "Independent reference, statistics and dead positions" runs it against
   every build.
3. **Corpus with expected verdicts** (`scripts/dead_position_corpus.py`), also
   run in CI, which fails on any wrong verdict or broken witness.
4. **No false draw claims in the engine**: `draw_status()` is tested to report
   `AutomaticDeadPosition` only for proved cases, and an ordinary middlegame is
   verified not to be classified dead.

The recorded results of these runs are in
[the dev2 benchmark report](../benchmarks/results/0.1.0-dev2/REPORT.md).
