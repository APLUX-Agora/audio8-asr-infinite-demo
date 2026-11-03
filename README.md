# Audio8-ASR-Infinite Demo · Agora

Streaming speech recognition on Qualcomm devices, powered by Edge0's [Audio8-ASR-Infinite](https://huggingface.co/Edge0/Audio8-ASR-Infinite). Includes a Web Demo, Python examples and C++ integration example.

[Pandora](https://pandora.aidlux.com/en/demos/live-transcribe-01/) · [ModelFarm](https://aiot.aidlux.com/en/models?name=Audio8)

[![Watch the demo video](docs/demo-poster.jpg)](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549)

[Watch video](https://pandora.aidlux.com/demos/live-transcribe-01/demo.mp4?v=14dc73371549) · [Download recording](docs/demo.mp4)

Source: Lorna Mitchell, FOSDEM 2025, **CC BY 2.0 BE**. Original credits are retained; the excerpt is trimmed and transcoded. [Source, license and changes](docs/MEDIA_ATTRIBUTION.md).

SDK version 0.9.0 supports the configurable models.json version 2 package.

## Agora 开发者部署

本仓库是面向 Agora 的独立副本。采用普通 Git、Python venv、Hugging Face CLI 和项目脚本，不封装 Agora CLI。参数集中放在 `agora-run.json`；环境检查通过后生成 `agora-env.sh`，后续命令加载它。配置中不保存 SSH 密钥、HF token 或 sudo 密码。

**从 [完整部署指南](docs/AGORA_DEPLOY.md) 开始。** 网页与该指南使用相同的五个环节：

1. 环境检查：自定义 workspace，校验 JSON 参数与真实设备，逐项显示预期、实际和结果。
2. 获取代码：通过 HTTPS clone 公共仓库；已有代码时保留，更新由开发者决定。
3. 环境搭建：分开确认系统运行时、系统工具和项目 venv；前置失败不继续当前段。
4. 获取资源：从对应 `-agora` HF 仓库下载公共文件及一个 SoC，校验已下载文件。
5. 运行测试：先用 20 秒文件样例，再按需启动 Web Demo；两种测试独立执行。

默认示例工作目录可任意修改，不固定在租约目录或仓库内：

```text
~/my-asr-demo/
├── agora-run.json                      # 可编辑的运行声明
├── check-environment.py                # 只检查，不自动安装
├── agora-env.sh                        # 由检查脚本生成，不手工维护
├── audio8-asr-infinite-demo/      # Git 代码与 .venv
└── models/audio8-160ms/                 # HF 模型根目录，含 models.json
```

修改 JSON 后重新运行检查。终端和远程桌面都使用同一用户主目录；切换终端不会自动继承 shell 变量，每段命令开头加载参数文件即可。`agora/demo.json` 描述项目资源与目标，不是安装执行器。

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
