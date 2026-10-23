# Model setup

Run all commands from the Demo repository root. Download the complete package for your chip;
keep its manifest, tokenizer, weights, shared files, checksums and licenses together.

## Download and extract

The main README uses the 160ms model on QCS8550:

```bash
mms login
mms list Audio8-ASR-Infinite
mms get -m Audio8-ASR-Infinite-160ms -p w4a16 -c qcs8550 -b qnn2.48 -d models
```

`-d models` saves the download inside this checkout's model directory. If MMS returns a ZIP,
use its actual filename and extract there:

```bash
ls models
unzip models/<downloaded-file>.zip -d models
```

Use the matching extraction tool for other archive formats. The installed layout must be:

```text
models/
└── qnn248_qcs8550/
    ├── manifest.json
    ├── SHA256SUMS
    ├── tokenizer.json
    ├── common/
    ├── 160ms/
    └── ...                         licenses and notices
```

If the archive has extra wrapper directories, move the entire directory containing `manifest.json`
to `models/qnn248_qcs8550/`; do not copy only the model graphs. Check integrity:

```bash
(cd models/qnn248_qcs8550 && sha256sum -c SHA256SUMS)
```

The MMS catalog entry, selectors and archive layout remain unverified. Use `mms list` to confirm
the published resource choices; the command above is prepared for publication. MMS uses your
ModelFarm account; users do not need a private Hugging Face token.

## Other chips and the 80ms model

Change `-c` to match your board:

| Board | `-c` | Package directory |
| --- | --- | --- |
| QCS8550 | `qcs8550` | `qnn248_qcs8550` |
| QCS8625 | `qcs8625` | `qnn248_qcs8625` |
| IQ8 / QCS8275 | `qcs8275` | `qnn248_qcs8275` |
| IQ9 / QCS9075 | `qcs9075` | `qnn248_qcs9075` |

For 80ms, select `-m Audio8-ASR-Infinite-80ms`; its package contains `80ms/` instead of `160ms/`.
The `w4a16` selector identifies the planned mixed-precision resource, not every individual component.
Resources exist for all four chips; current runtime qualification covers QCS8550 / Ubuntu22.04 / 160ms.

## Selecting a package

One installed package is discovered automatically. To keep both models, download/extract them
into separate subdirectories under `models/`, preserving each complete package. Pass the directory
that directly contains the desired `manifest.json`:

```bash
demo/run.sh --models <package-root> --port 8765
.venv/bin/python examples/python/transcribe_file.py --models <package-root> input.wav
```

The same path can be set using `A8_MODELS`. Explicit `--models` takes precedence. Do not merge
80ms/160ms manifests or overwrite one package with the other. Use the current SDK0.6.x package format;
old0.4.x per-layer prefix caches are incompatible. See the [SDK guide](../sdk/README.md).
