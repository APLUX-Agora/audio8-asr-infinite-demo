# Audio8-ASR-Infinite Demo

Streaming speech recognition on Qualcomm devices, powered by Edge0's [Audio8-ASR-Infinite](https://huggingface.co/Edge0/Audio8-ASR-Infinite). Includes a Web Demo, Python examples and C++ integration example.

[Pandora](https://pandora.aidlux.com/en/demos/live-transcribe-01/) · [ModelFarm](https://aiot.aidlux.com/en/models?name=Audio8)

[![Watch the demo video](docs/demo-poster.jpg)](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549)

[Watch video](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549) · [Download recording](docs/demo.mp4)

Source: Lorna Mitchell, FOSDEM 2025, **CC BY 2.0 BE**. Original credits are retained; the excerpt is trimmed and transcoded. [Source, license and changes](docs/MEDIA_ATTRIBUTION.md).

## 1. Install

Run on a supported Linux AArch64 AidLux board (Python 3.10 tested).

```bash
git clone https://github.com/APLUX-Pandora/audio8-asr-infinite-demo.git
cd audio8-asr-infinite-demo
sudo aid-pkg install aidlite-sdk aidlite-qnn248 aid-mms
sudo apt install ffmpeg libsndfile1 python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 2. Get the model

From the repository root, download the **160ms / QCS8550** model into `models/`:

```bash
mms login
mms list Audio8-ASR-Infinite
mms get -m Audio8-ASR-Infinite-160ms -p w4a16 -c qcs8550 -b qnn2.48 -d models
```

If MMS returns an archive, extract it under `models/`. The installed package should have
`models/qnn248_qcs8550/manifest.json`. Verify it before running:

```bash
(cd models/qnn248_qcs8550 && sha256sum -c SHA256SUMS)
```

For another chip, the 80ms model or extraction details, see [model setup](models/README.md).
MMS selectors are prepared for publication; the catalog entry and download have not been verified.

## 3. Run the Web Demo

```bash
demo/run.sh --port 8765
```

Open `http://<board-ip>:8765/`. Select a built-in video or upload your own.
See the [Web guide](demo/README.md) for hotwords and other controls.

## 4. Run a Python example

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --lang en
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
