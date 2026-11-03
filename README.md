# Audio8-ASR-Infinite Demo · Agora

Streaming speech recognition on Qualcomm devices, powered by Edge0's [Audio8-ASR-Infinite](https://huggingface.co/Edge0/Audio8-ASR-Infinite). Includes a Web Demo, Python examples and C++ integration example.

[Pandora](https://pandora.aidlux.com/en/demos/live-transcribe-01/) · [ModelFarm](https://aiot.aidlux.com/en/models?name=Audio8)

[![Watch the demo video](docs/demo-poster.jpg)](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549)

[Watch video](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549) · [Download recording](docs/demo.mp4)

Source: Lorna Mitchell, FOSDEM 2025, **CC BY 2.0 BE**. Original credits are retained; the excerpt is trimmed and transcoded. [Source, license and changes](docs/MEDIA_ATTRIBUTION.md).

SDK version 0.9.0 supports the configurable models.json version 2 package.

## Agora deployment

Use standard Git, Python venv, the Hugging Face CLI, and the project's examples. No Agora CLI is required.

**Declare parameters once in `agora.env`, source the file, then run normal commands.** The configuration contains your workspace, repositories, SoC, operating system, model target, paths, and application port. It does not contain credentials or generate another parameter file. The GitHub and HF repositories are public: HTTPS cloning and anonymous model downloads work without SSH keys or HF tokens.

Follow the [five-step deployment guide](docs/AGORA_DEPLOY.md):

1. Check the environment: create and load the configuration, then compare expected and detected conditions.
2. Get the code: clone the repository and enter its directory.
3. Set up dependencies: install missing system prerequisites and create a project venv.
4. Get model resources: download common files and the selected SoC target.
5. Run a test: use the 20-second audio sample, or start the Web Demo separately.

The [configuration template](agora/agora.env.example) is editable. Agora fills the same parameters from your selected content and hardware; developers using GitHub can edit the template themselves. After opening a new terminal, source your configuration again. Existing checkouts, updates, and troubleshooting remain under your control.

```text
~/my-asr-demo/                         # Choose your own name and location
├── agora.env
├── check-environment.py
├── audio8-asr-infinite-demo/          # Code and project .venv
└── models/audio8-160ms/               # HF model package root
```

## Supported platforms

SDK 0.9.0 supports CPython 3.10 / 3.11 / 3.12. The qualified combination is QCS8550 / Ubuntu 22.04 / AidLite 2.5.0.284 / QNN 2.48, with both 80ms and 160ms packages. QCS8625, IQ8/QCS8275, and IQ9/QCS9075 resource files are available, but their presence does not qualify the entire SDK/BSP/runtime stack. Other SoCs and Ubuntu 24.04/26.04 require separate on-device validation.

Model repositories:

- [160ms resources](https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-160ms)
- [80ms resources](https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-80ms)

These repositories are public. If you use a private fork or restricted model later, authenticate through the service's standard tools and keep credentials out of configuration files. See [model resource setup](docs/MODEL_SETUP.md).

## API reference

- [Python SDK API](sdk/PYTHON_API.md)
- [C ABI integration and C++ build instructions](sdk/NATIVE_INTEGRATION.md)
- [SDK requirements and compatibility](sdk/README.md)

## License

See [LICENSING.md](LICENSING.md) for component scopes, [LICENSE](LICENSE) for the license index,
and [NOTICE](NOTICE) for attribution. Demo/example code and public interfaces use Apache-2.0;
the precompiled SDK and model adaptations are subject to the
[Pandora Model and SDK License](LICENSES/Pandora-Model-SDK.en.txt) and applicable upstream terms.

## Hardware runtime configuration

Python and C callers configure hardware through Pandora Runtime/CpuOptions/QnnOptions,
separately from model generation settings. AidLite remains the inference backend.
See [Runtime options, support status and ownership](sdk/RUNTIME.md): supported
profiles/control latency are forwarded; priority/polling and system_settings are
reserved and explicitly reported as inactive in this provider.

CPU placement: SDK default `inherit`; official Web/file launchers explicitly
choose `default`. Both audio clocks accept `--cpu-affinity inherit`, `default`,
or comma-separated CPU IDs. See the [Python/C CPU reference](sdk/CPU_AFFINITY.md)
for platform profiles, native worker coverage and observed-thread status.
