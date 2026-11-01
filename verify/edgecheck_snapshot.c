/* edgecheck.c -- dependency-free bounded probabilistic model checker.
 *
 * mars-rover-edge-checker, exp1 (hackathon window 2026-10-30).
 * Plain C99, IEEE double, libc only. All memory is allocated at load time;
 * the checking loops allocate nothing.
 *
 * Front end A (explicit):  PRISM / PRISM-games `-exportmodel` files.
 *   edgecheck explicit MODEL.tra MODEL.lab "<spec>" [--players p0,p1]
 *   spec := [<<player>>]Pmax|Pmin  F|G  [<=k]  [!]label
 *   e.g. "Pmax F unsafe", "Pmin G !unsafe", "Pmax F<=20 unsafe",
 *        "<<defender>>Pmin F unsafe"
 *
 * Front end B (terrain):  builds the rover terrain MDP from a class map.
 *   edgecheck terrain MAP.txt PARAMS.csv K M [--reps N] [--json]
 *   prints, for the start state: Pmin/Pmax F<=K fail, Pmin/Pmax F fail,
 *   and P(F<=K fail | arc) for all 3^M arcs (first M steering choices
 *   fixed, the remaining K-M chosen to minimise failure).
 *
 * Engine: x_0 = 1_T ; x_{j+1}(s) = 1_T(s) ? 1 : opt_c sum_t P(s,c,t) x_j(t).
 * Bounded F<=k = exactly k sweeps. Unbounded F = sweep until the largest
 * change is 0 (exact on acyclic models) or < 1e-12, cap 1e6 sweeps.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ------------------------------------------------------------ model */
typedef struct {
    int n, nch, ntr;          /* states, choices, transitions            */
    int *ch_start;            /* n+1   : choices of state s              */
    int *tr_start;            /* nch+1 : transitions of choice c         */
    int *dst;                 /* ntr                                     */
    double *p;                /* ntr                                     */
    int *player;              /* n     : owner (SMG), 0 for MDP          */
    int init;
    unsigned char *tgt;       /* n     : target set of the current query */
    double *x, *y;            /* n     : value vectors                   */
} Model;

static void *xmalloc(size_t n) { void *q = calloc(1, n ? n : 1); if (!q) { fprintf(stderr, "out of memory\n"); exit(2); } return q; }

static void model_alloc(Model *m, int n, int nch, int ntr) {
    m->n = n; m->nch = nch; m->ntr = ntr;
    m->ch_start = xmalloc(sizeof(int) * (n + 1));
    m->tr_start = xmalloc(sizeof(int) * (nch + 1));
    m->dst = xmalloc(sizeof(int) * ntr);
    m->p = xmalloc(sizeof(double) * ntr);
    m->player = xmalloc(sizeof(int) * n);
    m->tgt = xmalloc(n);
    m->x = xmalloc(sizeof(double) * n);
    m->y = xmalloc(sizeof(double) * n);
    m->init = 0;
}

/* opt for state s: +1 max, -1 min.  mode: for MDP all states share opt;
 * for SMG the coalition's states get `copt`, the others the opposite.   */
typedef struct { int is_game, coalition, copt; } Opt;

static inline int opt_of(const Model *m, const Opt *o, int s) {
    if (!o->is_game) return o->copt;
    return m->player[s] == o->coalition ? o->copt : -o->copt;
}

/* one Bellman sweep y <- B(x); returns max |y - x| */
static double sweep(const Model *m, const Opt *o, const double *x, double *y) {
    double delta = 0.0;
    for (int s = 0; s < m->n; s++) {
        double v;
        if (m->tgt[s]) v = 1.0;
        else {
            int o_s = opt_of(m, o, s);
            v = (o_s > 0) ? -1.0 : 2.0;
            for (int c = m->ch_start[s]; c < m->ch_start[s + 1]; c++) {
                double acc = 0.0;
                for (int t = m->tr_start[c]; t < m->tr_start[c + 1]; t++) acc += m->p[t] * x[m->dst[t]];
                if (o_s > 0 ? acc > v : acc < v) v = acc;
            }
            if (m->ch_start[s] == m->ch_start[s + 1]) v = 0.0;   /* deadlock: never reaches */
        }
        double d = fabs(v - x[s]); if (d > delta) delta = d;
        y[s] = v;
    }
    return delta;
}

/* P^{opt}[F<=k T] (k < 0 : unbounded). result in m->x; returns sweeps done */
static long reach(Model *m, const Opt *o, long k, int *exact) {
    for (int s = 0; s < m->n; s++) m->x[s] = m->tgt[s] ? 1.0 : 0.0;
    long j = 0; *exact = 1;
    long cap = k >= 0 ? k : 1000000L;
    while (j < cap) {
        double d = sweep(m, o, m->x, m->y);
        double *t = m->x; m->x = m->y; m->y = t; j++;
        if (k < 0) {
            if (d == 0.0) break;
            if (d < 1e-12) { *exact = 0; break; }
        }
    }
    if (k < 0 && j == cap) *exact = -1;
    return j;
}

/* ---------------------------------------------- front end A: explicit */
static int nlabels; static char labname[64][64];

static void load_tra(Model *m, const char *path) {
    FILE *f = fopen(path, "r"); if (!f) { perror(path); exit(2); }
    char line[512]; int n, np = 0, nch, ntr;
    if (!fgets(line, sizeof line, f)) { fprintf(stderr, "empty %s\n", path); exit(2); }
    if (strchr(line, ':')) { if (sscanf(line, "%d:%d %d %d", &n, &np, &nch, &ntr) != 4) exit(3); }
    else if (sscanf(line, "%d %d %d", &n, &nch, &ntr) != 3) { fprintf(stderr, "bad header\n"); exit(3); }
    model_alloc(m, n, nch, ntr);
    int last_s = -1, last_c = -1, ci = -1, ti = 0;
    for (int s = 0; s <= n; s++) m->ch_start[s] = -1;
    while (fgets(line, sizeof line, f)) {
        int s, pl = 0, c, d; double pr; char *q = line;
        s = (int)strtol(q, &q, 10);
        if (*q == ':') { q++; pl = (int)strtol(q, &q, 10); }
        c = (int)strtol(q, &q, 10); d = (int)strtol(q, &q, 10); pr = strtod(q, &q);
        if (s < last_s || (s == last_s && c < last_c)) { fprintf(stderr, "unsorted .tra\n"); exit(3); }
        if (s != last_s || c != last_c) {
            ci++;
            if (s != last_s) { for (int u = last_s + 1; u <= s; u++) m->ch_start[u] = ci; }
            m->tr_start[ci] = ti; last_s = s; last_c = c;
        }
        m->player[s] = pl; m->dst[ti] = d; m->p[ti] = pr; ti++;
    }
    fclose(f);
    for (int u = last_s + 1; u <= n; u++) m->ch_start[u] = ci + 1;
    m->tr_start[ci + 1] = ti;
    if (ci + 1 != nch || ti != ntr) { fprintf(stderr, "count mismatch: %d/%d choices %d/%d transitions\n", ci + 1, nch, ti, ntr); exit(3); }
}

/* returns label index; fills a membership vector if want >= 0 */
static void load_lab(Model *m, const char *path, int want, unsigned char *mem) {
    FILE *f = fopen(path, "r"); if (!f) { perror(path); exit(2); }
    char line[1 << 16];
    if (!fgets(line, sizeof line, f)) exit(3);
    nlabels = 0;
    for (char *q = line; *q; ) {           /* 0="init" 1="deadlock" ... */
        int i = (int)strtol(q, &q, 10);
        char *a = strchr(q, '"'); if (!a) break; char *b = strchr(a + 1, '"');
        int L = (int)(b - a - 1); if (L > 63) L = 63;
        memcpy(labname[i], a + 1, L); labname[i][L] = 0; if (i + 1 > nlabels) nlabels = i + 1;
        q = b + 1;
    }
    if (mem) memset(mem, 0, m->n);
    int init_idx = -1; for (int i = 0; i < nlabels; i++) if (!strcmp(labname[i], "init")) init_idx = i;
    while (fgets(line, sizeof line, f)) {
        char *q = line; int s = (int)strtol(q, &q, 10); if (*q == ':') q++;
        while (*q && *q != '\n') {
            char *e; long l = strtol(q, &e, 10); if (e == q) break; q = e;
            if (l == init_idx) m->init = s;
            if (mem && l == want) mem[s] = 1;
        }
    }
    fclose(f);
}

static int label_index(const char *name) {
    for (int i = 0; i < nlabels; i++) if (!strcmp(labname[i], name)) return i;
    return -1;
}

static int run_explicit(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: edgecheck explicit M.tra M.lab \"spec\" [--players a,b]\n"); return 1; }
    char players[2][64] = {"", ""};
    for (int i = 5; i < argc; i++) if (!strcmp(argv[i], "--players") && i + 1 < argc) {
        char *c = strchr(argv[i + 1], ','); if (c) { *c = 0; strncpy(players[0], argv[i + 1], 63); strncpy(players[1], c + 1, 63); }
    }
    Model m; load_tra(&m, argv[2]);
    /* parse spec */
    char spec[256]; strncpy(spec, argv[4], 255); spec[255] = 0;
    Opt o = {0, 0, 1}; char *q = spec;
    if (!strncmp(q, "<<", 2)) {
        char *e = strstr(q, ">>"); *e = 0; o.is_game = 1; o.coalition = -1;
        for (int i = 0; i < 2; i++) if (!strcmp(players[i], q + 2)) o.coalition = i;
        if (o.coalition < 0) { fprintf(stderr, "unknown player %s (use --players)\n", q + 2); return 1; }
        q = e + 2;
    }
    int is_max; if (!strncmp(q, "Pmax", 4)) is_max = 1; else if (!strncmp(q, "Pmin", 4)) is_max = 0; else { fprintf(stderr, "spec must start with Pmax/Pmin\n"); return 1; }
    q += 4; while (*q == ' ') q++;
    char op = *q++; long k = -1;
    if (!strncmp(q, "<=", 2)) { q += 2; k = strtol(q, &q, 10); }
    while (*q == ' ') q++;
    int neg = 0; if (*q == '!') { neg = 1; q++; }
    if (op == 'G' && !neg) { fprintf(stderr, "G supports only G !label\n"); return 1; }
    if (op == 'F' && neg) { fprintf(stderr, "F supports only F label\n"); return 1; }
    load_lab(&m, argv[3], -1, NULL);
    int li = label_index(q); if (li < 0) { fprintf(stderr, "unknown label %s\n", q); return 1; }
    load_lab(&m, argv[3], li, m.tgt);
    /* F: opt as written. G !L: P^{opt}[G !L] = 1 - P^{-opt}[F L] */
    o.copt = (op == 'F') ? (is_max ? 1 : -1) : (is_max ? -1 : 1);
    int exact; struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    long sw = reach(&m, &o, k, &exact);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double v = m.x[m.init]; if (op == 'G') v = 1.0 - v;
    double us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;
    printf("value=%.17g sweeps=%ld stop=%s states=%d choices=%d transitions=%d check_us=%.1f\n",
           v, sw, k >= 0 ? "bounded" : (exact == 1 ? "exact" : exact == 0 ? "eps1e-12" : "cap"),
           m.n, m.nch, m.ntr, us);
    return 0;
}

/* ------------------------------------------------ front end B: terrain */
enum { CL_BED, CL_SOIL, CL_SAND, CL_UNK, CL_ROCK, NCLASS };
static const char CLCH[NCLASS] = {'b', 'o', 's', 'u', 'r'};
static const char *CLNAME[NCLASS] = {"bedrock", "soil", "sand", "unknown", "rock"};

typedef struct {
    int R, C; unsigned char *cls;      /* R*C, row 0 = nearest band */
    double slip[NCLASS], sink[NCLASS];
    /* state layout: grid r*C+c (0..R*C-1), START, COLL, BLIND, STUCK, THRU */
    int START, COLL, BLIND, STUCK, THRU, n;
    int start_col;
} Terrain;

static int class_of_char(char ch) { for (int i = 0; i < NCLASS; i++) if (CLCH[i] == ch) return i; return -1; }

static void load_terrain(Terrain *T, const char *map, const char *params) {
    FILE *f = fopen(map, "r"); if (!f) { perror(map); exit(2); }
    if (fscanf(f, "%d %d", &T->R, &T->C) != 2) { fprintf(stderr, "bad map header\n"); exit(3); }
    T->cls = xmalloc(T->R * T->C);
    char row[4096];
    for (int r = 0; r < T->R; r++) {        /* file lists far row first, as an image */
        if (fscanf(f, "%4095s", row) != 1 || (int)strlen(row) != T->C) { fprintf(stderr, "bad map row %d\n", r); exit(3); }
        for (int c = 0; c < T->C; c++) {
            int k = class_of_char(row[c]); if (k < 0) { fprintf(stderr, "bad class '%c'\n", row[c]); exit(3); }
            T->cls[(T->R - 1 - r) * T->C + c] = (unsigned char)k;
        }
    }
    fclose(f);
    for (int i = 0; i < NCLASS; i++) T->slip[i] = T->sink[i] = -1;
    f = fopen(params, "r"); if (!f) { perror(params); exit(2); }
    char line[512]; if (!fgets(line, sizeof line, f)) exit(3);        /* header */
    while (fgets(line, sizeof line, f)) {
        char name[64]; double sl, sk;
        if (sscanf(line, "%63[^,],%lf,%lf", name, &sl, &sk) != 3) continue;
        for (int i = 0; i < NCLASS; i++) if (!strcmp(name, CLNAME[i])) { T->slip[i] = sl; T->sink[i] = sk; }
    }
    fclose(f);
    for (int i = 0; i < NCLASS; i++) if (i != CL_ROCK && (T->slip[i] < 0 || T->sink[i] < 0)) { fprintf(stderr, "missing params for %s\n", CLNAME[i]); exit(3); }
    int g = T->R * T->C;
    T->START = g; T->COLL = g + 1; T->BLIND = g + 2; T->STUCK = g + 3; T->THRU = g + 4; T->n = g + 5;
    T->start_col = T->C / 2;
}

/* where a rover entering cell (r,c) ends up, landing only (no sink): */
static int land(const Terrain *T, int r, int c) {
    if (r >= T->R) return T->THRU;
    if (c < 0 || c >= T->C) return T->BLIND;
    if (T->cls[r * T->C + c] == CL_ROCK) return T->COLL;
    return r * T->C + c;
}

/* Build the terrain MDP into m (allocated once by the caller's sizes).
 * choice order per grid/start state: L, S, R  (steer -1, 0, +1).      */
static void build_terrain(const Terrain *T, Model *m) {
    int ci = 0, ti = 0;
    for (int s = 0; s < T->n; s++) {
        m->ch_start[s] = ci; m->player[s] = 0;
        int r, c;
        if (s < T->R * T->C) { r = s / T->C; c = s % T->C; }
        else if (s == T->START) { r = -1; c = T->start_col; }
        else { /* absorbing: one self-loop */
            m->tr_start[ci] = ti; m->dst[ti] = s; m->p[ti] = 1.0; ti++; ci++; continue;
        }
        for (int d = -1; d <= 1; d++) {
            m->tr_start[ci] = ti;
            int tr = r + 1, tc = c + d;
            int base = land(T, tr, tc);
            if (base == T->THRU || base == T->BLIND || base == T->COLL) {
                m->dst[ti] = base; m->p[ti] = 1.0; ti++;
            } else {
                int k = T->cls[tr * T->C + tc];
                double sk = T->sink[k], sl = T->slip[k], ok = 1.0 - sk - sl;
                if (ok > 0) { m->dst[ti] = base; m->p[ti] = ok; ti++; }
                if (sk > 0) { m->dst[ti] = T->STUCK; m->p[ti] = sk; ti++; }
                if (sl > 0) {
                    if (d != 0) { m->dst[ti] = land(T, tr, tc + d); m->p[ti] = sl; ti++; }
                    else {
                        m->dst[ti] = land(T, tr, tc - 1); m->p[ti] = sl / 2; ti++;
                        m->dst[ti] = land(T, tr, tc + 1); m->p[ti] = sl / 2; ti++;
                    }
                }
            }
            ci++;
        }
    }
    m->ch_start[T->n] = ci; m->tr_start[ci] = ti;
    m->nch = ci; m->ntr = ti; m->init = T->START;
}

/* per-arc values: first M choices fixed (by time), then K-M min sweeps.
 * Needs scratch vector z (n). Writes 3^M values into out.               */
static void arc_values(Model *m, const Terrain *T, int K, int M, double *out, double *z, double *base) {
    Opt omin = {0, 0, -1}; int exact;
    reach(m, &omin, K - M, &exact);                  /* continuation value */
    memcpy(base, m->x, sizeof(double) * m->n);
    int narcs = 1; for (int i = 0; i < M; i++) narcs *= 3;
    for (int a = 0; a < narcs; a++) {
        int steer[16]; int code = a;
        for (int i = M - 1; i >= 0; i--) { steer[i] = code % 3; code /= 3; }   /* digit 0..2 = L,S,R */
        memcpy(m->x, base, sizeof(double) * m->n);
        for (int i = M - 1; i >= 0; i--) {           /* backward over the fixed steps */
            for (int s = 0; s < m->n; s++) {
                if (m->tgt[s]) { z[s] = 1.0; continue; }
                int nc = m->ch_start[s + 1] - m->ch_start[s];
                int c = m->ch_start[s] + (nc == 3 ? steer[i] : 0);
                double acc = 0.0;
                for (int t = m->tr_start[c]; t < m->tr_start[c + 1]; t++) acc += m->p[t] * m->x[m->dst[t]];
                z[s] = acc;
            }
            memcpy(m->x, z, sizeof(double) * m->n);
        }
        out[a] = m->x[T->START];
    }
}

static int run_terrain(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: edgecheck terrain MAP PARAMS K M [--reps N] [--noblind]\n"); return 1; }
    int K = atoi(argv[4]), M = atoi(argv[5]), reps = 1, noblind = 0;
    for (int i = 6; i < argc; i++) {
        if (!strcmp(argv[i], "--reps") && i + 1 < argc) reps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--noblind")) noblind = 1;
    }
    if (M < 0 || M > 12 || K < M) { fprintf(stderr, "need 0 <= M <= K, M <= 12\n"); return 1; }
    Terrain T; load_terrain(&T, argv[2], argv[3]);
    Model m; int nmax = T.n, chmax = T.n * 3, trmax = T.n * 3 * 4;
    model_alloc(&m, nmax, chmax, trmax);
    int narcs = 1; for (int i = 0; i < M; i++) narcs *= 3;
    double *arcs = xmalloc(sizeof(double) * narcs), *z = xmalloc(sizeof(double) * nmax), *base = xmalloc(sizeof(double) * nmax);
    double best_build = 1e30, best_all = 1e30; double *lat = xmalloc(sizeof(double) * reps), *cpu = xmalloc(sizeof(double) * reps);
    double pminK = 0, pmaxK = 0, pminU = 0, pmaxU = 0; int exU1 = 0, exU2 = 0;
    for (int rep = 0; rep < reps; rep++) {
        struct timespec t0, t1, t2, c0, c2;
        clock_gettime(CLOCK_THREAD_CPUTIME_ID, &c0);
        clock_gettime(CLOCK_MONOTONIC, &t0);
        build_terrain(&T, &m);                       /* per call: model from the map */
        memset(m.tgt, 0, m.n);
        m.tgt[T.COLL] = 1; m.tgt[T.STUCK] = 1; if (!noblind) m.tgt[T.BLIND] = 1;
        clock_gettime(CLOCK_MONOTONIC, &t1);
        arc_values(&m, &T, K, M, arcs, z, base);    /* the on-board check: every arc */
        clock_gettime(CLOCK_MONOTONIC, &t2);
        clock_gettime(CLOCK_THREAD_CPUTIME_ID, &c2);
        cpu[rep] = (c2.tv_sec - c0.tv_sec) * 1e6 + (c2.tv_nsec - c0.tv_nsec) / 1e3;
        double b = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;
        double a = (t2.tv_sec - t0.tv_sec) * 1e6 + (t2.tv_nsec - t0.tv_nsec) / 1e3;
        if (b < best_build) best_build = b; if (a < best_all) best_all = a; lat[rep] = a;
    }
    Opt omin = {0, 0, -1}, omax = {0, 0, 1}; int ex;
    reach(&m, &omin, K, &ex); pminK = m.x[T.START];
    reach(&m, &omax, K, &ex); pmaxK = m.x[T.START];
    reach(&m, &omin, -1, &exU1); pminU = m.x[T.START];
    reach(&m, &omax, -1, &exU2); pmaxU = m.x[T.START];
    /* median latency */
    for (int i = 1; i < reps; i++) { double v = lat[i]; int j = i - 1; while (j >= 0 && lat[j] > v) { lat[j + 1] = lat[j]; j--; } lat[j + 1] = v; }
    double med = lat[reps / 2], q1 = lat[reps / 4], q3 = lat[(3 * reps) / 4];
    for (int i = 1; i < reps; i++) { double v = cpu[i]; int j = i - 1; while (j >= 0 && cpu[j] > v) { cpu[j + 1] = cpu[j]; j--; } cpu[j + 1] = v; }
    double cmed = cpu[reps / 2], cq1 = cpu[reps / 4], cq3 = cpu[(3 * reps) / 4];
    printf("{\"R\":%d,\"C\":%d,\"K\":%d,\"M\":%d,\"states\":%d,\"choices\":%d,\"transitions\":%d,"
           "\"blind_is_fail\":%s,\"pmin_k\":%.17g,\"pmax_k\":%.17g,\"pmin_inf\":%.17g,\"pmax_inf\":%.17g,"
           "\"inf_stop\":\"%s/%s\",\"reps\":%d,\"lat_us_median\":%.2f,\"lat_us_q1\":%.2f,\"lat_us_q3\":%.2f,"
           "\"cpu_us_median\":%.2f,\"cpu_us_q1\":%.2f,\"cpu_us_q3\":%.2f,"
           "\"build_us_min\":%.2f,\"arcs\":[",
           T.R, T.C, K, M, m.n, m.nch, m.ntr, noblind ? "false" : "true", pminK, pmaxK, pminU, pmaxU,
           exU1 == 1 ? "exact" : "eps", exU2 == 1 ? "exact" : "eps", reps, med, q1, q3, cmed, cq1, cq3, best_build);
    for (int a = 0; a < narcs; a++) printf("%s%.17g", a ? "," : "", arcs[a]);
    printf("]}\n");
    return 0;
}

#ifndef EDGECHECK_NO_MAIN
int main(int argc, char **argv) {
    if (argc >= 2 && !strcmp(argv[1], "explicit")) return run_explicit(argc, argv);
    if (argc >= 2 && !strcmp(argv[1], "terrain")) return run_terrain(argc, argv);
    fprintf(stderr, "usage: edgecheck explicit|terrain ...\n");
    return 1;
}
#endif
