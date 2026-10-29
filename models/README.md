# Model resources

Download common resources and exactly the SoC target for your board into the same package root. Run from the Demo checkout using its installed .venv. SDK 0.7.2.dev2 supports models.json version 2, where all common-resource and graph paths are explicit configuration.

```bash
.venv/bin/python -m pip install huggingface_hub
REPO=APLUX-Pandora/Audio8-ASR-Infinite-160ms
REV=a3f645da5a4ab0583b4b1376ff76c6f56b91426f
DEST=models
TARGET=qcs8550_qnn248
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --exclude "targets/*"
.venv/bin/hf download "$REPO" --revision "$REV" --local-dir "$DEST" --include "targets/$TARGET/*"
```

For80ms use APLUX-Pandora/Audio8-ASR-Infinite-80ms. Targets are qcs8550_qnn248, qcs8625_qnn248, qcs8275_qnn248 (IQ8) and qcs9075_qnn248 (IQ9). Both commands must use the same revision; a fixed commit is preferable for reproducible applications. Repositories are maintained on main without extra branches or tags.

The SDK reads models/models.json. Ordinary resources map purpose names to package-root-relative paths. Raw token_vectors also declare dtype/shape/layout. Each target declares SoC, QNN version, directory and explicit encoder/adapter/decoder graph paths. No resource filename or target directory is inferred from a conventional spelling. Missing roles/paths, an unsupported schema or multiple complete targets cause explicit errors. Use A8_TARGET=qcs8550_qnn248 at application startup to select among multiple installed targets; this selects a declared installation and does not detect hardware compatibility.

Demo and examples use the installed SDK's root discovery. models.json takes precedence, otherwise legacy manifest.json remains supported. A unique immediate child package can be discovered; several model roots require an explicit --models or A8_MODELS selection. Keep80ms and160ms in separate roots; do not overlay them into the same destination. SDK installation outside a Demo requires an explicit model root and does not guess site-packages parents.

SHA256SUMS owns hashes. `sha256sum --ignore-missing -c SHA256SUMS` verifies present files only, not required-file completeness. Web preflight resolves required resources through the SDK and verifies their checksums before model replacement. Native loading validates configuration/path containment and raw embedding size before graph allocation. Silero VAD remains a Demo asset; semantic_vad/ belongs to the model.

The common download can replace this data directory's README with the HF model card. Installation instructions remain in the GitHub root README. See [models.json contract](../sdk/MODEL_PACKAGE.md) for fields and examples. Old SDK releases remain paired with their old resource revisions; the former prototype version1 models.json is superseded by version2. The candidate implementation changed resource loading only, not numerical model data or inference arithmetic.

Verified resource revisions for SDK0.7.2.dev2:160ms `a3f645da5a4ab0583b4b1376ff76c6f56b91426f`;80ms `a06231291d4264bee67cb7eabb0bdde663eb8032`. Both are commits on main; no tags are needed.
