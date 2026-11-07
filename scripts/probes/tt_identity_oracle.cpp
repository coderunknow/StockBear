// exp-0064 INDEPENDENT MODEL ORACLE for the main-TT identity contract.
// Randomised store/probe sequences are checked against a reference model:
//   match iff key, rule50 and historyContext are equal AND
//            (agnostic OR the stored extension budget equals the requested one)
// The model is written from the specification, not from the implementation.
#include "chess/position.hpp"
#include "chess/zobrist.hpp"
#include "search/search.hpp"
#include "search/transposition_table.hpp"
#include <cstdio>
#include <random>
#include <vector>
using namespace stockbear;

int main(int argc, char** argv) {
    const int cases = argc > 1 ? std::atoi(argv[1]) : 20000;
    const std::uint64_t seed = argc > 2 ? std::strtoull(argv[2], nullptr, 10) : 2026110664ULL;
    Zobrist::init();
    std::mt19937_64 rng(seed);
    long long checked = 0, mismatch = 0, agnosticHits = 0, shippedHits = 0;
    for (int c = 0; c < cases; ++c) {
        TranspositionTable tt(1);
        // A small population of synthetic identities sharing some fields.
        struct Id { Key key; std::uint64_t rule50; Key ctx; int ext; };
        std::vector<Id> ids;
        const Key baseKey = rng(), baseCtx = rng();
        for (int i = 0; i < 6; ++i) {
            Id id;
            // i = 0..3 deliberately share the FULL position identity
            // (key, rule50, context) and differ ONLY in the extension budget:
            // this is exactly the reuse the candidate recovers. i = 4,5 are
            // unrelated identities that must never be served.
            if (i < 4) { id.key = baseKey; id.rule50 = 0; id.ctx = baseCtx; id.ext = i; }
            else {
                id.key = Key(rng());
                id.rule50 = (i % 2 == 0) ? 0 : 4;
                id.ctx = Key(rng());
                id.ext = int(rng() % 4);
            }
            ids.push_back(id);
            tt.store(id.key, id.rule50, id.ctx, tt_identity_extensions(false, id.ext),
                     MOVE_NONE, 100 + i, 8, Bound::Exact, 0, VALUE_NONE);
        }
        // Agnostic table: every store uses argument 0, exactly as the search does.
        TranspositionTable ag(1);
        for (size_t i = 0; i < ids.size(); ++i)
            ag.store(ids[i].key, ids[i].rule50, ids[i].ctx,
                     tt_identity_extensions(true, ids[i].ext),
                     MOVE_NONE, 100 + int(i), 8, Bound::Exact, 0, VALUE_NONE);
        for (const Id& q : ids) {
            // Shipped model: the exact tuple must match.
            bool modelShipped = false;
            for (const Id& s : ids)
                if (s.key == q.key && s.rule50 == q.rule50 && s.ctx == q.ctx && s.ext == q.ext)
                    modelShipped = true;
            const bool gotShipped =
                tt.probe(q.key, q.rule50, q.ctx, tt_identity_extensions(false, q.ext)) != nullptr;
            // The bucket holds 2 slots, so a model "true" can be evicted; only a
            // model "false" that returns an entry is a hard contract violation.
            if (!modelShipped && gotShipped) ++mismatch;
            if (gotShipped) ++shippedHits;
            ++checked;
            bool modelAgnostic = false;
            for (const Id& s : ids)
                if (s.key == q.key && s.rule50 == q.rule50 && s.ctx == q.ctx)
                    modelAgnostic = true;
            const bool gotAgnostic =
                ag.probe(q.key, q.rule50, q.ctx, tt_identity_extensions(true, q.ext)) != nullptr;
            if (!modelAgnostic && gotAgnostic) ++mismatch;
            if (gotAgnostic) ++agnosticHits;
            ++checked;
            // Cross-field isolation: changing ONLY the context or ONLY rule50
            // must never be served by the agnostic table.
            if (ag.probe(q.key, q.rule50, q.ctx ^ Key(0xA5A5A5A5DEADBEEFULL),
                         tt_identity_extensions(true, q.ext)) != nullptr) ++mismatch;
            if (ag.probe(q.key, q.rule50 + 1, q.ctx,
                         tt_identity_extensions(true, q.ext)) != nullptr) ++mismatch;
            checked += 2;
            // CROSS-BUDGET REUSE: request a budget that was NEVER stored for
            // this identity. The shipped identity must miss; the agnostic
            // identity must still find the position. This is the mechanism.
            const int unseen = 7;
            const bool shippedCross =
                tt.probe(q.key, q.rule50, q.ctx, tt_identity_extensions(false, unseen)) != nullptr;
            const bool agnosticCross =
                ag.probe(q.key, q.rule50, q.ctx, tt_identity_extensions(true, unseen)) != nullptr;
            bool storedIdentity = false;
            for (const Id& s : ids)
                if (s.key == q.key && s.rule50 == q.rule50 && s.ctx == q.ctx) storedIdentity = true;
            if (storedIdentity && shippedCross) ++mismatch;      // must NOT match
            if (storedIdentity && !agnosticCross) ++mismatch;    // MUST match
            if (!storedIdentity && agnosticCross) ++mismatch;
            if (agnosticCross) ++agnosticHits;
            if (shippedCross) ++shippedHits;
            checked += 2;
        }
    }
    std::printf("cases %d seed %llu checked %lld mismatches %lld\n",
                cases, (unsigned long long)seed, checked, mismatch);
    std::printf("shipped_hits %lld agnostic_hits %lld reuse_gain %lld\n",
                shippedHits, agnosticHits, agnosticHits - shippedHits);
    std::printf("verdict %s\n", mismatch == 0 ? "PASS" : "FAIL");
    return mismatch == 0 ? 0 : 1;
}
