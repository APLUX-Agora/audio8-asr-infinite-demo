# SDK examples

Run from the checkout root after [installation](../docs/AGORA_DEPLOY.md#3-set-up-dependencies) and [model placement](../docs/MODEL_SETUP.md).
The Python programs use this Demo's `.venv` and its pip-installed SDK; they do not import SDK files from the checkout. They use the editable SDK audio adapter for WAV/FLAC/MP3, mono/stereo conversion and 16kHz resampling. More than two channels require explicit selection in application code. Their inference calls use the shipped Python SDK; the C++ example calls the same library's C ABI.

## Python file transcription

For the first run, use the 20-second sample. It prints model loading / transcribing / complete phases; the transcript is returned at the end. Set --models explicitly for a model package outside the checkout; follow the [Agora guide](../docs/AGORA_DEPLOY.md).

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/quickstart_en_20s.wav --lang en
```

Outputs text to stdout and application diagnostics to stderr. AidLite/RPC may also emit
vendor notices to stdout/stderr; stdout is not a machine-only transcript protocol.
For programmatic integration use the SDK's returned text. This is the bare engine. For long audio with music,
applause or pauses, the streaming example adds the Web Demo's silence gate and soft-reset policy.
The gate loads the bundled `demo/assets/silero_vad.onnx`; it does not require a VAD file in the HF package:

```bash
.venv/bin/python examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --lang zh
```

| Option | Program | Meaning |
| --- | --- | --- |
| `--models PACKAGE` | Both | Exact root containing models.json (or a supported legacy manifest.json); overrides A8_MODELS. Otherwise discover one package in checkout models/. |
| `--clock-ms 160` or `80` | Both | Select the clock installed in that package; default installed clock,160 preferred. |
| `--lang en` or `zh` | Both | Explicit language. File example defaults to the model default zh; streaming presentation example defaults to en. |
| `--max-new-tokens N` | transcribe_file | Positive generation cap, including controls; result reports stop/length. |
| `--hotword TERM` | transcribe_file | Repeat for multiple words/phrases; default off. |
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
examples/cpp/build/transcribe_file --models models/audio8-160ms --clock-ms 160 --lang en input.wav
# Alternatively, after downloading the 80ms package:
examples/cpp/build/transcribe_file --models models/audio8-80ms --clock-ms 80 --lang en input.wav
```

Install `g++` and `cmake` if absent. `--clock-ms`, `--lang`, repeated `--hotword` and `--tokenizer` select the
same inference options. `--realtime` paces100ms audio blocks; default is unpaced. A local RAII deleter releases
the native handle on normal return, errors and cooperative signals. See the
[C ABI guide](../sdk/NATIVE_INTEGRATION.md) for direct g++ linking, RPATH, dependencies, every API and ownership.

## Integrating Python

The [Python API reference](../sdk/PYTHON_API.md) documents `ASRModel.from_pretrained`,
`transcribe`, `create_stream`, complete/update results, capabilities and exceptions.
The stream example keeps VAD/endpoint/replay presentation in the business layer while owning a model and recording context.
Audio conversion is public Python code; inference remains in the same native library.

With80ms and160ms installed, keep independent package roots and explicitly pass `--models` to every example.
Changing a package path does not prove chip compatibility. Preserve package checksums/licenses and use a qualified
SDK/runtime pair. Example output/performance is input/platform dependent; no fixed latency is promised.

## Root models.json configuration

SDK 0.7.2 (native 0.7.2) resolves common resources and target graphs from models.json version 2. Pass the root containing models.json; see the [model setup](../docs/MODEL_SETUP.md) and [package contract](../sdk/MODEL_PACKAGE.md). Legacy manifests remain supported. Both 80ms and 160ms are qualified on QCS8550 / Ubuntu 22.04 / AidLite 2.5.0.284 / QNN 2.48 with CPython 3.10, 3.11 and 3.12. Other SoC NPU execution and Ubuntu releases remain untested.

## AidLite Runtime configuration (SDK0.8.0)

The [C Runtime client](c/runtime_example.c) demonstrates the unified configuration
contract, model binding, support/submission queries and explicit cleanup. On the
Linux AArch64 board, from the repository root:

```bash
cc -std=c11 -I sdk/include examples/c/runtime_example.c -L sdk/lib \
  -Wl,-rpath,"$PWD/sdk/lib" -laudio8_asr -o /tmp/audio8-runtime-example
/tmp/audio8-runtime-example /path/to/Audio8-ASR-Infinite-80ms 80
/tmp/audio8-runtime-example /path/to/Audio8-ASR-Infinite-160ms 160
```

Both variants use the same SDK. See [Runtime options](../sdk/RUNTIME.md) for Python
usage, accepted values and defaults, and reserved options that are not forwarded
to AidLite in this version.

## CPU placement

SDK CPU affinity defaults to `inherit`; official Demo/file launchers explicitly use
`default`. Python `Runtime(cpu=CpuOptions(affinity=...))` and the C Runtime accept
inherit/default/explicit CPU IDs for both 80ms and 160ms. See the
[Python/C CPU options reference](../sdk/CPU_AFFINITY.md) for values, platform profiles,
CLI commands, ownership and actual-thread status queries.

The C++ file example also accepts `--cpu-affinity inherit`, `default` or a comma-separated CPU list. The C Runtime client takes an optional final CPU ID; without it the example chooses the default profile.
