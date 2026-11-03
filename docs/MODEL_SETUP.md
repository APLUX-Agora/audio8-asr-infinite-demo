# Model resources

All resources are maintained on main. Common files are shared once; targets/<SoC>/ contains hardware-specific graphs. The global agora.env contains only AGORA_WORKSPACE and AGORA_SOC. Repository URLs appear directly in the commands below.

## Download with the official HF CLI

During dependency setup, install huggingface_hub in the project virtual environment:

```bash
cd "$AGORA_WORKSPACE/code"
source .venv/bin/activate
pip install --upgrade huggingface_hub
```

Keep using this activated terminal. In a new terminal, source your saved agora.env, change to "$AGORA_WORKSPACE/code", and activate .venv again.

Then download common resources and the selected SoC directory:

### Download common resources

```bash
hf download APLUX-Agora/Audio8-ASR-Infinite-160ms \
  --exclude "targets/*" --local-dir "$AGORA_WORKSPACE/resources"
```

### Download the SoC model

```bash
hf download APLUX-Agora/Audio8-ASR-Infinite-160ms \
  --include "targets/$AGORA_SOC/*" --local-dir "$AGORA_WORKSPACE/resources"
```

For 80ms, replace both repository IDs with APLUX-Agora/Audio8-ASR-Infinite-80ms. Supported AGORA_SOC values: QCS8550, QCS8625, IQ8, IQ9. The first command gets common files; the second gets only the selected hardware directory. No Git LFS installation, branch selection, custom CLI, or authentication is required. The default revision is main. See the [official HF CLI guide](https://huggingface.co/docs/huggingface_hub/en/guides/cli).

Re-run these commands to reuse current files and download missing or changed resources. Existing unrelated files are not deleted. Use a separate workspace per task or model/hardware combination. Selected model files occupy about 3.3 GiB; allow at least 8 GiB for the workspace, dependencies, and download overhead.

## Layout

```text
resources/
├── models.json / agora-model.json / SHA256SUMS
├── embedding.bin / *.npy / tokenizer.json / token_bytes.json
├── frontend/ prefix/ semantic_vad/ LICENSES/ NOTICE
└── targets/
    └── QCS8550/  # only the selected hardware is downloaded
```

The repository also contains targets/QCS8625, targets/IQ8, and targets/IQ9. models.json maps runtime platform identifiers to these directories. Version tags can identify releases independently of hardware selection.

## Verify

```bash
cd "$AGORA_WORKSPACE/resources"
sha256sum -c SHA256SUMS --ignore-missing
cd "$AGORA_WORKSPACE/code"
```

Unselected hardware directories are intentionally absent. This verifies present files; missing-file tolerance alone does not prove completeness. The application's preflight checks required files and hashes before startup. Only QCS8550 / Ubuntu 22.04 has been validated in the Agora lab. Other targets require device qualification. Original model and SDK license terms are unchanged. See the [deployment guide](AGORA_DEPLOY.md), [package contract](../sdk/MODEL_PACKAGE.md), and [Python API](../sdk/PYTHON_API.md).
