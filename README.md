# Audio8-ASR-Infinite Demo

Streaming speech recognition on Qualcomm devices, powered by Edge0's [Audio8-ASR-Infinite](https://huggingface.co/Edge0/Audio8-ASR-Infinite). Includes a Web Demo, Python examples and C++ integration example.

[Pandora](https://pandora.aidlux.com/en/demos/live-transcribe-01/) · [ModelFarm](https://aiot.aidlux.com/en/models?name=Audio8)

[![Watch the demo video](docs/demo-poster.jpg)](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549)

[Watch video](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549) · [Download recording](docs/demo.mp4)

Source: Lorna Mitchell, FOSDEM 2025, **CC BY 2.0 BE**. Original credits are retained; the excerpt is trimmed and transcoded. [Source, license and changes](docs/MEDIA_ATTRIBUTION.md).

SDK version 0.9.0 supports the configurable models.json version 2 package.

## 1. Install

Choose one installed CPython interpreter: **3.10, 3.11 or 3.12**. All three were verified on QCS8550 / Ubuntu 22.04 AArch64 with the same SDK and model package. The selected interpreter must provide the `venv` module; the `python3-venv` package supplies it for Ubuntu's default Python. Validation covered both the 80ms and 160ms models; see [SDK compatibility](sdk/README.md#compatibility).

```bash
git clone https://github.com/APLUX-Pandora/audio8-asr-infinite-demo.git
cd audio8-asr-infinite-demo
sudo aid-pkg install aidlite-sdk aidlite-qnn248
sudo apt install ffmpeg libsndfile1 python3-venv
DEMO_PYTHON=python3.10  # Or python3.11 / python3.12; choose one installed interpreter.
"$DEMO_PYTHON" -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

`requirements.txt` also installs the matched Python SDK into this Demo's `.venv`.
For integration in another application, see [SDK installation](sdk/PYTHON_PACKAGE.md).

## 2. Get the model

The recommended configuration is **160ms / QCS8550**:

```bash
.venv/bin/python -m pip install huggingface_hub
REPO=APLUX-Pandora/Audio8-ASR-Infinite-160ms
REV=a3f645da5a4ab0583b4b1376ff76c6f56b91426f
DEST=models/audio8-160ms
TARGET=qcs8550_qnn248
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --exclude "targets/*"
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --include "targets/$TARGET/*"
```

The entry point is `models/audio8-160ms/models.json`; other SoC graphs are not downloaded.
For complete **80ms and 160ms** download/startup/example steps and other SoCs, see [model setup](docs/MODEL_SETUP.md). Silero VAD is bundled with the Demo.

## 3. Run the Web Demo

```bash
A8_CLOCK_MS=160 demo/run.sh --models models/audio8-160ms --port 8765
```

Open `http://<board-ip>:8765/`. Select a built-in video or upload your own.
See the [Web guide](demo/README.md) for hotwords and other controls.

## 4. Run a Python example

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --models models/audio8-160ms --clock-ms 160 --lang en
```

For streaming, Chinese audio and the compilable C++ example, see [examples](examples/README.md).

## API reference

- [Python SDK API](sdk/PYTHON_API.md)
- [C ABI integration and C++ build instructions](sdk/NATIVE_INTEGRATION.md)
- [SDK requirements and compatibility](sdk/README.md)

## License

See [LICENSING.md](LICENSING.md) for component scopes, [LICENSE](LICENSE) for the license index,
and [NOTICE](NOTICE) for attribution. Demo/example code and public interfaces use Apache-2.0;
the precompiled SDK and model adaptations are subject to the
[Pandora Model and SDK License](LICENSES/Pandora-Model-SDK.en.txt) and applicable upstream terms.

## Hardware runtime configuration

Python and C callers configure hardware through Pandora Runtime/CpuOptions/QnnOptions,
separately from model generation settings. AidLite remains the inference backend.
See [Runtime options, support status and ownership](sdk/RUNTIME.md): supported
profiles/control latency are forwarded; priority/polling and system_settings are
reserved and explicitly reported as inactive in this provider.

CPU placement: SDK default `inherit`; official Web/file launchers explicitly
choose `default`. Both audio clocks accept `--cpu-affinity inherit`, `default`,
or comma-separated CPU IDs. See the [Python/C CPU reference](sdk/CPU_AFFINITY.md)
for platform profiles, native worker coverage and observed-thread status.
