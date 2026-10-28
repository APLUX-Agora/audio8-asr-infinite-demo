# Audio8-ASR-Infinite Python SDK

Install into your application's Python 3.10, 3.11 or 3.12 virtual environment:

```bash
python -m pip install /path/to/audio8-asr-infinite-demo/sdk
```

The package includes the matching precompiled native SDK 0.7.1 and its licenses. Python
package version `0.7.1` adds installation support without changing that native library.
The target is **Linux AArch64** with AidLite, its QNN 2.48 backend and the matching board BSP.
Installation does not install the vendor runtime or download models.

From your own application, with no repository import-path changes:

```python
from audio8_asr import ASRModel

with ASRModel.from_pretrained("/path/to/package-containing-manifest") as model:
    result = model.transcribe("speech.wav", language="en")
    print(result.text, result.finish_reason)
```

Pass the model package root explicitly, or set `A8_MODELS` to that root. The installed SDK
does not search for models beside its `site-packages` directory. Demo launchers and examples
separately discover their own checkout's `models/` when no explicit model path is selected.

See the [repository](https://github.com/APLUX-Pandora/audio8-asr-infinite-demo) for model downloads,
the full Python API, C ABI integration, examples and the Web Demo. Python bindings are Apache-2.0;
APLUX proprietary parts of the bundled native library use the Pandora Model and SDK License.
Applicable upstream and third-party terms remain in the included notices and licenses.
