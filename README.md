# Audio8-ASR-Infinite Demo · Agora

Streaming speech recognition on Qualcomm devices, powered by Edge0's [Audio8-ASR-Infinite](https://huggingface.co/Edge0/Audio8-ASR-Infinite). Includes a Web Demo, Python examples and C++ integration example.

[Pandora](https://pandora.aidlux.com/en/demos/live-transcribe-01/) · [ModelFarm](https://aiot.aidlux.com/en/models?name=Audio8)

[![Watch the demo video](docs/demo-poster.jpg)](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549)

[Watch video](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549) · [Download recording](docs/demo.mp4)

Source: Lorna Mitchell, FOSDEM 2025, **CC BY 2.0 BE**. Original credits are retained; the excerpt is trimmed and transcoded. [Source, license and changes](docs/MEDIA_ATTRIBUTION.md).

SDK version 0.9.0 supports the configurable models.json version 2 package.

## Agora 开发者部署

采用普通 Git、Python venv、Hugging Face CLI 和项目脚本，不封装 Agora CLI。

**参数在 `agora.env` 中定义一次，source 后生效，后面执行正常命令。** workspace 路径、仓库、SoC、系统、模型目标和端口都在同一份配置里；不生成第二份参数文件。GitHub 和 HF 均公开，无需 GitHub SSH 授权或 HF token。

从 [五步部署指南](docs/AGORA_DEPLOY.md) 开始：

1. 环境检查：创建并加载配置，逐项查看预期与实际环境。
2. 获取代码：正常 git clone 并进入代码目录。
3. 环境搭建：缺什么装什么，创建项目独立 venv。
4. 获取资源：HF 下载公共资源及所选 SoC。
5. 运行测试：20秒文件样例，或按需启动 Web Demo。

[配置文件示例](agora/agora.env.example) 可直接修改。网页按你的内容和硬件选择生成同样的配置与命令。命令不包裹条件判断或子 shell；已有目录、更新与排错由开发者决定。打开新终端后 source 一次配置即可继续。

```text
~/my-asr-demo/                         # 名字与路径自定义
├── agora.env
├── check-environment.py
├── audio8-asr-infinite-demo/          # 代码与 .venv
└── models/audio8-160ms/               # HF 模型根目录
```

## 支持范围

SDK 0.9.0；CPython 3.10 / 3.11 / 3.12。实际验收范围为 QCS8550 / Ubuntu 22.04 / AidLite 2.5.0.284 / QNN 2.48，含 80ms 和 160ms。HF 同时有 QCS8625、IQ8/QCS8275、IQ9/QCS9075 资源，但存在模型文件不等于完整运行链路已通过验收。其它 SoC、Ubuntu 24.04/26.04 必须另做真机验证，不在此承诺兼容。

模型仓库：

- [160ms Agora 资源](https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-160ms)
- [80ms Agora 资源](https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-80ms)

本仓库与两个 HF 模型仓库均公开，Git 使用 HTTPS、HF 匿名下载即可。若改用私有分支或受控模型，按服务原生方式单独认证，不在配置文件中保存凭据。模型下载和目录说明见 [MODEL_SETUP.md](docs/MODEL_SETUP.md)。

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
