/* KLEE harness: symbolic map size (1..2 x 1..2, small bound) and symbolic class per cell,
 * concrete terrain_params.csv values. KLEE explores every path of
 * build_terrain + arc_values (K=4, M=2) and reports any out-of-bounds access,
 * and asserts the CSR invariants and value range.                           */
#define EDGECHECK_NO_MAIN
#include "edgecheck_snapshot.c"  /* byte-identical copy (sha256 recorded in VERIFY.md) */
#include <klee/klee.h>
#include <assert.h>
int main(void) {
    Terrain T; int R, C;
    klee_make_symbolic(&R, sizeof R, "R"); klee_make_symbolic(&C, sizeof C, "C");
    klee_assume(R >= 1); klee_assume(R <= 2); klee_assume(C >= 1); klee_assume(C <= 2);
    T.R = R; T.C = C;
    unsigned char cls[4]; klee_make_symbolic(cls, sizeof cls, "cls");
    for (int i = 0; i < 4; i++) klee_assume(cls[i] < NCLASS);
    T.cls = cls;
    double sl[NCLASS] = {0.02, 0.05, 0.15, 0.15, 0}, sk[NCLASS] = {0.0, 0.002, 0.02, 0.02, 0};
    for (int i = 0; i < NCLASS; i++) { T.slip[i] = sl[i]; T.sink[i] = sk[i]; }
    int g = R * C;
    T.START = g; T.COLL = g + 1; T.BLIND = g + 2; T.STUCK = g + 3; T.THRU = g + 4; T.n = g + 5; T.start_col = C / 2;
    Model m; model_alloc(&m, 9, 27, 108);   /* load-time allocation at the 2x2 maximum */
    m.n = T.n;
    build_terrain(&T, &m);
    assert(m.nch <= T.n * 3 && m.ntr <= T.n * 3 * 4);
    for (int s = 0; s < m.n; s++) assert(m.ch_start[s] <= m.ch_start[s + 1]);
    for (int c = 0; c < m.nch; c++) {
        double tot = 0; assert(m.tr_start[c] < m.tr_start[c + 1]);
        for (int t = m.tr_start[c]; t < m.tr_start[c + 1]; t++) { assert(m.dst[t] >= 0 && m.dst[t] < m.n); tot += m.p[t]; }
        assert(tot > 1.0 - 1e-12 && tot < 1.0 + 1e-12);
    }
    memset(m.tgt, 0, m.n); m.tgt[T.COLL] = 1; m.tgt[T.STUCK] = 1; m.tgt[T.BLIND] = 1;
    double arcs[9], z[16], base[16];
    arc_values(&m, &T, 4, 2, arcs, z, base);
    for (int a = 0; a < 9; a++) assert(arcs[a] >= 0.0 && arcs[a] <= 1.0 + 1e-12);
    return 0;
}
