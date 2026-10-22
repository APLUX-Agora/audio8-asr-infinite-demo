# Audio8-ASR-Infinite · Real-time on-device transcription

**Turn continuous speech into text, directly on your device.**

[Audio8-ASR-Infinite](https://huggingface.co/Edge0/Audio8-ASR-Infinite), developed by Edge0, powers this Pandora solution for meeting transcription, live captions, and embedded voice applications. It combines a ready-to-use inference SDK, runnable examples, a web demo, and matching model packages for Qualcomm platforms.

[Explore the demo on Pandora](https://pandora.aidlux.com/en/demos/live-transcribe-01/) · [Get the code on GitHub](https://github.com/APLUX-Pandora/audio8-asr-infinite-demo) · [Get the models on ModelFarm](https://aiot.aidlux.com/en/models?name=Audio8)

## What you can do

- Transcribe speech as audio arrives, with continuous streaming for long sessions.
- Work with Chinese and English using the same SDK.
- Segment the transcript when a speaker finishes a turn.
- Run inference locally on the board's NPU, without cloud inference or a GPU.
- Integrate through a C API or Python binding, or start with the web demo.

## Demo

https://github.com/user-attachments/assets/97a0599d-f6f0-4725-9093-da80a8d94b55

[Download the full-quality recording](docs/demo.mp4)

Source: Lorna Mitchell, FOSDEM 2025, **CC BY 2.0 BE**. Original credits are retained; the excerpt is trimmed and transcoded. [Source, license and changes](docs/MEDIA_ATTRIBUTION.md).

The web demo plays a built-in or uploaded video while the board transcribes its audio. Watch the transcript, end-of-turn prediction, and board load update in real time.

## Supported hardware

| Hardware | Model folder | Status |
| --- | --- | --- |
| Qualcomm QCS8550 | `qnn248_qcs8550` | Available |
| Qualcomm QCS8625 | `qnn248_qcs8625` | Available |
| Qualcomm Dragonwing IQ8 (QCS8275) | `qnn248_qcs8275` | Available |
| Qualcomm Dragonwing IQ9 (QCS9075) | `qnn248_qcs9075` | Available |
| Qualcomm Dragonwing IQ10 | — | Coming soon |

Download the ModelFarm package matching your board. The prebuilt SDK is shared across these supported chips; model packages are chip-specific.

## Run the demo

This repository contains the application code, Python examples, and prebuilt SDK. Obtain model packages separately through ModelFarm MMS; a private Hugging Face token is not required.

## Setup

Once, on the board (AidLux image):

**1. This repository**:

```bash
git clone https://github.com/APLUX-Pandora/audio8-asr-infinite-demo.git && cd audio8-asr-infinite-demo
```

**2. Inference runtime**: AidLite and its QNN 2.48 backend.

```bash
sudo aid-pkg install aidlite-sdk
sudo aid-pkg install aidlite-qnn248
```

**3. System packages**: ffmpeg (ffprobe checks uploaded videos in the web demo) and libsndfile (audio file reading).

```bash
sudo apt install ffmpeg libsndfile1 libicu70 python3-venv
```

**4. Isolated Python environment** (Python 3.10 tested): each demo has its own `.venv`.
Do not install this demo into system Python or reuse another demo’s environment.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

## Quick start

On the board, from the root of this repository:

**1. Get the model through ModelFarm MMS.**

**Pending publication:** the MMS model resources are not published yet. The commands below are prepared for the planned entries and will only work after publication; they are not verified download results.

On an APLUX board, install MMS if needed, log in with your ModelFarm account, and request the recommended 160ms model:

```bash
sudo aid-pkg install aid-mms
mms login
mms list Audio8-ASR-Infinite
mkdir -p downloads/audio8-160ms
mms get -m Audio8-ASR-Infinite-160ms -p w4a16 -c qcs8550 -b qnn2.48 -d downloads/audio8-160ms
```

For the separate 80ms model, use a different download directory:

```bash
mkdir -p downloads/audio8-80ms
mms get -m Audio8-ASR-Infinite-80ms -p w4a16 -c qcs8550 -b qnn2.48 -d downloads/audio8-80ms
```

Replace `qcs8550` with the chipset matching your board. The other prepared selectors are `qcs8625`, `qcs8275` (IQ8), and `qcs9075` (IQ9). These commands use the planned `W4A16` / `QNN2.48` selections; confirm the published choices with `mms list` when resources become available.

Inspect the download and extract an archive if MMS returns one. Install the **complete** package so the manifest is at `models/qnn248_qcs8550/manifest.json` for QCS8550 / QNN 2.48 (or the corresponding chip directory). Do not assume MMS downloads directly into a ready-to-load layout. See [models/README.md](models/README.md) for extraction, package placement and keeping both models separately. No HF login/token is needed for the intended MMS workflow.

**2. Start the Web Demo**. With one downloaded package, no model-path option is needed:

```bash
demo/run.sh --port 8765
```

Open `http://<board-ip>:8765/`. The launcher always uses this checkout's `.venv`; shell activation is not required.

**Or transcribe a file through the same Python SDK:**

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --lang en
.venv/bin/python examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --lang zh
```

The SDK/examples/Web share model discovery: a flat `models/manifest.json` remains supported; otherwise one immediate
chip package is selected. Multiple packages require explicit selection, for example `demo/run.sh --models models/qnn248_qcs8550`
or `--models models/qnn248_qcs8550` on a Python example. Explicit paths must directly contain the manifest and never silently
fall back to another package. Relative explicit paths are interpreted from the caller's working directory; automatic
paths are anchored to this checkout. A directory name alone does not prove hardware compatibility.

## Learn more

| | |
|---|---|
| [demo/README.md](demo/README.md) | the web demo: start-up options and what every control on the page does |
| [examples/README.md](examples/README.md) | the Python examples and how to use the SDK in your own code |
| [sdk/README.md](sdk/README.md) | the C API and the Python binding |
| [models/README.md](models/README.md) | how to get the model files |

## License

This repository contains components with different licenses. See [LICENSING.md](LICENSING.md)
for the exact file scope and [LICENSE](LICENSE) for the licensing index.

- APLUX-authored Demo frontends, business logic, examples, C API headers and Python bindings:
  [Apache-2.0](LICENSES/Apache-2.0.txt).
- APLUX proprietary contributions in the precompiled SDK libraries:
  [Pandora Model and SDK License (English)](LICENSES/Pandora-Model-SDK.en.txt) /
  [Pandora Model and SDK License (Chinese)](LICENSES/Pandora-Model-SDK.zh-CN.txt).
- Model files and third-party software, runtime components and media: their own applicable
  licenses, as described in [NOTICE](NOTICE) and [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

Free APLUX permission covers evaluation, development, demonstrations, small-device
pilots and paid PoCs. Charging for development, integration or validation alone does
not require a commercial APLUX license. Volume production, sales, deliveries or
production deployment at scale require prior written commercial authorization.
Reverse engineering of APLUX proprietary SDK binaries is prohibited, subject to the
agreement's exceptions. Applicable upstream restrictions must still be satisfied.
