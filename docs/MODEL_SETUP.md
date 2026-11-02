# Model setup

Run these commands from the Demo checkout after [installation](../README.md#1-install). Python SDK integration uses the same package roots; no model download is performed by pip or `from_pretrained`.

## Supported targets

| SoC | QNN | TARGET |
| --- | --- | --- |
| QCS8550 | 2.48 | `qcs8550_qnn248` |
| QCS8625 | 2.48 | `qcs8625_qnn248` |
| QCS8275 / IQ8 | 2.48 | `qcs8275_qnn248` |
| QCS9075 / IQ9 | 2.48 | `qcs9075_qnn248` |

Both variants provide these target resources. Native SDK and Python package **0.9.0** support this models.json version 2 layout. Both 80ms and 160ms are qualified on QCS8550 / Ubuntu 22.04 / AidLite 2.5.0.284 / QNN 2.48 with CPython 3.10, 3.11 and 3.12. Other SoC NPU execution and Ubuntu releases remain untested.

Download common resources and exactly one target into each independent package root. The examples below select QCS8550; replace `TARGET` using the table for another board. Both downloads for a variant use its same immutable commit. Authentication is required only while the repository is private or access-controlled; public downloads do not require login.

## 160ms

```bash
.venv/bin/python -m pip install huggingface_hub
REPO=APLUX-Pandora/Audio8-ASR-Infinite-160ms
REV=a3f645da5a4ab0583b4b1376ff76c6f56b91426f
DEST=models/audio8-160ms
TARGET=qcs8550_qnn248
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --exclude "targets/*"
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --include "targets/$TARGET/*"
```

Run the Web Demo (stop an existing instance before reusing its port):

```bash
A8_CLOCK_MS=160 demo/run.sh --models models/audio8-160ms --port 8765
```

Open `http://<board-ip>:8765/`, select a video and press Start. Independent Python examples:

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --models models/audio8-160ms --clock-ms 160 --lang en
.venv/bin/python examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --models models/audio8-160ms --clock-ms 160 --lang zh
```

## 80ms

```bash
.venv/bin/python -m pip install huggingface_hub
REPO=APLUX-Pandora/Audio8-ASR-Infinite-80ms
REV=a06231291d4264bee67cb7eabb0bdde663eb8032
DEST=models/audio8-80ms
TARGET=qcs8550_qnn248
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --exclude "targets/*"
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --include "targets/$TARGET/*"
```

Run the Web Demo (stop the 160ms instance before reusing its port):

```bash
A8_CLOCK_MS=80 demo/run.sh --models models/audio8-80ms --port 8765
```

Open `http://<board-ip>:8765/`, select a video and press Start. Independent Python examples:

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac --models models/audio8-80ms --clock-ms 80 --lang en
.venv/bin/python examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --models models/audio8-80ms --clock-ms 80 --lang zh
```

## Package roots and selection

Each destination directly contains `models.json`, common resources, `SHA256SUMS`, `LICENSES/`, `NOTICE`, and only the downloaded `targets/<soc>_qnn248/`. No extraction or manual file moves are needed. Never overlay the two models into the same directory. Their HF model cards may be downloaded as data-directory READMEs; these installation instructions remain here in `docs/`.

All resource paths come from `models.json` version 2; see the [package contract](../sdk/MODEL_PACKAGE.md). Pass the package root, not its `targets/` directory. Examples/Web prefer explicit `--models` over `A8_MODELS`; without either they discover a flat checkout `models/models.json` or a unique immediate child package. With both models downloaded, select a root explicitly. Restart with the other root to change variants; the Web clock control only offers clocks in the selected root.

The installed SDK in another application requires an explicit model root or `A8_MODELS`; it does not search beside site-packages. For example:

```python
from audio8_asr import ASRModel

with ASRModel.from_pretrained("/absolute/path/to/models/audio8-80ms", clock_ms=80) as model:
    result = model.transcribe("speech.wav", language="en")
    print(result.text)
```

When multiple complete SoC targets are installed in one package, set `A8_TARGET=<soc>_qnn248` at application startup. This selects a declared installation; it does not detect the board or establish hardware compatibility. Normal single-target downloads need no selector.

## Integrity and compatibility

To check downloaded files, from the checkout root:

```bash
(cd models/audio8-160ms && sha256sum --ignore-missing -c SHA256SUMS)
# For 80ms:
(cd models/audio8-80ms && sha256sum --ignore-missing -c SHA256SUMS)
```

`--ignore-missing` permits intentionally absent other-SoC graphs, but verifies present files only; it does not establish package completeness. Web preflight additionally checks configured required resources and hashes before loading/replacing a model. Native loading validates configured paths, required files and raw embedding size; independent SDK calls do not automatically hash every resource. Checksums detect damaged downloads, not an attacker replacing both files and the checksum list.

Use the pinned resources above with this configuration-driven SDK. Legacy SDK releases remain paired with their documented historical revisions; legacy manifest formats 1/2 remain supported, but the prototype models.json version 1 is rejected. No model tensors or graph bytes changed for this documentation update. HF repositories keep only main without Git version tags; reproducibility uses commit IDs.

Silero VAD is bundled in `demo/assets/` for the business-layer silence gate; model semantic VAD remains in the HF package. AidLite/QNN and the board BSP are external prerequisites. See [SDK requirements](../sdk/README.md), [Web usage](../demo/README.md), [Python API](../sdk/PYTHON_API.md) and [C++ examples](../examples/README.md#c-file-transcription).
