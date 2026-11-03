# Model resources

The global agora.env contains only AGORA_WORKSPACE and AGORA_SOC. Repository URLs are explicit in commands. Model filenames, clocks, and target-directory mappings belong to the package.

## Download

Install Git LFS, source your agora.env, then run:

```bash
git clone --depth 1 --branch "$AGORA_SOC" https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-160ms "$AGORA_WORKSPACE/resources"
```

For 80ms, use https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-80ms instead. Supported hardware branches: QCS8550, QCS8625, IQ8, IQ9. Each branch has common assets and only its selected target, so sparse checkout and file-include patterns are unnecessary. The main branch keeps all targets for maintainers. Resources are public and need no token.

A hardware branch contains about 3.3 GiB of models. Git LFS keeps cached and working copies (about 6.6 GiB); allow at least 12 GiB for your workspace. Use a new workspace when switching model or hardware. Existing directories are not overwritten.

## Verify

```bash
cd "$AGORA_WORKSPACE/resources"
sha256sum -c SHA256SUMS
cd "$AGORA_WORKSPACE/code"
```

Only QCS8550 / Ubuntu 22.04 has been validated in the Agora lab. Other targets require device qualification. The SDK reads application defaults from models.json. Original model and SDK license terms are unchanged. See the [deployment guide](AGORA_DEPLOY.md), [package contract](../sdk/MODEL_PACKAGE.md), and [Python API](../sdk/PYTHON_API.md).
