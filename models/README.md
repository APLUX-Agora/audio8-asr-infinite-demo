# Model setup

This integration candidate uses the root `models.json` from HF. It supports the flat model package; SDK 0.7.1 uses its previous pinned resources instead. The candidate is not a formal SDK release.

| Model | HF repository | Candidate revision |
| --- | --- | --- |
| 160ms | [Audio8-ASR-Infinite-160ms](https://huggingface.co/APLUX-Pandora/Audio8-ASR-Infinite-160ms) | `03a93fff6ce4993a701d8c172261355cbe6f1217` |
| 80ms | [Audio8-ASR-Infinite-80ms](https://huggingface.co/APLUX-Pandora/Audio8-ASR-Infinite-80ms) | `ee036e11a7744164bfbc981ad353331cecc41692` |

## Download for one SoC

Run from this Demo checkout, using its own installed `.venv`:

```bash
.venv/bin/python -m pip install huggingface_hub
REPO=APLUX-Pandora/Audio8-ASR-Infinite-160ms
REV=03a93fff6ce4993a701d8c172261355cbe6f1217
DEST=models
TARGET=qcs8550_qnn248
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --exclude "targets/*"
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --include "targets/$TARGET/*"
```

Targets: `qcs8550_qnn248`, `qcs8625_qnn248`, `qcs8275_qnn248` (IQ8), `qcs9075_qnn248` (IQ9). Choose the target for your actual board. The SDK selects the unique completely installed target; that selection is not hardware identification. If multiple targets are installed, explicitly set `A8_TARGET=qcs8550_qnn248` before starting the application. Unknown or incomplete selections fail without falling back.

The first command obtains root files plus frontend/, prefix/, semantic_vad/ and licenses; the second obtains only one target. Both commands must use the same fixed revision. The repository's existing access permissions apply; future public repositories use the same commands.

```text
models/
  models.json
  embedding.bin
  tokenizer.json
  token_bytes.json
  mel_filters.npy
  rotation.npy
  frontend/
  prefix/
  semantic_vad/
  targets/qcs8550_qnn248/
    encoder.aidem
    adapter.aidem
    decoder_1.aidem
    decoder_2.aidem
    SHA256SUMS
  LICENSES/
  NOTICE
  SHA256SUMS
```

## Package selection and checks

Demo and examples use the installed SDK's discovery: a root models.json (or legacy manifest.json) takes precedence, otherwise exactly one immediate child package is required. Explicit `--models` / `A8_MODELS` points to that package root. No selection is guessed from the working directory or a deeper folder. To keep both 80ms and 160ms, download into separate roots such as models/80ms/ and models/160ms/, and explicitly select one with `--models models/80ms`. Do not overlay the two repositories into the same destination.

For a selected download, `sha256sum --ignore-missing -c SHA256SUMS` checks present files only; it does not detect absent required files. Web preflight uses SDK resource resolution and hashes every required file before replacing a loaded engine. Native loading additionally validates required files, target metadata and the exact raw embedding size. Checksums are not authenticated signatures.

The [candidate package contract](../sdk/MODEL_PACKAGE.md) records the provisional fields. Model bytes and inference arithmetic are unchanged. Legacy format-1/2 manifests remain supported by the candidate SDK; old SDK versions cannot load models.json directly. Runtime qualification is limited to the board/variants in the integration report, not every resource directory.
