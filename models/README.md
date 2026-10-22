# Audio8-ASR-Infinite model packages

ModelFarm MMS is the model-download entry point; this GitHub repository provides the SDK, Python examples and Web Demo. Private HF repositories are backing storage, not a required end-user login step.

## Download through ModelFarm MMS

**Pending publication (2026-10-22):** the model resources are not yet downloadable through MMS. The commands below are prepared for the planned model entries, not successful download verification. Availability, final selectors and archive layout will be reconciled after publication. MMS uses your ModelFarm account; no private Hugging Face token is required.

Run on an APLUX board, from the Demo checkout root:

```bash
# Install MMS if it is not already available.
sudo aid-pkg install aid-mms
mms login
mms list Audio8-ASR-Infinite

# Recommended model: 160ms, QCS8550, QNN 2.48.
mkdir -p downloads/audio8-160ms
mms get -m Audio8-ASR-Infinite-160ms -p w4a16 -c qcs8550 -b qnn2.48 -d downloads/audio8-160ms

# Optional, separate model: 80ms. Keep the download separate.
mkdir -p downloads/audio8-80ms
mms get -m Audio8-ASR-Infinite-80ms -p w4a16 -c qcs8550 -b qnn2.48 -d downloads/audio8-80ms
```

Both command examples use the planned precision `W4A16` and backend `QNN2.48`. The model has mixed-precision components; `W4A16` is the intended MMS resource selector, not a statement that every component has the same precision. Check the actual resource choices with `mms list` once published.

| Board | Prepared `-c` selector | Installed QNN 2.48 package directory |
| --- | --- | --- |
| QCS8550 | `qcs8550` | `qnn248_qcs8550` |
| QCS8625 | `qcs8625` | `qnn248_qcs8625` |
| Dragonwing IQ8 | `qcs8275` | `qnn248_qcs8275` |
| Dragonwing IQ9 | `qcs9075` | `qnn248_qcs9075` |

### Inspect and install the download

MMS may return an archive rather than an extracted model directory. The final archive name and wrapper directories have not been verified; do not guess a ZIP filename or assume `-d` produces a loadable package root.

```bash
find downloads/audio8-160ms -maxdepth 3 -type f
```

If the download is a ZIP archive, set `ARCHIVE` to its **actual** path, inspect its contents, and extract to a staging directory:

```bash
ARCHIVE="downloads/audio8-160ms/<actual-archive-name>.zip"
unzip -l "$ARCHIVE"
mkdir -p downloads/audio8-160ms-extracted
unzip "$ARCHIVE" -d downloads/audio8-160ms-extracted
find downloads/audio8-160ms-extracted -name manifest.json -print
```

For another archive format, use its matching extraction tool. If MMS already returned files, inspect them directly. Locate the directory that directly contains `manifest.json` and copy that **entire package directory**, retaining checksums, tokenizer, graph/tensor files and licenses, into `models/qnn248_<chip>/`. For QCS8550, a single installed package must have this result:

```text
models/qnn248_qcs8550/manifest.json
models/qnn248_qcs8550/SHA256SUMS
models/qnn248_qcs8550/common/
models/qnn248_qcs8550/160ms/        # 80ms/ for the separate 80ms model
```

Verify integrity after placing the complete package:

```bash
(cd models/qnn248_qcs8550 && sha256sum -c SHA256SUMS)
```

SDK/examples/Web automatically discover one installed package. To keep both models, use separate roots such as `models/audio8-160ms-qcs8550/` and `models/audio8-80ms-qcs8550/`, each directly containing its own manifest. Select one explicitly:

```bash
demo/run.sh --models models/audio8-160ms-qcs8550 --port 8765
# Or use the separate 80ms package:
demo/run.sh --models models/audio8-80ms-qcs8550 --port 8765
```

Do not merge the two downloads into one package, overwrite one model's manifest with the other, or copy only the NPU graphs.

## Model repositories and layout

These are two distinct models with separate private repositories:

- `APLUX-GenAI4/Audio8-ASR-Infinite-160ms`
- `APLUX-GenAI4/Audio8-ASR-Infinite-80ms`

Within each repository, `qnn248_qcs8550/` is the model package for QCS8550 / QNN 2.48. Keep its full contents: the manifest, common files, clock-specific graphs/prefix caches, tokenizer, checksums and licenses. This migration does not modify graph or tensor bytes. Use MMS once the model resources are published.

For one model, place its package at `models/qnn248_qcs8550/manifest.json`; SDK/examples/Web discover it automatically. To keep both models, use separate package roots and pass the desired one explicitly with `--models`. Do not overwrite one model's manifest with the other model's manifest or add an unreferenced second clock directory.

## Model paths and validation

SDK, examples and Web share model discovery, anchored to this checkout. An explicit `--models` or `A8_MODELS` value must point directly at the manifest. Multiple immediate child packages require an explicit path. Discovery does not prove hardware compatibility or file integrity.

Keep every required graph, tensor, vocabulary, prefix cache, configuration and license. The Web application verifies manifest targets and checksums before loading. SDK 0.6.0 uses the single-file prefix-cache format; 0.4.x per-layer packages are incompatible. Model bytes are unchanged by the real-name SDK migration. Exact HF resource revisions are recorded in the internal release pairing.

## Layout

`manifest.json` lists the files of each audio clock; the SDK loads exactly these files and reports a clear error when
one is missing or does not match the model. The SDK, the examples and the web demo use the installed clocks only
(160 ms first).

```
qnn248_<chip>/                   one model package (the SDK's model directory)
├── manifest.json                the files of each audio clock (read by the SDK)
├── SHA256SUMS                   checksums of all files
├── common/                      shared by both audio clocks
│   ├── embedding.npy            token embedding table (CPU lookup)
│   ├── rotation.npy             rotation used when the 30 s context rolls
│   ├── mel_filters.npy          mel filterbank
│   ├── token_bytes.json         UTF-8 bytes of every token
│   ├── vad/                     end-of-turn heads (W.npy, b.npy, meta.json)
│   └── silero_vad.onnx          Silero VAD v5 (silence gate of the demo and of stream_file.py, not the SDK)
└── 160ms/                       80ms/ instead in the separate 80ms model package
    ├── frontend/                config.json (streaming configuration), rows_const.npy (constant audio rows)
    ├── encoder/                 encoder + adapter (NPU, encrypted .aidem), prefix_kv.bin (constant prefix)
    └── decoder/                 part_1_of_2 + part_2_of_2 (NPU, encrypted .aidem), prefix_kv_zh.bin, prefix_kv_en.bin
```

The NPU models are QNN context binaries, encrypted (`*.serialized.bin.aidem`); AidLite decrypts them when it loads
them. The constant prefixes (`prefix_kv*.bin`) are KV cache files in the layout of the Qualcomm Genie KV cache
(16-byte header, then the keys and the values of all layers), with float32 data.


## Licensing

Keep upstream model attribution and all applicable licenses, including the distributor's scoped model-adaptation terms, with the downloaded package. Required notices are part of the model resource, not a replacement for its files.
