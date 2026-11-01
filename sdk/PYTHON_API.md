# Python ASR API

Install into the interpreter/venv that runs your application. From the Demo repository root:

```bash
python -m pip install ./sdk
```

Then `from audio8_asr import ASRModel` works in your own application without `sys.path` changes.
This delivery includes native SDK 0.8.0; Python distribution version is `0.8.0`.
Use Python, native library and models from compatible deliveries. No model is downloaded by `from_pretrained`.

## Quick start

```python
from audio8_asr import ASRModel

with ASRModel.from_pretrained("models") as model:
    result = model.transcribe("speech.wav")
    print(result.text, result.finish_reason)
```

Pass a package root containing `models.json` (or a legacy `manifest.json`), or set `A8_MODELS` to that root. Without either, the installed SDK reports a missing selection; it does not search near `site-packages`. Demo launchers/examples separately discover their checkout's flat or unique immediate child package. Multiple packages require explicit selection. Explicit paths and `library=` select exactly those files; failures do not fall back to another package or library.

## Transcription

```python
model.transcribe(audio, *, sample_rate=None, channel=None, language=None,
                 prompt=None, hotwords=None, max_new_tokens=None)
```

| Argument | Contract |
| --- | --- |
| `audio` | Local path (`str`/`PathLike`) or NumPy `float32`/`float64` array. Initial file formats: WAV, FLAC, MP3, subject to the installed SoundFile/libsndfile decoder. No URLs or raw encoded bytes. |
| `sample_rate` | Positive integer source Hz, mandatory for PCM. File metadata supplies the rate; a supplied conflicting rate is an error. |
| `channel` | Zero-based integer selection before resampling, or `None`. Mono passes through; stereo defaults to arithmetic mean. More than two channels require explicit selection. |
| `language` | `None` means model default; `"auto"` explicitly requests automatic language behavior; other strings explicitly select a language. See model support below. |
| `prompt` | Optional task instruction when supported; unsupported use raises an error. |
| `hotwords` | `None`, list/tuple of nonempty strings, or `HotwordConfig`. Cleared for each new request unless supplied again. |
| `max_new_tokens` | Positive integer or `None` for native policy. Counts generated tokens including controls, never characters. |

PCM axes are `(samples,)` or `(samples, channels)`. Arrays must contain finite normalized values in `[-1, 1]`. Integer PCM arrays, including int16, are rejected; ordinary PCM16 WAV **files** can be decoded to float. No inferred interleaving/axis transposition. File decoding, channel conversion and 16 kHz resampling live in editable Python, outside the inference `.so`. There is no implicit VAD, denoising, gain normalization or long-file segmentation. Excessive rational rate ratios (reduced up/down factor above100000) fail before FIR allocation; resample such unusual source rates explicitly.

`TranscriptionResult` is an immutable owned value with `text: str`, `language: str | None`, `duration_s: float`, `finish_reason: "stop" | "length"`, and derived `is_complete: bool`. Duration is the complete source input duration, even when generation is capped. `language=None` does not claim language detection. `stop` means normal native completion; `length` means an effective generation cap prevented normal completion. EOS on the final allowed token is still `stop`. Invalid input and inference failures raise exceptions rather than returning an empty success. Valid nonspeech can yield an empty transcript. `dataclasses.asdict(result)` gives serializable fields; derived properties are not separate stored fields.

## Capabilities and errors

`model.capabilities` is an optional read-only immutable descriptor: `streaming`, `supported_languages`, `selectable_languages`, `auto_language`, `prompt`, `hotwords`, `max_new_tokens`. Ordinary callers can read this documentation instead; unsupported parameters still fail explicitly.

`TypeError`/`ValueError` indicate invalid Python inputs. `ASRError` subclasses are `ASRLoadError`, `ASRInferenceError`, `ASRStateError`, and `ASRUnsupportedError`. Runtime exceptions retain `native_code` when available and the original cause. A validation error before native work leaves the model reusable. After native failure, close and recreate; there is no silent retry.

`close()` is explicit and idempotent. Context managers call it. Each model has one active request/recording. Overlapping operations raise `ASRStateError`. Wait for synchronous work and close the recording before closing its model; no immediate native cancellation or asynchronous API is promised. Application signal handlers must request cooperative shutdown and wait for workers before destruction; runnable examples implement this ownership pattern.

`HotwordConfig(words, top_k=50, start_boost=6.0, continuation_boost=8.0)` is immutable. `words` is converted to a tuple; request validation checks model-specific bounds. Hints are token-prefix bias, not a guarantee that a phrase appears.

## Audio8-ASR-Infinite specifics

```python
ASRModel.from_pretrained(model_dir=None, *, library=None, clock_ms=None,
                        roll_s=28.8, stable_rows=-1, semantic_vad=True,
                        replay_max_s=10.0, runtime=None)
```

Request-language, budget and final-audio controls were introduced in native SDK 0.7.0. The current models.json version 2 delivery requires the matched native **0.8.0** / Python **0.8.0** pair. `clock_ms=None` selects an installed clock (160 first, then 80). Explicit clock must exist. Other options preserve native rolling, stable-row, semantic EOT and replay controls; they are not cross-model features. `stable_rows=-1` uses native defaults; `roll_s=0` disables rolling and therefore retains native context-capacity limits. `sdk_version`, `info` (copy) and `stats()` (last owned-call snapshot) expose advanced diagnostics.

- `language=None` defaults to Chinese; `"zh"`/`"en"` select native prefix state per request. `"auto"` is unsupported. Result language reports the selected language, not detected speech.
- Free-text `prompt` is unsupported, including empty string.
- `max_new_tokens=None` keeps the native continuous-clock policy; explicit limits are positive int64 values and include streaming/control tokens. No post-hoc text slicing.
- Hotwords: at most 256 entries, 1024 UTF-8 bytes each; top_k up to the package vocabulary size; finite boosts 0..100. The matching package tokenizer is required.

## Live streaming

```python
with ASRModel.from_pretrained("models") as model:
    with model.create_stream(sample_rate=48000, channels=2, language="en") as stream:
        for pcm_chunk in microphone_chunks:  # float, (samples, 2), original source rate
            update = stream.feed(pcm_chunk)
            print(update.delta, end="", flush=True)
            if update.is_final:
                break
        result = stream.finish()
```

`create_stream(*, sample_rate, channels=1, channel=None, language=None, prompt=None, hotwords=None, max_new_tokens=None)` reserves one model for one recording until `stream.close()`. Rate and channel layout stay fixed throughout a recording. Stateful resampling preserves FIR history and phase across chunks; `finish()` flushes its tail once. Source frame count determines duration.

`feed(pcm)` returns immutable `TranscriptionUpdate(text, delta, finish_reason=None)`. Text is a complete snapshot; delta is newly completed UTF-8 text. `is_final` is derived from a terminal reason. A live cap returns `length`, including when a later caller declares EOF. Feed after terminal completion fails.

`finish()` returns the complete `TranscriptionResult`; subsequent calls return that cached object. It drains once, never reruns inference. A normal complete result requires known EOF and all native/converter tails drained. Empty recordings fail. Closing early abandons pending input without fabricating normal completion or flushing extra inference. Results already returned remain valid after closing.

Advanced integrations can inspect `stream.last_tokens` (copied token ID/is_text/audio_t/EOT records), `token_bytes(id)`, `text_of(ids)`, `eot_probs()`, `info`, `stats()`, `clock_s`, and `samples_per_token`. `soft_reset(replay_from_s)` replays cached rows and returns copied replay tokens; those tokens are appended to the stream snapshot. Applications using replay own endpoint/timestamp/presentation policy; the Web demo's ResetPolicy remains outside inference. These controls are model-specific and are not required for ordinary transcription.

## Root models.json configuration

SDK 0.8.0 (native 0.8.0) resolves common resources and target graphs from models.json version 2. Pass the root containing models.json; see the [model setup](../docs/MODEL_SETUP.md) and [package contract](MODEL_PACKAGE.md). Legacy manifests remain supported. Both audio clocks were tested on QCS8550 / Ubuntu22.04 with CPython3.10,3.11 and3.12.

### Package resource inspection

`model_files(model_dir, clock_ms)` returns a fresh dictionary of runtime role names to package-root-relative file paths. It performs new-index schema/path/target completeness checks without loading a native library; it does not hash resources or identify board hardware. `installed_clocks(model_dir)` reports the selected package clock. Web preflight uses the same resource paths for SHA256SUMS checks.

## Host process integration (0.8.0)

The SDK leaves host signal masks/handlers, stdout/stderr, global AidLite logging,
core/memlock limits and dumpable state unchanged. Vendor notices may appear.
Calls are synchronous; signal delivery to Python may wait for native return.
Use explicit close/destroy after in-flight work finishes. Persistent native owner
slots permit cleanup after an interrupted return handoff. Model/Runtime handles
are process-local; use spawn/exec, and initialize there instead of inheriting an
initialized AidLite provider. See [Runtime host contract](RUNTIME.md#host-integration).
