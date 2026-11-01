/* Exhaustive enumeration: EVERY class assignment of EVERY map up to 3x3
 * (5 classes per cell), assumed parameters from terrain_params.csv, horizons
 * (K,M) in {(2,1),(4,2),(8,3)}, built with -fsanitize=address,undefined.
 * Asserts: model fits the load-time allocation; CSR monotone; destinations in
 * range; every choice's probabilities sum to 1 +- 1e-12 and are > 0; every arc
 * value and every closed-loop bounded value in [0, 1]; unbounded Pmin <= Pmax. */
#define EDGECHECK_NO_MAIN
#include "../checker/edgecheck.c"
#include <assert.h>
int main(void) {
    double sl[NCLASS] = {0.02, 0.05, 0.15, 0.15, 0}, sk[NCLASS] = {0.0, 0.002, 0.02, 0.02, 0};
    const int KM[3][2] = {{2, 1}, {4, 2}, {8, 3}};
    Model m; model_alloc(&m, 14, 42, 168);              /* 3x3 + 5 maximum */
    double arcs[27], z[14], base[14];
    unsigned char cls[9]; long maps = 0, checks = 0;
    for (int R = 1; R <= 3; R++) for (int C = 1; C <= 3; C++) {
        long total = 1; for (int i = 0; i < R * C; i++) total *= NCLASS;
        for (long code = 0; code < total; code++) {
            long x = code; for (int i = 0; i < R * C; i++) { cls[i] = (unsigned char)(x % NCLASS); x /= NCLASS; }
            Terrain T; T.R = R; T.C = C; T.cls = cls;
            for (int i = 0; i < NCLASS; i++) { T.slip[i] = sl[i]; T.sink[i] = sk[i]; }
            int g = R * C; T.START = g; T.COLL = g + 1; T.BLIND = g + 2; T.STUCK = g + 3; T.THRU = g + 4; T.n = g + 5; T.start_col = C / 2;
            m.n = T.n; build_terrain(&T, &m);
            assert(m.nch <= 42 && m.ntr <= 168);
            for (int s = 0; s < m.n; s++) assert(m.ch_start[s] < m.ch_start[s + 1]);
            for (int c = 0; c < m.nch; c++) {
                double tot = 0; assert(m.tr_start[c] < m.tr_start[c + 1]);
                for (int t = m.tr_start[c]; t < m.tr_start[c + 1]; t++) { assert(m.dst[t] >= 0 && m.dst[t] < m.n); assert(m.p[t] > 0); tot += m.p[t]; }
                assert(fabs(tot - 1.0) < 1e-12);
            }
            memset(m.tgt, 0, m.n); m.tgt[T.COLL] = m.tgt[T.STUCK] = m.tgt[T.BLIND] = 1;
            for (int q = 0; q < 3; q++) {
                int K = KM[q][0], M = KM[q][1], na = 1; for (int i = 0; i < M; i++) na *= 3;
                arc_values(&m, &T, K, M, arcs, z, base);
                for (int a = 0; a < na; a++) assert(arcs[a] >= 0.0 && arcs[a] <= 1.0 + 1e-12);
                Opt lo = {0, 0, -1}, hi = {0, 0, 1}; int ex;
                reach(&m, &lo, K, &ex); double pmin = m.x[T.START];
                for (int s = 0; s < m.n; s++) assert(m.x[s] >= 0.0 && m.x[s] <= 1.0 + 1e-12);
                reach(&m, &hi, K, &ex); double pmax = m.x[T.START];
                assert(pmin <= pmax + 1e-15);
                for (int a = 0; a < na; a++) assert(arcs[a] >= pmin - 1e-15);   /* fixing a prefix can only hurt Pmin */
                checks++;
            }
            maps++;
        }
    }
    printf("exhaustive: %ld maps (all class assignments, R,C <= 3), %ld (map, K, M) checks, all assertions held\n", maps, checks);
    return 0;
}
