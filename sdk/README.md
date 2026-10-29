# Audio8-ASR-Infinite SDK

The prebuilt `lib/libaudio8_asr.so` and [C ABI header](include/audio8_asr.h) are shared by Python and C/C++ callers.
Use the [Python API reference](PYTHON_API.md) for every method/result and the
[C ABI integration guide](NATIVE_INTEGRATION.md) for native calls, compilation, linking and ownership.
[Runnable examples](../examples/README.md) include Python file/stream programs and one C++ WAV program.
There is no second SDK or separate C++ inference implementation.

- SDK version: **0.7.2-dev2**.
- Library SHA256: `a5102a3a26f64b1295e806feeb1b152453d37ab5baa4bf163e4771a93163997c`.
- Platform: Linux AArch64, AidLite/QNN2.48 and matching board BSP/driver.
- Current Hugging Face model packages contain single-file prefix caches and the optional matching hotword tokenizer.
- ICU70.1 code and Unicode data are embedded; no system ICU installation is required.

## Install for Python integration

From the Demo repository root, in the interpreter/venv used by your application:

```bash
python -m pip install ./sdk
python -m pip check
```

You can then import `audio8_asr` from another directory without repository import-path changes.
The Python distribution is `audio8-asr-infinite-sdk==0.7.1`, carrying native SDK 0.7.1.
Its native library is installed inside the Python package; the original `sdk/lib/` library remains the
C/C++ integration artifact. Both have the same SHA256. Models are downloaded separately and selected
with an explicit package root or `A8_MODELS`. AidLite/QNN and the board BSP remain external prerequisites.
See [package details](PYTHON_PACKAGE.md) and [Python API](PYTHON_API.md).

## Compatibility

This SDK is tested on QCS8550 / Ubuntu22.04 with the160ms model.
Prior SDK0.6.1 userspace checks do not qualify the new0.7.0 binary on Ubuntu24.04/26.04.
Other clocks, chip targets and Ubuntu releases require their own qualification before broader claims.
CPython **3.10, 3.11 and 3.12** were verified for the Python SDK, examples and Web Demo with this same SDK and model package. Choose one interpreter with matching `venv` support and create this checkout's `.venv`; see [installation](../README.md#1-install). This does not extend the OS/BSP/NPU test scope. AidLite/QNN remain external prerequisites;
see the [native environment and loader requirements](NATIVE_INTEGRATION.md#target-and-linking).

## C API and Python integration

Use the same prebuilt SDK from Python or C/C++. See the complete
[Python API reference](PYTHON_API.md) and [C ABI integration guide](NATIVE_INTEGRATION.md).
The guides cover options, inputs, return values, errors, resource ownership, call order and cleanup.
Runnable [Python and C++ examples](../examples/README.md) use those public interfaces.

A session follows create -> reset -> optional hotwords -> feed/drain -> finish/drain -> close.
Do not call soft_reset or feed after finish without resetting. Signal handlers should request a stop;
wait for synchronous native work before destruction. The library does not perform file IO or own a worker.

## Environment variables

- `AUDIO8_ASR_LIB`: explicit qualified library path.
- `A8_KEEP_STDOUT=1`: retain vendor initialization/destruction notices on stdout instead of stderr.
- `A8_AIDLITE_LOG`: AidLite log level, default `warning`.


## Licensing / 许可

The APLUX proprietary portions of the prebuilt `.so` libraries are covered by the
Pandora Model and SDK License, not by the Apache-2.0 license of the business layer.
The C headers and Python bindings authored by APLUX remain Apache-2.0. Third-party
portions keep their own terms. See [licensing scope](../LICENSING.md),
[中文协议](../LICENSES/Pandora-Model-SDK.zh-CN.txt),
[English agreement](../LICENSES/Pandora-Model-SDK.en.txt) and the notices in `lib/`.

预编译 `.so` 中阿加犀专有部分采用 Pandora 自有许可，业务层 Apache-2.0 不覆盖这些专有部分；
阿加犀的 C 头文件、Python 绑定仍为 Apache-2.0，第三方部分保留各自许可。

## models.json integration candidate

Python package 0.7.2.dev2 contains native 0.7.2-dev2. This is an integration candidate, not a formal SDK release. Pass the package root containing models.json; legacy manifest formats remain supported. See [model setup](../../models/README.md) and [candidate contract](MODEL_PACKAGE.md).
