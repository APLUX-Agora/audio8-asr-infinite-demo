# SDK examples

Run from the checkout root after [installation](../README.md#1-install) and [model placement](../models/README.md).
The Python programs use this Demo's `.venv`. They read soundfile-supported audio formats, mix channels and resample
to16kHz. Their inference calls use the shipped Python SDK; the C++ example calls the same library's C ABI.

## Python file transcription

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --lang en
```

Outputs text to stdout and processing diagnostics to stderr. This is the bare engine. For long audio with music,
applause or pauses, the streaming example adds the Web Demo's silence gate and soft-reset policy:

```bash
.venv/bin/python examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --lang zh
```

| Option | Program | Meaning |
| --- | --- | --- |
| `--models PACKAGE` | Both | Exact root containing manifest.json; overrides A8_MODELS. Otherwise discover one package in checkout models/. |
| `--clock-ms 160` or `80` | Both | Select the clock installed in that package; default installed clock,160 preferred. |
| `--lang en` or `zh` | Both | Spoken language; default en. |
| `--hotword TERM` | transcribe_file | Repeat for multiple words/phrases; default off. |
| `--tokenizer FILE` | transcribe_file | Optional explicit matching tokenizer; current packages include tokenizer.json. |
| `--hotword-top-k`, `--hotword-start-boost`, `--hotword-continuation-boost` | transcribe_file | Bias settings; defaults50/6/8. See the API reference for limits. |
| `--chunk-ms N` | stream_file | Audio chunk milliseconds; default80. |
| `--eot-horizon N`, `--eot-threshold N` | stream_file | Paragraph end prediction; default2seconds/0.6. |
| `--plain` | stream_file | Disable silence-gate and soft-reset policy. |
| `--fast` | stream_file | Process without real-time pacing. |

```bash
.venv/bin/python examples/python/transcribe_file.py input.wav --lang en --hotword "a phrase"
```

The programs explicitly close on normal completion, errors, SIGTERM and SIGINT. Signal handlers request a stop;
they do not interrupt a synchronous native creation/inference before its handle/result returns.
The helper `python/example_lifecycle.py` belongs to examples, not the SDK. Cooperative signal exits use
128+signal (130 for SIGINT,143 for SIGTERM); cleanup may wait for the current native call.
The helper enables syscall restart for these signals so a stop request does not interrupt native FastRPC waits.

## C++ file transcription

The complete [C++ source](cpp/transcribe_file.cpp) uses the public header and existing prebuilt library;
it is not a new C++ SDK. Input is strictly mono16kHz PCM16 WAV. Build and run on the target board:

```bash
cmake -S examples/cpp -B examples/cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build examples/cpp/build -j2
ffmpeg -i examples/audio/jobs_keynote_10min_16k.flac -ac 1 -ar 16000 -c:a pcm_s16le input.wav
examples/cpp/build/transcribe_file --models models/qnn248_qcs8550 --lang en input.wav
```

Install `g++` and `cmake` if absent. `--clock-ms`, `--lang`, repeated `--hotword` and `--tokenizer` select the
same inference options. `--realtime` paces100ms audio blocks; default is unpaced. A local RAII deleter releases
the native handle on normal return, errors and cooperative signals. See the
[C ABI guide](../sdk/NATIVE_INTEGRATION.md) for direct g++ linking, RPATH, dependencies, every API and ownership.

## Integrating Python

The [Python API reference](../sdk/PYTHON_API.md) documents all Engine calls, parameter defaults, Token/info/stats,
bytes/UTF-8 handling, errors, states and explicit close. Use try/finally, finish/drain once, and reset before the
next stream. `text_of()` returns bytes, not a decoded string. The SDK does not read files, resample or mix channels.

With80ms and160ms installed, keep independent package roots and explicitly pass `--models` to every example.
Changing a package path does not prove chip compatibility. Preserve package checksums/licenses and use a qualified
SDK/runtime pair. Example output/performance is input/platform dependent; no fixed latency is promised.
