# examples

Small programs that use the SDK directly, without the web demo. Start from these to integrate Audio8-ASR-Infinite into
your own application.

Requirements: the setup in the [main README](../README.md#setup) (AidLite runtime, `pip install -r requirements.txt`:
numpy, soundfile, scipy, and onnxruntime for `stream_file.py`), the SDK library (`sdk/lib/libaudio8_asr.so`) and the
model package of your chip ([../models/README.md](../models/README.md)); `$SOC` below is its folder in `models/`, e.g.
`qnn248_<chip>`. Run the commands from the root of the repository.

`examples/audio/` holds the 10-minute audio tracks of the web demo's three videos (16 kHz mono FLAC): one English
keynote and two Chinese product launches, with music and video inserts, as real long-form input.

## Python

### transcribe_file.py: an audio file to text

The smallest complete use of the Python binding: load the models, feed the audio, read the text. Audio files that
soundfile reads (wav, flac, ogg, mp3, ...) are averaged to mono and resampled to 16 kHz.

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --lang en
```

```
[160 ms clock models loaded in 2.1 s]
I was a day. I've been looking forward to for two and a half years. Every once in a while, a revolutionary product
comes along. That changes everything. And Apple has been. Well, first of all, one's very fortunate. ...
[600.0 s of audio in 228.3 s, RTF 0.38]
```

| Option | Default | Meaning |
|---|---|---|
| `--lang` | `en` | language spoken in the audio (`en` or `zh`) |
| `--clock-ms` | the installed one (160 first) | audio clock: `160` or `80` ms (80: text about 0.1 s sooner, twice the compute) |
| `--models` | discover this checkout’s `models/` | explicit package root directly containing manifest.json; overrides A8_MODELS |

This is the bare engine. For long audio with music, applause or long pauses use `stream_file.py`.

### stream_file.py: long audio, live

Plays the file into the engine at real-time speed in 80 ms chunks, the way a microphone delivers audio, and prints the
text as it comes out. A new paragraph starts after each end of turn predicted by the model (semantic VAD); every
paragraph starts with the time its first word was spoken.

It also adds the two helpers the web demo uses for long real-world audio (imported from `demo/`):
- a **silence gate** (Silero VAD) that silences the noise before the first words;
- a **soft-reset policy**: after a long stretch without speech (e.g. a music video in a keynote) the model can stay
  silent although speech is back; the policy then lets the engine re-listen to the last seconds
  (`Engine.soft_reset`). `--plain` turns both off to show the difference.

```bash
.venv/bin/python examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --lang zh
```

```
[160 ms clock, 480 ms model delay; 600.0 s of audio, real time]
[   0.64 s] 大家晚上好，欢迎大家收看《小米秋季》新品的发布会。这一次啊，我们一共给大家带来了两款产品：小米十八Pro和小米十八Pro Max，……我们来看一个亮相的视频。
[  66.88 s] 我拿到，我拿到，我来看一下细节啊。点亮这块屏幕，大家看到，正面呢几乎没有边框，观感呢也非常的震撼。……
...
[processing lag: median 0.14 s, max 1.75 s (+ 480 ms model delay); wall 600.4 s; soft resets 1]
```

On this file the music video after the first paragraph stops the bare engine for the rest of the 10 minutes
(`--plain`: 125 characters in total); with the policy one soft reset at 67 s brings the text back (2624 characters).

| Option | Default | Meaning |
|---|---|---|
| `--lang`, `--clock-ms`, `--models` | | as above |
| `--chunk-ms` | `80` | audio delivered per chunk (at most one audio clock) |
| `--eot-horizon` | `2` | end of turn = probability that nobody speaks within the next 0.5 / 1 / 2 / 3 s |
| `--eot-threshold` | `0.6` | end-of-turn probability that starts a new paragraph |
| `--fast` | off | feed as fast as possible instead of real time |
| `--plain` | off | no silence gate and no soft-reset policy |

The processing lag is the time between a piece of audio arriving and its text coming out; the model's fixed 480 ms
transcription delay comes on top of it, so words appear about 0.6 s after they are spoken. The maximum is the burst
after a soft reset, when the engine re-listens to a few seconds at once.

## Use the SDK in your own code

```python
import codecs, sys
sys.path.insert(0, "sdk/python")
from audio8_asr import Engine

eng = Engine(lang="en")                 # load the models once (installed clock, 160 ms first)
dec = codecs.getincrementaldecoder("utf-8")(errors="replace")    # a token can hold part of a character
eng.reset()                                                     # one session per stream
for chunk in audio_chunks:                                      # float32, 16 kHz mono, any chunk size
    toks = eng.feed(chunk)                                      # each token: id, audio time, end-of-turn probabilities
    print(dec.decode(eng.text_of([t.id for t in toks])), end="", flush=True)
toks = eng.finish()                                             # end of input: flush the last words
print(dec.decode(eng.text_of([t.id for t in toks]), final=True))
```

The C API (`sdk/include/audio8_asr.h`) has the same calls; see [../sdk/README.md](../sdk/README.md).

## What the examples show

- **Any chunk size.** The engine produces the same text however the audio is chunked; it runs every audio clock the
  fed audio completes and returns the new tokens.
- **Text as bytes.** A token can hold part of a UTF-8 character, so the text is decoded incrementally
  (`codecs.getincrementaldecoder`).
- **End of the input.** `finish()` flushes the last words (it appends a short silence internally).
- **Sessions.** `reset()` starts a new session on the loaded models; create the engine once and reuse it.
- **Policies stay outside the SDK.** The silence gate and the soft-reset trigger are a few lines of Python around
  `feed()` and `soft_reset()` (`demo/vad_gate.py`, `demo/reset_policy.py`).

## Model paths and environment

Use this checkout's `.venv/bin/python` as in the main README. SDK/examples/Web share path discovery: the flat
`models/manifest.json` layout is supported, otherwise a unique immediate chip subdirectory is selected. No path
option is needed for the standard single-chip download. With multiple packages, explicitly pass
`--models models/qnn248_<chip>`; that directory must directly contain `manifest.json`. Invalid explicit paths never
fall back. `--models` overrides `A8_MODELS`. Explicit relative paths use the caller's working directory; automatic
paths are anchored to this checkout. The resolved package path is printed before loading.


Optional hotwords (development SDK 0.6.0): `python examples/python/transcribe_file.py input.wav --hotword term --hotword "a phrase" --tokenizer /path/to/matching/tokenizer.json`. The SDK owns tokenization and bias. Omit `--hotword` to retain the original decoding path. See `sdk/README.md` for limits, resource requirements and false-trigger tradeoffs.
