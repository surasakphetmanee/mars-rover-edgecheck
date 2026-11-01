/* CBMC harness: terrain front end (build_terrain + arc_values + reach).
 * Nondeterministic map up to 3x3, nondeterministic class per cell,
 * nondeterministic per-class slip/sink with 0 <= slip, sink and slip+sink <= 1,
 * K <= 3, M <= 2. Checked: array bounds, pointers, overflow, NaN, and that
 * every per-arc value and every closed-loop value lies in [0, 1].           */
#define EDGECHECK_NO_MAIN
#include "../checker/edgecheck.c"
int nondet_int(void); double nondet_double(void);
int main(void) {
    Terrain T; T.R = nondet_int(); T.C = nondet_int();
    __CPROVER_assume(T.R >= 1 && T.R <= 3 && T.C >= 1 && T.C <= 3);
    T.cls = xmalloc(T.R * T.C);
    for (int i = 0; i < T.R * T.C; i++) { int k = nondet_int(); __CPROVER_assume(k >= 0 && k < NCLASS); T.cls[i] = (unsigned char)k; }
    for (int i = 0; i < NCLASS; i++) {
        double sl = nondet_double(), sk = nondet_double();
        __CPROVER_assume(sl >= 0.0 && sk >= 0.0 && sl <= 1.0 && sk <= 1.0 && sl + sk <= 1.0);
        T.slip[i] = sl; T.sink[i] = sk;
    }
    int g = T.R * T.C;
    T.START = g; T.COLL = g + 1; T.BLIND = g + 2; T.STUCK = g + 3; T.THRU = g + 4; T.n = g + 5; T.start_col = T.C / 2;
    Model m; model_alloc(&m, T.n, T.n * 3, T.n * 3 * 4);
    build_terrain(&T, &m);
    __CPROVER_assert(m.nch <= T.n * 3 && m.ntr <= T.n * 3 * 4, "model fits the load-time allocation");
    memset(m.tgt, 0, m.n); m.tgt[T.COLL] = 1; m.tgt[T.STUCK] = 1; m.tgt[T.BLIND] = 1;
    int K = nondet_int(), M = nondet_int(); __CPROVER_assume(K >= 1 && K <= 3 && M >= 0 && M <= 2 && M <= K);
    double arcs[9], z[14], base[14];
    arc_values(&m, &T, K, M, arcs, z, base);
    int narcs = 1; for (int i = 0; i < M; i++) narcs *= 3;
    for (int a = 0; a < narcs; a++) __CPROVER_assert(arcs[a] >= 0.0 && arcs[a] <= 1.0 + 1e-9, "arc value in [0,1]");
    Opt o = {0, 0, nondet_int() > 0 ? 1 : -1}; int ex;
    reach(&m, &o, K, &ex);
    for (int s = 0; s < m.n; s++) __CPROVER_assert(m.x[s] >= 0.0 && m.x[s] <= 1.0 + 1e-9, "bounded value in [0,1]");
    return 0;
}
