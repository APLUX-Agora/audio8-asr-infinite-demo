# Model resources and directories

Declare repositories, target, and paths in agora.env. Source it once, then run standard commands. See the [deployment guide](AGORA_DEPLOY.md).

## Download resources

A single target is about 3.3 GiB. Allow at least 8 GiB for the workspace. Public model downloads do not require authentication; repositories, target files, and paths are declared in the configuration.

```bash
.venv/bin/python -m pip install huggingface_hub
.venv/bin/hf download "$AGORA_MODEL_REPO" \
  --local-dir "$AGORA_MODELS_DIR" --include "${AGORA_MODEL_FILES[@]}"
```

AGORA_MODEL_FILES contains common resources and the selected SoC target. Downloads are anonymous and resolve one snapshot of main; no long revision string is required. Use HF --revision yourself when reproducibility requires an immutable commit.

## Resource targets

| SoC | Ubuntu selection | Model target | Qualification |
| --- | --- | --- | --- |
| QCS8550 | 22.04 | qcs8550_qnn248 | Validated on this board |
| QCS8625 | 22.04 | qcs8625_qnn248 | End-to-end validation pending |
| IQ8 / QCS8275 | 24.04 | qcs8275_qnn248 | End-to-end validation pending |
| IQ9 / QCS9075 | 24.04 | qcs9075_qnn248 | End-to-end validation pending |

The last three rows describe resource and OS selection, not a compatibility guarantee for the native SDK/BSP stack. Ubuntu 26.04 is unqualified. For 80ms, change the clock, model repository, and model directory together in agora.env.

## Package layout

```text
$AGORA_MODELS_DIR/
├── models.json                 # SDK package entry point
├── agora-model.json            # Resource metadata; not required by the SDK
├── SHA256SUMS
├── embedding.bin / *.npy / tokenizer.json / token_bytes.json
├── frontend/ prefix/ semantic_vad/
├── targets/<selected-soc>_qnn248/
└── LICENSES/ NOTICE README.md
```

A single-target download is about 3.3 GiB. No extraction or manual file moves are needed. --models takes the package root containing models.json. Model graphs, tensor bytes, models.json format, and SDK 0.9.0 ABI are unchanged by the Agora documentation work. The [package contract](../sdk/MODEL_PACKAGE.md), [Python API](../sdk/PYTHON_API.md), and [licensing scopes](../LICENSING.md) still apply.

## Integrity and repeated use

SHA256SUMS verifies downloaded file bytes. --ignore-missing permits intentionally absent other-SoC files; it does not prove required resources are complete. Web startup also checks required paths/resources and hashes. Cache reuse is supported. After changing workspace or model variant, source the edited configuration again and repeat the environment check. Never overlay two model variants in one package directory.

HF holds model data. GitHub holds application code, SDK, dependencies, and examples. Keep the deployment instructions in the GitHub guide rather than maintaining another installer in the model card. Original Pandora and upstream licensing remains applicable.
