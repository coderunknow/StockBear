#include "test.hpp"
#include "search/transposition_table.hpp"
using namespace stockbear;
TEST(unit, ep_hash_uses_legal_not_pseudo_legal_moves) {
    Position a = test::position("k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 2");
    Position b = test::position("k3r3/8/8/3pP3/8/8/8/4K3 w - - 0 2");
    CHECK_EQ(a.key(),b.key()); // pinned pawn cannot legally capture
    Position c = test::position("7k/8/8/3pP3/4K3/8/8/8 w - d6 0 2");
    Position d = test::position("7k/8/8/3pP3/4K3/8/8/8 w - - 0 2");
    CHECK(c.key() != d.key()); // capture of checking pawn is legal
    CHECK(c.history_context() != d.history_context());
}
TEST(unit, transposition_context_clock_and_mate_scores) {
    TranspositionTable tt(1); tt.new_search();
    const Key key = 999, context = 12345;
    const int mate = VALUE_MATE - 5;
    tt.store(key, 17, context, 1, make_move(SQ_A2,SQ_A3), mate, 8, Bound::Exact, 3);
    const TTEntry* entry = tt.probe(key,17,context,1);
    CHECK(entry); CHECK_EQ(TranspositionTable::value_from_table(entry->value,3),mate);
    CHECK_EQ(TranspositionTable::value_from_table(entry->value,5),mate-2);
    CHECK(tt.probe(key,18,context,1) == nullptr);
    CHECK(tt.probe(key,17,context+1,1) == nullptr);
    CHECK(tt.probe(key,17,context,0) == nullptr);
    CHECK(tt.allocated_bytes() <= 1024*1024);
    tt.clear(); CHECK(tt.probe(key,17,context,1) == nullptr);
}
