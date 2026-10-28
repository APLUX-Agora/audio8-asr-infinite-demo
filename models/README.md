# Model setup

Download the complete package for your SoC directly from Hugging Face. Run all commands from
this Demo's repository root, after creating its `.venv` as described in [installation](../README.md#1-install).
The commands below assume public repository access and do not require a login or token.

## Model repositories and fixed revisions

| Model | Repository | Resource revision |
| --- | --- | --- |
| 160ms (recommended) | [APLUX-Pandora/Audio8-ASR-Infinite-160ms](https://huggingface.co/APLUX-Pandora/Audio8-ASR-Infinite-160ms) | `ce6c6a646e962b75640bfba20e97bffeb4928b06` |
| 80ms | [APLUX-Pandora/Audio8-ASR-Infinite-80ms](https://huggingface.co/APLUX-Pandora/Audio8-ASR-Infinite-80ms) | `3128332fba287510dc7137bb2fef63d3a9398097` |

These resource snapshots are the download baseline for SDK 0.7.0. Each repository has separate
QNN 2.48 packages for the four SoCs below. File availability does not establish runtime qualification:
current SDK 0.7.0 NPU validation covers QCS8550 / Ubuntu 22.04 / 160ms.

## Download one SoC package

Install the Hugging Face CLI in this Demo's environment:

```bash
.venv/bin/python -m pip install huggingface_hub
```

Choose the directory that matches your board:

| Board | `PACKAGE` |
| --- | --- |
| QCS8550 | `qnn248_qcs8550` |
| QCS8625 | `qnn248_qcs8625` |
| IQ8 / QCS8275 | `qnn248_qcs8275` |
| IQ9 / QCS9075 | `qnn248_qcs9075` |

For example, download the 160ms package for QCS8550:

```bash
PACKAGE=qnn248_qcs8550  # Replace with your board's directory from the table.
.venv/bin/hf download APLUX-Pandora/Audio8-ASR-Infinite-160ms \
  --revision ce6c6a646e962b75640bfba20e97bffeb4928b06 \
  --include "$PACKAGE/**" --local-dir models
(cd "models/$PACKAGE" && sha256sum -c SHA256SUMS)
```

The quoted include pattern downloads the entire selected package, including nested model files,
manifest, tokenizer, shared tensors, prefix caches, checksums and licenses. Other SoC packages
are excluded. Allow about 3.6 GB per package, plus runtime working space.
Hugging Face preserves the repository-relative directory; there is no ZIP extraction or manual move:

```text
models/
└── qnn248_qcs8550/
    ├── manifest.json
    ├── SHA256SUMS
    ├── tokenizer.json
    ├── README.md
    ├── common/
    ├── 160ms/
    └── ...                         licenses and notices
```

The directory directly containing `manifest.json` is the package root. Keep every file and
check that all checksum entries pass before starting the SDK or Demo. Downloading files
successfully does not establish that they can run on your board/runtime.

## Use the 80ms model

For an 80ms-only installation, start with no other model package in `models/`, then use its
separate repository and revision. Do not download it over an installed 160ms package:

```bash
PACKAGE=qnn248_qcs8550  # Select your board's directory.
.venv/bin/hf download APLUX-Pandora/Audio8-ASR-Infinite-80ms \
  --revision 3128332fba287510dc7137bb2fef63d3a9398097 \
  --include "$PACKAGE/**" --local-dir models
(cd "models/$PACKAGE" && sha256sum -c SHA256SUMS)
```

Its package has `80ms/` instead of `160ms/`. The Python examples and Web Demo discover one
package in their checkout automatically. Independent SDK callers pass a package root or set `A8_MODELS`.

## Keep both models

The two repositories use the same SoC directory names. Give each download a separate destination
and explicitly select its package root, so their manifests and common files cannot overwrite each other:

```bash
PACKAGE=qnn248_qcs8550
.venv/bin/hf download APLUX-Pandora/Audio8-ASR-Infinite-160ms \
  --revision ce6c6a646e962b75640bfba20e97bffeb4928b06 \
  --include "$PACKAGE/**" --local-dir models/audio8-160ms
.venv/bin/hf download APLUX-Pandora/Audio8-ASR-Infinite-80ms \
  --revision 3128332fba287510dc7137bb2fef63d3a9398097 \
  --include "$PACKAGE/**" --local-dir models/audio8-80ms
(cd "models/audio8-160ms/$PACKAGE" && sha256sum -c SHA256SUMS)
(cd "models/audio8-80ms/$PACKAGE" && sha256sum -c SHA256SUMS)

demo/run.sh --models "models/audio8-160ms/$PACKAGE" --port 8765
# Or run an example with the 80ms package:
.venv/bin/python examples/python/transcribe_file.py \
  --models "models/audio8-80ms/$PACKAGE" examples/audio/jobs_keynote_10min_16k.flac --lang en
```

These package roots are nested two levels below `models/`, so pass `--models` explicitly;
automatic discovery only accepts a flat package or one unique immediate child package.
`A8_MODELS` is also supported by the launchers/examples; explicit `--models` takes precedence.
For direct Python integration, pass the package root to `ASRModel.from_pretrained`.
Do not merge manifests or copy only the NPU graphs. SDK 0.7.0 retains the single-file prefix-cache
package layout; old 0.4.x per-layer prefix caches are incompatible. See the [SDK guide](../sdk/README.md).
