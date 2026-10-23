# Python API reference

Import `audio8_asr` from this checkout's `sdk/python` using the Demo's `.venv`.
The module is a thin ctypes interface to the same prebuilt `libaudio8_asr.so` used by C/C++ callers.
It does not read audio files, resample, mix channels, pace a stream or start a Web service.
See the [examples](../examples/README.md) for those application tasks.

## Create and own an engine

```python
import codecs
import sys
sys.path.insert(0, "sdk/python")
from audio8_asr import Engine

engine = Engine("models/qnn248_qcs8550", clock_ms=160, lang="en")
try:
    engine.reset()
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    for pcm in audio_chunks:  # 1-D float32, mono 16000 Hz, samples in [-1, 1]
        tokens = engine.feed(pcm)
        print(decoder.decode(engine.text_of([t.id for t in tokens])), end="")
    tokens = engine.finish()
    print(decoder.decode(engine.text_of([t.id for t in tokens]), final=True))
finally:
    engine.close()
```

This integration sketch assumes the application supplies `audio_chunks`; runnable file examples are in
`examples/python`. An Engine is **not** a context manager. Always close it explicitly in `finally`; `__del__`
is a fallback, not an application shutdown protocol. Use one thread at a time per engine, including close.
Wait for any in-flight native call to return before closing. The example programs implement cooperative
SIGTERM/SIGINT handling in `examples/python/example_lifecycle.py`: signal handlers only request shutdown,
including during construction, and the main thread closes the returned handle at a safe point.

### `Engine(model_dir=None, clock_ms=None, lang="zh", roll_s=28.8, stable_rows=-1, semantic_vad=True, replay_max_s=10.0)`

Construction synchronously loads the model and stores an engine handle. Failure raises `A8Error` or a library
loading `OSError`; do not continue with a partially created engine.

| Parameter | Meaning |
| --- | --- |
| `model_dir` | Path-like package root directly containing `manifest.json`. `None` uses discovery below. Relative explicit paths use the caller's working directory. |
| `clock_ms` | `160` or `80`, selecting the installed model. `None` selects the first installed clock, preferring 160. The two ModelFarm models are separate packages. |
| `lang` | Use exactly `"zh"` or `"en"` for the LM prefix. The current wrapper maps only `"en"` to English and other values to Chinese; validate application input rather than relying on a language error. |
| `roll_s` | Rolling LM context in seconds, default 28.8. `0` disables rolling; a full cache then raises `A8_ERR_FULL`. Keep the model's default unless deliberately managing bounded sessions. |
| `stable_rows` | Rows retained at each trim; `-1` selects the model default (9 at 160ms, 18 at 80ms). Other values must be nonnegative and fit the rolling/cache budget; invalid native configurations fail. |
| `semantic_vad` | Whether to compute end-of-turn heads. Boolean, default true. |
| `replay_max_s` | Seconds of audio rows retained for soft-reset replay, default 10. Must be nonnegative and fit the model's replay/context budget. |

Python numeric arguments are converted to the C scalar types. Do not pass oversized integers, nonfinite
numbers or values outside the documented model contract. Constructor options are fixed for an engine;
changing its language/clock requires closing and recreating it.

## Methods

| Method | Input, return and state contract |
| --- | --- |
| `reset()` | Starts/restarts a session on the loaded model: resets positions, audio time, native token queue and per-session stats. Returns `None`. Resets hotword matching history, retaining hotword configuration. Use before a new audio stream and after `finish()`. |
| `feed(pcm)` | Supply a one-dimensional mono 16 kHz sample sequence in `[-1,1]`, finite values. The wrapper converts to contiguous NumPy float32; it does **not** enforce channel layout, resample or downmix. Returns `list[Token]` newly emitted by this call, possibly empty. Audio length must fit the C `int` sample count. Synchronous; input is consumed before return. After `finish()`, raises a state error until reset. |
| `finish(tail_tokens=-1)` | Flushes the end of a stream with silent audio clocks. `-1` means the model default (5 clocks at 160ms, 7 at 80ms); otherwise use a nonnegative clock count. Returns `list[Token]`, possibly empty. Call once per session; repeated finish or further feed/soft-reset requires reset first. |
| `soft_reset(replay_from_s)` | Seconds from this session's audio timeline. Resets the LM and replays cached audio rows newer than that point, limited by `replay_max_s`; audio-tower state continues. Returns replayed `list[Token]`. Requires an emitted token and an unfinished session. This is a mechanism; the application decides when it is appropriate. |
| `token_bytes(tid)` | Integer token ID; returns `bytes` (empty for non-text tokens). UTF-8 characters may span tokens. Use an incremental decoder rather than decoding each token independently. |
| `text_of(ids)` | Iterable of token IDs; concatenates their raw bytes and returns **`bytes`, not `str`**. This method neither decodes nor owns a text-stream decoder. |
| `eot_probs()` | Returns a NumPy float32 array of shape `(4,8)` for the last token's end-of-turn class probabilities. Enable semantic VAD; normally query after receiving a token. |
| `stats()` | Returns the per-session dictionary below. Query while the engine is open. |
| `close()` | Releases native model/host/device resources. Returns `None`; repeated close is safe. Do not invoke other engine methods after close. No asynchronous worker is owned by this engine. |

### `set_hotwords(words=(), *, tokenizer_path=None, top_k=50, start_boost=6.0, continuation_boost=8.0)`

Call after reset and before audio. Returns `None`. `words` is a list or tuple of nonempty strings; an empty
list disables bias. SDK 0.6.1 and the current HF packages include the matching tokenizer resource.

- `tokenizer_path`: matching tokenizer JSON; otherwise resolve manifest `extras.tokenizer`, then package-root
  `tokenizer.json`. No system ICU package or external ICU data directory is required.
- `top_k`: `0` disables gating; otherwise integer from 1 to vocabulary size.
- Boosts: finite logit adjustments in `[0,100]`, defaults 6 and 8.
- Native limits: 256 words, 1024 UTF-8 bytes/word, 128 tokens/variant, total JSON at most 65536 bytes.
- Configuration persists across reset; matching history clears on reset and soft-reset. Bias is probabilistic
  and can change ordinary words; it does not guarantee exact spelling or constrain the vocabulary.
- A wrapper `ValueError` may reject invalid word-list types/values. A missing tokenizer or invalid native
  configuration raises `A8Error`. Older libraries without this ABI support empty/disabled lists only.

## Results and attributes

`Token` is a namedtuple with `id: int`, `is_text: bool`, `audio_t: float` (seconds from session start, excluding
synthetic padding), and `eot: tuple[float,float,float,float]`. `eot` gives the no-speech probabilities at
0.5/1/2/3 seconds and is zero when semantic VAD is disabled. EOS is not emitted. The model's transcription
delay is separate from `audio_t`: `num_delay_tokens * clock_s`.

| Attribute | Contents |
| --- | --- |
| `model_dir` | Resolved absolute package root. |
| `sampling_rate` | 16000 samples/second. |
| `samples_per_token` | 2560 for 160ms; 1280 for 80ms. |
| `clock_s` | `samples_per_token / sampling_rate`, seconds. |
| `info` | Snapshot dictionary created at construction, not a method. Keys: `sampling_rate`, `samples_per_token`, `clock_ms`, `lang` (`en`/`zh`), `eot_horizons_s` (four floats), `num_delay_tokens`, `streaming_pad_id`, `default_tail_tokens`, `roll_s`. |

`stats()` returns `audio_fed_s` (real audio seconds), `n_tokens`, `lm_pos`, `lm_trims`, `soft_resets`, and
cumulative milliseconds `ms_mel`, `ms_tower_prep`, `ms_tower_npu`, `ms_tower_post`, `ms_projector_npu`,
`ms_lm_prep`, `ms_lm_npu`, `ms_lm_post`. These are session counters, not an end-to-end application latency.

## Package and version helpers

| Function | Contract |
| --- | --- |
| `version()` | Loads the native library if needed and returns its version string. |
| `resolve_model_dir(model_dir=None, *, models_root=None)` | Returns an absolute string path. An explicit path must contain the manifest and never falls back. Otherwise prefer a flat manifest in the checkout's `models/`, then exactly one immediate child package. Multiple/missing packages raise `A8Error(-2, ...)`. `models_root` overrides only the discovery root. Discovery does not validate all hashes or target compatibility. |
| `installed_clocks(model_dir=None)` | Returns available clock integers in preference order `[160,80]`, checking manifest configuration-file existence. Not a full integrity check. |
| `extra_file(model_dir, name)` | Returns the manifest `extras` path joined to the resolved root, or `None`. Does not prove the file exists. Examples use `silero_vad`; hotwords use `tokenizer`. |

`lib()` is the binding's low-level ctypes loader, not the normal integration API; use `Engine`.
Library resolution checks `AUDIO8_ASR_LIB`, checkout `sdk/lib`, checkout `sdk/build`, then the system loader.
Use a matched installation; an explicit environment override should name the qualified library.

## Errors

`A8Error` derives from `RuntimeError`; `.code` is the native negative error number, or `None` for native
creation failure (only a message is provided by that C API). `str(error)` includes the classification/message.

| Code | Symbol | Meaning |
| --- | --- | --- |
| -1 | A8_ERR_ARG | Invalid argument. |
| -2 | A8_ERR_MODEL | Missing/inconsistent model resource or package path. |
| -3 | A8_ERR_NPU | External AidLite/QNN failure. |
| -4 | A8_ERR_FULL | LM cache full with rolling disabled: finish/reset or start a new session. |
| -5 | A8_ERR_STATE | Invalid call order or unsupported optional feature. |
| -6 | A8_ERR_INTERNAL | Internal failure, including allocation errors. |

Python conversions may also raise `TypeError`, `ValueError` or `OverflowError`; native library lookup can raise
`OSError`. Handle application errors while still closing an existing engine. A closed engine is not a reusable
error-recovery object: create another one when needed.

The shipped CLI examples request cooperative stops and enable syscall restart for SIGTERM/SIGINT.
Python signal handlers otherwise disable restart, which can interrupt a native FastRPC wait before cleanup.
Custom applications must finish outstanding calls before close; do not raise from a signal handler during native creation.
