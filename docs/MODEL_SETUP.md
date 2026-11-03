# Model resource setup

The global agora.env declares only the HF repository/revision and target hardware. It does not declare model filenames, target-directory names, audio clocks, or web ports. The code checkout owns [agora/resources.env](../agora/resources.env), which maps the selected SoC to the correct Audio8 files.

## Download

After sourcing the global configuration and creating the project venv, run from workspace/code:

```bash
source agora/resources.env
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch "$AGORA_RESOURCE_REF" \
  "https://huggingface.co/$AGORA_RESOURCE_REPO" "$AGORA_WORKSPACE/resources"
git -C "$AGORA_WORKSPACE/resources" lfs install --local
GIT_LFS_SKIP_SMUDGE=1 git -C "$AGORA_WORKSPACE/resources" sparse-checkout set --no-cone \
  '/*' '!/targets/*' "/targets/$AUDIO8_MODEL_TARGET/"
GIT_LFS_SKIP_SMUDGE=1 git -C "$AGORA_WORKSPACE/resources" lfs pull --include="$AUDIO8_LFS_INCLUDE"
```

The file filters are project metadata, not editable global variables. They may change with model package versions. Git LFS is the standard downloader; no Agora CLI is involved. Resources are public and anonymous. Install git-lfs as a system prerequisite. Git LFS keeps both cached objects and working files (about 6.6 GiB total); sparse checkout omits unselected targets. An existing resource directory is not overwritten. The clone command accepts a branch or tag; exact commits use native Git checkout/fetch.

## Target mapping and qualification

| SoC | OS selection | Project target | Status |
| --- | --- | --- | --- |
| QCS8550 | Ubuntu22.04 | qcs8550_qnn248 | Qualified |
| QCS8625 | Ubuntu22.04 | qcs8625_qnn248 | End-to-end validation pending |
| IQ8 / QCS8275 | Ubuntu24.04 | qcs8275_qnn248 | End-to-end validation pending |
| IQ9 / QCS9075 | Ubuntu24.04 | qcs9075_qnn248 | End-to-end validation pending |

OS selections are not a promise of native SDK/BSP compatibility. Ubuntu26.04 is unqualified. The model repository selects 80ms versus 160ms; models.json declares the clock, and SDK/Web infer it from the selected package. A separate A8_CLOCK_MS export is not needed for this guide.

## Package root

```text
$AGORA_WORKSPACE/resources/
├── models.json                 # SDK entry point and audio-clock metadata
├── agora-model.json            # Resource metadata
├── SHA256SUMS
├── embedding.bin / *.npy / tokenizer.json / token_bytes.json
├── frontend/ prefix/ semantic_vad/
├── targets/<selected-soc>_qnn248/
└── LICENSES/ NOTICE README.md
```

No model bytes, SDK ABI, or models.json format are changed by this configuration work. A single target is about 3.3 GiB; allow at least 12 GiB for a workspace. Choose a separate workspace when switching content/hardware/model variants so old target files cannot be selected accidentally.

## Integrity

SHA256SUMS verifies present files. --ignore-missing allows unselected SoC files to be absent, but does not prove package completeness. Web startup also checks required resources and hashes. Native SDK and model licensing remain unchanged. See the [full deployment guide](AGORA_DEPLOY.md), [package contract](../sdk/MODEL_PACKAGE.md), and [Python API](../sdk/PYTHON_API.md).
