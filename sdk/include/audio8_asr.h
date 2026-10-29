/*
 * audio8_asr.h - Audio8-ASR-Infinite streaming ASR on Qualcomm NPUs (QNN context binaries via aidlite), C ABI of
 * libaudio8_asr.so. The NPU architecture is a property of the model files; the library itself is architecture-neutral.
 *
 * The engine implements the model's own streaming protocol (DSM: one text token per audio clock): audio windowing,
 * mel, audio tower + projector (NPU), LM (NPU, native KV), KV / position management, the 30 s rolling context, greedy
 * decoding, the semantic-VAD (end-of-turn) heads and the soft-reset replay mechanism.
 * It is passive: no threads, no timers, no IO. The caller decides when and how much audio to feed; every call runs
 * synchronously all the clocks the audio allows. Policies (silence gate, when to soft-reset, pacing, UI) belong to the
 * caller.
 *
 * Typical use:
 *   a8_options o; a8_default_options(&o); o.clock_ms = 160; o.lang = A8_LANG_ZH;
 *   a8_engine *e = a8_create("models", &o);           // loads the bins (~2 s)
 *   a8_reset(e);                                       // new session
 *   while (have_audio) { a8_feed(e, pcm, n); n_tok = a8_read_tokens(e, toks, cap); ... }
 *   a8_finish(e, -1); a8_read_tokens(...);             // end of input: drain the last tokens
 *   a8_destroy(e);
 *
 * Feeding is chunk-invariant: the same audio fed in any chunking gives the same tokens.
 * One engine is not thread-safe; use it from one thread at a time.
 */
#ifndef AUDIO8_ASR_H
#define AUDIO8_ASR_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define A8_VERSION "0.7.2-dev2"

#if defined(__GNUC__)
#define A8_API __attribute__((visibility("default")))
#else
#define A8_API
#endif

/* return codes (>= 0 = success) */
#define A8_OK 0
#define A8_ERR_ARG -1     /* bad argument */
#define A8_ERR_MODEL -2   /* model file missing / inconsistent */
#define A8_ERR_NPU -3     /* aidlite / QNN failure */
#define A8_ERR_FULL -4    /* LM KV full (only with roll_s = 0): call a8_finish + a8_reset */
#define A8_ERR_STATE -5   /* call not valid in the current state (e.g. a8_feed after a8_finish) */
#define A8_ERR_INTERNAL -6 /* unexpected failure inside the library (e.g. out of memory) */

#define A8_LANG_ZH 0
#define A8_LANG_EN 1
#define A8_EOT_HORIZONS 4 /* semantic VAD horizons, see a8_info.eot_horizons_s (0.5 / 1 / 2 / 3 s) */
#define A8_EOT_CLASSES 8

typedef struct a8_engine a8_engine;

typedef struct {
    int clock_ms;      /* audio clock: 160 (default) or 80 ms, one text token per clock; selects the model package */
    int lang;          /* A8_LANG_ZH / A8_LANG_EN: which LM prefix KV (language token) is loaded */
    double roll_s;     /* LM rolling context in seconds (default 28.8); 0 = no rolling (A8_ERR_FULL when KV is full) */
    int stable_rows;   /* LM rows kept by every trim; -1 = default (left pad: 9 at 160 ms, 18 at 80 ms) */
    int semantic_vad;  /* 1 = compute the end-of-turn heads for every token (a8_token.eot), 0 = off. Default 1 */
    double replay_max_s; /* audio rows cached for a8_soft_reset (default 10 s) */
} a8_options;

typedef struct {
    int32_t id;        /* token id; EOS is never emitted */
    int32_t is_text;   /* 0 for STREAMING_PAD / STREAMING_WORD / BOS / PAD (no text), 1 otherwise */
    float audio_t;     /* end of the audio clock behind this token, seconds from the session start (real audio, the
                          synthetic left pad excluded) */
    float eot[A8_EOT_HORIZONS]; /* P(no speech within horizon h) after this token; 0 if semantic_vad is off */
} a8_token;

typedef struct {
    int sampling_rate;          /* 16000 */
    int samples_per_token;      /* one clock: 2560 at 160 ms, 1280 at 80 ms */
    int clock_ms, lang;
    float eot_horizons_s[A8_EOT_HORIZONS];
    int num_delay_tokens;       /* model delay in clocks (text lags the audio by num_delay_tokens * clock) */
    int streaming_pad_id;       /* STREAMING_PAD ("nothing new yet"); policies use it to tell silence from output */
    int default_tail_tokens;    /* a8_finish(e, -1) appends this many silent clocks */
    double roll_s;              /* LM rolling context in use (0 = off) */
} a8_info;

typedef struct {
    double audio_fed_s;         /* real audio fed in this session */
    int64_t n_tokens;           /* tokens emitted in this session */
    int64_t lm_pos;             /* absolute LM position of the next row */
    int32_t lm_trims;           /* rolling trims so far */
    int32_t soft_resets;        /* a8_soft_reset calls in this session */
    /* cumulative ms in this session, per stage */
    double ms_mel, ms_tower_prep, ms_tower_npu, ms_tower_post, ms_projector_npu, ms_lm_prep, ms_lm_npu, ms_lm_post;
} a8_stats;

A8_API const char *a8_version(void);
A8_API void a8_default_options(a8_options *opt);

/* Load the model from model_dir (layout: models/README.md). NULL on failure, see a8_create_error().
   While loading (and in a8_destroy) the process's stdout is sent to stderr: the vendor runtime prints notices there
   (A8_KEEP_STDOUT=1 to keep them on stdout). */
A8_API a8_engine *a8_create(const char *model_dir, const a8_options *opt);
A8_API const char *a8_create_error(void);   /* last a8_create failure (thread-local) */
A8_API void a8_destroy(a8_engine *e);

A8_API int a8_get_info(a8_engine *e, a8_info *info);
A8_API const char *a8_last_error(a8_engine *e);

/* New session: KV back to the prefix, positions and time restart, token queue cleared. */
A8_API int a8_reset(a8_engine *e);

/* Begin one exclusive request without reloading model graphs. max_new_tokens=0
 * uses the continuous model's native unlimited-clock policy. Counts include
 * emitted streaming/control tokens. lang is A8_LANG_ZH or A8_LANG_EN. */
A8_API int a8_begin_request(a8_engine *e, int lang, int64_t max_new_tokens);
/* 0 running, 1 normal EOF/drain, 2 generation cap; negative on API error. */
A8_API int a8_request_state(a8_engine *e);
/* Finite final audio plus EOF/tail in one operation; preserves exact-cap normal
 * completion. Same PCM contract as a8_feed; tail_tokens=-1 uses native default. */
A8_API int a8_finish_audio(a8_engine *e, const float *pcm, int n, int tail_tokens);


/* Optional decode-time token-prefix bias, disabled by default. Call after create/reset,
   before feeding any audio. words_json is a JSON array of UTF-8 strings; [] disables.
   Nonempty words require the matching tokenizer.json path (no model-package changes).
   top_k: 0 = no gate, otherwise 1..vocabulary size. Boosts are finite logit units in [0,100].
   Configuration persists across reset; matching history clears on reset/soft-reset.
   This is a probabilistic preference and can change ordinary words; no term-specific rules.
   Limits: 256 words, 1024 bytes/word, 128 tokens/variant, 65536 bytes total JSON.
   Existing options/info layouts are unchanged. Older libraries do not expose this function. */
A8_API int a8_set_hotwords(a8_engine *e, const char *tokenizer_path, const char *words_json, int top_k, float start_boost, float continuation_boost);

/* Append n mono float samples (16 kHz, clipped to [-1, 1]) and run every clock they complete.
   Returns the number of new tokens queued (read them with a8_read_tokens), or < 0. */
A8_API int a8_feed(a8_engine *e, const float *pcm, int n);

/* End of input: append tail_tokens clocks of silence (-1 = default: 5 at 160 ms, 7 at 80 ms) and run them.
   Returns the number of new tokens queued, or < 0. After this only a8_read_tokens / a8_reset are valid. */
A8_API int a8_finish(a8_engine *e, int tail_tokens);

/* Pop up to cap queued tokens (oldest first). Returns how many were written. */
A8_API int a8_read_tokens(a8_engine *e, a8_token *out, int cap);

/* UTF-8 bytes of a token (0 bytes for the no-text tokens). A token may hold part of a multi-byte character: decode
   incrementally across tokens. Returns the byte count (may exceed cap: then only cap bytes are written), or < 0. */
A8_API int a8_token_bytes(a8_engine *e, int32_t id, char *buf, int cap);

/* Soft reset (mechanism; the caller decides when): LM context back to the prefix (fresh positions), then the cached
   audio rows with audio_t > replay_from_s (at most replay_max_s before the next clock) are replayed so the model
   re-hears them. The audio tower and the audio stream are untouched; feeding continues normally afterwards.
   Valid once the first token is out (A8_ERR_STATE before). Returns the number of new tokens queued by the replay,
   or < 0. */
A8_API int a8_soft_reset(a8_engine *e, double replay_from_s);

/* Full [horizon][class] softmax of the semantic VAD heads after the last token (semantic_vad must be on). */
A8_API int a8_eot_probs(a8_engine *e, float out[A8_EOT_HORIZONS][A8_EOT_CLASSES]);

A8_API int a8_get_stats(a8_engine *e, a8_stats *st);

#ifdef __cplusplus
}
#endif

#endif /* AUDIO8_ASR_H */
