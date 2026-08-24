/* homodyne_rng_mex.c -- bit-exact reproduction of numpy's default_rng RNG.
 *
 * Reproduces, bit for bit, the random stream of
 *     numpy.random.default_rng(seed).standard_normal(n)
 * i.e. SeedSequence(seed) -> PCG64 (128-bit LCG, XSL-RR output) ->
 * 256-layer ziggurat standard normal (numpy random_standard_normal).
 *
 * This lets the MATLAB/Octave port of the homodyne validators run the SAME
 * noise realizations as the Python reference, so golden metrics compare
 * within tight tolerances instead of only statistically.
 *
 * Algorithms transcribed from NumPy v2.4.4 (BSD-3-Clause):
 *   numpy/random/bit_generator.pyx      (SeedSequence entropy mixing)
 *   numpy/random/src/pcg64/pcg64.{h,c}  (PCG64 seeding / next64)
 *   numpy/random/src/distributions/distributions.c (random_standard_normal)
 *   ziggurat tables: ziggurat_constants.h (verbatim copy in this directory)
 *
 * MEX API (works in GNU Octave via `mkoctfile --mex` and in MATLAB via `mex`;
 * requires a compiler with __uint128_t, e.g. gcc/clang on 64-bit):
 *   h = homodyne_rng_mex('new', seed)     new generator, returns handle (>=1)
 *   x = homodyne_rng_mex('randn', h, n)   next n standard normals (n x 1)
 *   homodyne_rng_mex('reset')             discard all generator states
 *
 * Compile:  mkoctfile --mex -O2 -ffp-contract=off homodyne_rng_mex.c
 * (-ffp-contract=off: keep FP semantics identical to the Python reference.)
 */
#include "mex.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "ziggurat_constants.h"

typedef __uint128_t u128;

typedef struct { u128 state; u128 inc; } pcg64_rng;

#define PCG_MULT ((((u128)2549297995355413924ULL) << 64) | 4865540595714422341ULL)

static inline void pcg_step(pcg64_rng *r) { r->state = r->state * PCG_MULT + r->inc; }

static inline uint64_t rotr64(uint64_t v, unsigned int rot)
{
    return (v >> rot) | (v << ((-rot) & 63u));
}

static inline uint64_t pcg_next64(pcg64_rng *r)
{
    pcg_step(r);
    return rotr64((uint64_t)(r->state >> 64) ^ (uint64_t)r->state,
                  (unsigned int)(r->state >> 122));
}

static inline double next_double(pcg64_rng *r)
{
    return (double)(pcg_next64(r) >> 11) * (1.0 / 9007199254740992.0);
}

/* ---- SeedSequence(entropy).generate_state(4, uint64) -------------------- */
#define SS_INIT_A 0x43b0d7e5u
#define SS_MULT_A 0x931e8875u
#define SS_INIT_B 0x8b51f9ddu
#define SS_MULT_B 0x58f38dedu
#define SS_MIX_L  0xca01f9ddu
#define SS_MIX_R  0x4973f715u

static inline uint32_t ss_hashmix(uint32_t value, uint32_t *hash_const)
{
    value ^= *hash_const;
    *hash_const *= SS_MULT_A;
    value *= *hash_const;
    value ^= value >> 16;
    return value;
}

static inline uint32_t ss_mix(uint32_t x, uint32_t y)
{
    uint32_t result = SS_MIX_L * x - SS_MIX_R * y;
    result ^= result >> 16;
    return result;
}

/* entropy limited to non-negative integers < 2^64 (validators use < 2^32) */
static void seedseq_generate(uint64_t entropy, uint64_t out[4])
{
    uint32_t pool[4];
    uint32_t ent[2];
    int nent, i, i_src, i_dst;
    uint32_t hc = SS_INIT_A, hb = SS_INIT_B;
    uint32_t w[8];

    ent[0] = (uint32_t)(entropy & 0xffffffffu);
    if (entropy >> 32) { ent[1] = (uint32_t)(entropy >> 32); nent = 2; }
    else               { nent = 1; }

    for (i = 0; i < 4; i++)
        pool[i] = ss_hashmix(i < nent ? ent[i] : 0u, &hc);
    for (i_src = 0; i_src < 4; i_src++)
        for (i_dst = 0; i_dst < 4; i_dst++)
            if (i_src != i_dst)
                pool[i_dst] = ss_mix(pool[i_dst], ss_hashmix(pool[i_src], &hc));
    /* (no entropy words beyond the pool size for our seed range) */

    for (i = 0; i < 8; i++) {
        uint32_t v = pool[i % 4];
        v ^= hb;
        hb *= SS_MULT_B;
        v *= hb;
        v ^= v >> 16;
        w[i] = v;
    }
    for (i = 0; i < 4; i++)
        out[i] = (uint64_t)w[2 * i] | ((uint64_t)w[2 * i + 1] << 32);
}

static void pcg_seed(pcg64_rng *r, uint64_t seed)
{
    uint64_t v[4];
    u128 initstate, initseq;
    seedseq_generate(seed, v);
    initstate = (((u128)v[0]) << 64) | v[1];
    initseq   = (((u128)v[2]) << 64) | v[3];
    r->state = 0;
    r->inc = (initseq << 1) | 1;
    pcg_step(r);
    r->state += initstate;
    pcg_step(r);
}

/* ---- numpy random_standard_normal (256-layer ziggurat) ------------------ */
static double std_normal(pcg64_rng *r)
{
    uint64_t rr, rabs;
    int idx, sign;
    double x, xx, yy;
    for (;;) {
        rr = pcg_next64(r);
        idx = (int)(rr & 0xff);
        rr >>= 8;
        sign = (int)(rr & 0x1);
        rabs = (rr >> 1) & 0x000fffffffffffffULL;
        x = (double)rabs * wi_double[idx];
        if (sign & 0x1)
            x = -x;
        if (rabs < ki_double[idx])
            return x;
        if (idx == 0) {
            for (;;) {
                xx = -ziggurat_nor_inv_r * log1p(-next_double(r));
                yy = -log1p(-next_double(r));
                if (yy + yy > xx * xx)
                    return ((rabs >> 8) & 0x1) ? -(ziggurat_nor_r + xx)
                                               : ziggurat_nor_r + xx;
            }
        } else {
            if (((fi_double[idx - 1] - fi_double[idx]) * next_double(r) +
                 fi_double[idx]) < exp(-0.5 * x * x))
                return x;
        }
    }
}

/* ---- handle registry ----------------------------------------------------- */
static pcg64_rng *g_states = NULL;
static size_t g_count = 0, g_cap = 0;

static void cleanup(void)
{
    free(g_states);
    g_states = NULL;
    g_count = g_cap = 0;
}

void mexFunction(int nlhs, mxArray *plhs[], int nrhs, const mxArray *prhs[])
{
    char cmd[16];

    if (nrhs < 1 || !mxIsChar(prhs[0]))
        mexErrMsgTxt("usage: homodyne_rng_mex('new'|'randn'|'reset', ...)");
    mxGetString(prhs[0], cmd, sizeof(cmd));

    if (strcmp(cmd, "reset") == 0) {
        g_count = 0;
        return;
    }

    if (strcmp(cmd, "new") == 0) {
        double seed_d;
        uint64_t seed;
        if (nrhs != 2)
            mexErrMsgTxt("homodyne_rng_mex('new', seed)");
        seed_d = mxGetScalar(prhs[1]);
        if (seed_d < 0 || seed_d != floor(seed_d) || seed_d > 9.007199254740992e15)
            mexErrMsgTxt("seed must be a non-negative integer < 2^53");
        seed = (uint64_t)seed_d;
        if (g_count == g_cap) {
            size_t ncap = g_cap ? 2 * g_cap : 1024;
            pcg64_rng *ns = (pcg64_rng *)realloc(g_states, ncap * sizeof(*ns));
            if (!ns)
                mexErrMsgTxt("out of memory");
            g_states = ns;
            g_cap = ncap;
            mexAtExit(cleanup);
        }
        pcg_seed(&g_states[g_count], seed);
        g_count++;
        plhs[0] = mxCreateDoubleScalar((double)g_count);
        return;
    }

    if (strcmp(cmd, "randn") == 0) {
        double h_d, n_d, *out;
        size_t h, n, i;
        pcg64_rng *r;
        if (nrhs != 3)
            mexErrMsgTxt("homodyne_rng_mex('randn', h, n)");
        h_d = mxGetScalar(prhs[1]);
        n_d = mxGetScalar(prhs[2]);
        if (h_d < 1 || h_d != floor(h_d) || (size_t)h_d > g_count)
            mexErrMsgTxt("invalid rng handle");
        if (n_d < 0 || n_d != floor(n_d))
            mexErrMsgTxt("n must be a non-negative integer");
        h = (size_t)h_d;
        n = (size_t)n_d;
        r = &g_states[h - 1];
        plhs[0] = mxCreateDoubleMatrix((mwSize)n, 1, mxREAL);
        out = mxGetPr(plhs[0]);
        for (i = 0; i < n; i++)
            out[i] = std_normal(r);
        return;
    }

    mexErrMsgTxt("unknown command");
}
