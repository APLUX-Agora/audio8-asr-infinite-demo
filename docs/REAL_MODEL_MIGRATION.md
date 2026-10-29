# Model and API migration

Audio8-ASR-Infinite-80ms and Audio8-ASR-Infinite-160ms have separate Hugging Face repositories
under APLUX-Pandora. QNN version and SoC are package-directory dimensions, such as
`targets/qcs8550_qnn248/`. Both models use the same [SDK and Demo repository](https://github.com/APLUX-Pandora/audio8-asr-infinite-demo).
The Pandora page slug remains `live-transcribe-01`; historical repositories and tags retain their original content.

## Current Python API: SDK 0.7.0

The old `Engine` interface and identity-renamed Python aliases are not provided by the current SDK.
Install the SDK into your application's venv, then use `ASRModel`:

```bash
python -m pip install /path/to/audio8-asr-infinite-demo/sdk
```

```python
from audio8_asr import ASRModel

with ASRModel.from_pretrained("models/qnn248_qcs8550") as model:
    result = model.transcribe("examples/audio/jobs_keynote_10min_16k.flac", language="en")
    print(result.text, result.finish_reason)
```

Use [Python API](../sdk/PYTHON_API.md) for inputs, streaming, results, errors and explicit resource ownership.
`from_pretrained` loads a local package; it does not download models. Use matching installed Python package,
header and native library from compatible deliveries. No old `Engine` alias is retained.

## Native interface naming

| Historical delivery | Current delivery |
| --- | --- |
| `liblive_transcribe_01.so` | `libaudio8_asr.so` |
| `live_transcribe_01.h` | `audio8_asr.h` |
| `lt01_*` C ABI | `a8_*` C ABI |
| `LT01_*` macros and Demo settings | `A8_*` |
| `LIVE_TRANSCRIBE_01_LIB` | `AUDIO8_ASR_LIB` |

SDK 0.7.0 preserves existing real-name C ABI signatures and adds per-request language, token-budget
and final-audio controls. See [native integration](../sdk/NATIVE_INTEGRATION.md).
The old identity-renamed ABI is historical; do not mix files across the naming or Python API boundary.

## Model resources

- [APLUX-Pandora/Audio8-ASR-Infinite-160ms](https://huggingface.co/APLUX-Pandora/Audio8-ASR-Infinite-160ms)
- [APLUX-Pandora/Audio8-ASR-Infinite-80ms](https://huggingface.co/APLUX-Pandora/Audio8-ASR-Infinite-80ms)

Follow [model setup](MODEL_SETUP.md) to download a complete SoC package at a fixed revision
and check its SHA256SUMS. Packages retain manifests, tokenizer, shared tensors, prefix caches,
applicable licenses and a brief README linking to GitHub. Full SDK/API/example/Web instructions
are maintained in the GitHub repository.

The resource migration preserves accepted model bytes. SDK 0.7.0 uses the existing single-file
prefix-cache layout; old 0.4.x per-layer packages are incompatible. The API and package must be
validated together for the target board/runtime; changing a repository name does not qualify a new platform.
