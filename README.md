# Audio8-ASR-Infinite · Real-time on-device transcription

**Turn continuous speech into text, directly on your device.**

[Audio8-ASR-Infinite](https://huggingface.co/Edge0/Audio8-ASR-Infinite), developed by Edge0, powers this Pandora solution for meeting transcription, live captions, and embedded voice applications. It combines a ready-to-use inference SDK, runnable examples, a web demo, and matching model packages for Qualcomm platforms.

[Explore the demo on Pandora](https://pandora.aidlux.com/en/demos/live-transcribe-01/) · [Get the code on GitHub](https://github.com/APLUX-Pandora/audio8-asr-infinite-demo) · [Get the models on ModelFarm](https://aiot.aidlux.com/en/models?name=Audio8)

## Demo

https://github.com/user-attachments/assets/97a0599d-f6f0-4725-9093-da80a8d94b55

[Download the full-quality recording](docs/demo.mp4)

Source: Lorna Mitchell, FOSDEM 2025, **CC BY 2.0 BE**. Original credits are retained; the excerpt is trimmed and transcoded. [Source, license and changes](docs/MEDIA_ATTRIBUTION.md).

The Web Demo plays built-in or uploaded video and shows streaming transcription. The same inference library
also supports standalone Python and C++ file integration.

## Install

This repository is currently private; use an authorized GitHub account. On a Linux AArch64 AidLux board,
clone it first, then install platform prerequisites and a project-local Python environment (Python3.10 tested):

```bash
git clone https://github.com/APLUX-Pandora/audio8-asr-infinite-demo.git
cd audio8-asr-infinite-demo
sudo aid-pkg install aidlite-sdk aidlite-qnn248
sudo apt install ffmpeg libsndfile1 python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

Use your supported platform runtime; do not replace shared board drivers/runtime packages for this Demo.
System/SDK compatibility and native loader requirements are in the [SDK guide](sdk/README.md).

## Get and place a model

Obtain the model from ModelFarm MMS using your ModelFarm account; no private HF token is required.
The following selectors are prepared; catalog publication, downloads and archive layout are **not verified**:

```bash
sudo aid-pkg install aid-mms
mms login
mms list Audio8-ASR-Infinite
mms get -m Audio8-ASR-Infinite-160ms -p w4a16 -c qcs8550 -b qnn2.48 -d downloads/audio8-160ms
```

Choose your chip and the separate80ms/160ms model. Copy the **complete** extracted package so its manifest
is at `models/qnn248_qcs8550/manifest.json` for QCS8550. Check its `SHA256SUMS`.
[Model instructions](models/README.md) cover the four resource targets,80ms selection and keeping both packages.
QCS8550/QCS8625/IQ8(QCS8275)/IQ9(QCS9075) packages are present; resource availability is separate from the
QCS8550/Ubuntu22.04/160ms runtime qualification.

## Run the Web Demo

```bash
demo/run.sh --port 8765
```

Open `http://<board-ip>:8765/`. The launcher uses this checkout's `.venv`.
One package is discovered automatically; multiple packages require `--models PACKAGE_ROOT`.
[Web guide](demo/README.md) covers controls, hotwords and graceful shutdown.

## Use Python examples

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --lang en
.venv/bin/python examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --lang zh
```

[Examples](examples/README.md) explain file/stream options, hotwords and the compilable C++ example.
Use the [Python API reference](sdk/PYTHON_API.md) for integration and the
[C ABI integration guide](sdk/NATIVE_INTEGRATION.md) for native calls/build/linking. Both use the same `.so`.

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
