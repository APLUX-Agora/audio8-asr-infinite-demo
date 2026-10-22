# sdk

Prebuilt `libaudio8_asr.so` (`lib/`) and its public interface
[include/audio8_asr.h](include/audio8_asr.h).

The library is built for aarch64 Linux (AidLux); it needs the AidLite runtime with the QNN 2.48 backend (see the main
README's setup).

| | |
|---|---|
| Version | 0.6.0 (`A8_VERSION`) |
| Model resources | Matching ModelFarm/mms package with manifest and single-file prefix caches |
| Built with | Ubuntu 22.04 aarch64, g++ 11.4, aidlite-sdk 2.5.0, aidlite-qnn248 2.5.0, QNN / QAIRT 2.48, ICU 70 |
| sha256 | `0c2c8714895ecc87bacf91156a16171eef61bda28d342c85a9911f14f2d56c65` |

## C API

```c
a8_options o; a8_default_options(&o); o.clock_ms = 160; o.lang = A8_LANG_ZH;   // also roll_s, semantic_vad, replay_max_s
a8_engine *e = a8_create("models", &o);       // NULL on failure: a8_create_error()
a8_reset(e);                                   // new session
a8_feed(e, pcm, n);                            // returns the number of new tokens
a8_read_tokens(e, toks, cap);                  // id / is_text / audio_t / eot[4]
a8_token_bytes(e, id, buf, cap);               // UTF-8 bytes (decode incrementally)
a8_soft_reset(e, replay_from_s);               // mechanism: LM back to the prefix + replay of cached audio rows
a8_finish(e, -1);                              // end of input: default silent tail (5 clocks at 160 ms, 7 at 80 ms)
a8_eot_probs / a8_get_info / a8_get_stats / a8_last_error / a8_destroy
```

Return codes: `>= 0` success or a count, `< 0` an `A8_ERR_*` code with the message in `a8_last_error`.

## Python binding

`python/audio8_asr.py` (ctypes, used by the business layer):

```python
from audio8_asr import Engine
eng = Engine(clock_ms=160, lang="zh")
eng.reset()
toks = eng.feed(pcm_f32)               # [Token(id, is_text, audio_t, eot), ...]
text = eng.text_of([t.id for t in toks])
toks += eng.finish()
eng.soft_reset(replay_from_s); eng.stats(); eng.info; eng.close()
```

Library lookup order: `$AUDIO8_ASR_LIB`, `sdk/lib/`, `sdk/build/`, then the system loader path.

## Design notes

- **Passive engine.** No threads, timers or IO in the .so. `a8_feed` synchronously runs every clock the audio
  completes; how much to feed and when is the caller's choice.
- **Chunk invariance.** The same audio gives the same tokens however it is chunked.
- **Outputs through a queue.** `a8_feed` / `a8_finish` / `a8_soft_reset` return how many tokens were added; the caller
  drains them with `a8_read_tokens`, so it never has to guess buffer sizes.
- **Text as bytes.** `a8_token_bytes` returns UTF-8 bytes; a token can be part of a character, so decode incrementally.
- **No file names in the library.** The model directory's `manifest.json` lists the files of each audio clock; the
  library loads exactly these and fails with a message naming the missing or mismatching file (format, clock, key,
  path; shapes and tensor interfaces are checked against the model).
- **Audio clock and language at create time.** The clock (160 or 80 ms, upstream `frame_len` 8 / 4) selects the model
  package, the language only selects the LM prefix KV (language token). To switch, destroy and create again. A clock
  whose package is not installed fails with a clear message.
- **Soft reset: mechanism in the .so, policy in the caller.** The .so resets the LM to its prefix and replays the
  cached audio rows; when to do it (Silero onset, time without output, backoff) is decided by the business layer
  (`demo/reset_policy.py`). Valid once the first token is out.
- **Semantic VAD.** Every token carries P(no speech within 0.5 / 1 / 2 / 3 s) (`a8_token.eot`); the full [4][8]
  distribution is available through `a8_eot_probs`.
- **One engine = one thread at a time.**

## Environment variables

| Variable | Default | Effect |
|---|---|---|
| `A8_KEEP_STDOUT` | unset | `a8_create` / `a8_destroy` send the process's stdout to stderr while the runtime loads and releases the graphs (its license and fastrpc notices); set it (e.g. `1`) to keep them on stdout |
| `A8_AIDLITE_LOG` | `warning` | aidlite's log level; `info` shows everything |

## Python package discovery

The current main-branch Python binding exposes `resolve_model_dir()` and allows `Engine()` without a path.
It discovers this checkout's `models/manifest.json` first, otherwise a unique immediate child package. Multiple
packages require an explicit root, for example `Engine("models/qnn248_qcs8550", lang="en")`. An explicit invalid or
empty path raises the MODEL error before native loading; it never selects a different package. `engine.model_dir`
reports the resolved root. Explicit relative paths use the caller's working directory. Standalone integrations
should pass their package root explicitly. Native C callers continue to supply the exact root to the C API.

Discovery is packaging/interface glue: it neither checks all payload hashes nor proves chip compatibility.
The Web application's preflight validates its required files; native model loading remains authoritative.
The real-name SDK uses `audio8_asr`, `A8Error`, `a8_*` and `AUDIO8_ASR_LIB` in every delivery. Older release tags retain their original `live_transcribe_01` interface and library; the incompatible naming migration is documented in [the migration guide](../docs/REAL_MODEL_MIGRATION.md).

## Optional hotwords (development SDK 0.6.0)

Hotword bias is disabled by default. The C++ library owns UTF-8 tokenization, prefix matching, quantized-logit score adjustment and history. There are no term-specific spelling, syntax or semantic rules. Existing model weights and graph files are unchanged.

After `reset()` and before feeding audio, call `engine.set_hotwords(["term", "a phrase"], tokenizer_path="/path/to/matching/tokenizer.json")`. The defaults are top-k 50, first-token boost 6 and continuation boost 8; pass an empty list to disable. Configuration persists across reset, while matching history clears on reset and soft reset. C users call `a8_set_hotwords`; the existing options/info layouts are unchanged. The Python wrapper still works with an older library while hotwords are disabled, and reports an unsupported-feature error if enabled.

The matching tokenizer JSON is an optional runtime resource, resolved from an explicit path, manifest `extras.tokenizer`, or package-root `tokenizer.json`. It is required only when enabling hotwords. Historical released model packages do not automatically gain this asset; distribution of the new SDK/resource pair is pending. Do not substitute another model's tokenizer. The tokenizer is lazy-loaded and linked inside the same SDK library; the build requires ICU 67+ development headers (`libicu-dev`); the tested Ubuntu 22.04 binary links to `libicu70`, which must be installed at runtime.

These are preferences, not guaranteed vocabulary constraints. False merges of ordinary expressions are possible. The original-model development probe corrected selected technical terms but also introduced two errors in 65 constructed negatives. Board results must be evaluated separately; no universal accuracy claim is made.


## Licensing / 许可

The APLUX proprietary portions of the prebuilt `.so` libraries are covered by the
Pandora Model and SDK License, not by the Apache-2.0 license of the business layer.
The C headers and Python bindings authored by APLUX remain Apache-2.0. Third-party
portions keep their own terms. See [licensing scope](../LICENSING.md),
[中文协议](../LICENSES/Pandora-Model-SDK.zh-CN.txt),
[English agreement](../LICENSES/Pandora-Model-SDK.en.txt) and the notices in `lib/`.

预编译 `.so` 中阿加犀专有部分采用 Pandora 自有许可，业务层 Apache-2.0 不覆盖这些专有部分；
阿加犀的 C 头文件、Python 绑定仍为 Apache-2.0，第三方部分保留各自许可。
