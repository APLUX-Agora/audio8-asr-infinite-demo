# 模型资源与目录

参数来自第一步生成的 agora-env.sh，不在这里重复定义仓库、SoC 和路径。完整流程见 [Agora 部署指南](AGORA_DEPLOY.md)。

## 获取资源

单目标约 3.3 GiB，整个 workspace 建议预留至少 8 GiB。公共模型无需 HF 登录。仓库、硬件目标和下载目录从配置读取；如后续使用受控资源，token 也不写进配置。

```bash
. "$HOME/my-asr-demo/agora-env.sh" &&
(
  set -eu
  cd "$AGORA_CODE_DIR"
  .venv/bin/python -m pip install huggingface_hub
  .venv/bin/hf download "$AGORA_MODEL_REPO" --local-dir "$AGORA_MODELS_DIR" --include \
    README.md models.json agora-model.json SHA256SUMS NOTICE "LICENSES/*" \
    embedding.bin mel_filters.npy rotation.npy token_bytes.json tokenizer.json \
    "frontend/*" "prefix/*" "semantic_vad/*" "targets/$AGORA_MODEL_TARGET/*"
  (cd "$AGORA_MODELS_DIR" && sha256sum --ignore-missing -c SHA256SUMS)
  echo "CHECKED: downloaded files match checksums"
)
```

本仓库公开，直接下载即可；使用受控模型时另行执行 hf auth login，不要把 token 写入声明。单次下载按 main 解析同一版本，用户无需复制长 revision；要复现实验时可自行记录 hf 返回的快照或使用原生 --revision。Git 和 HF 独立版本，不假定其 commit 相同。

## SoC 资源目标

| SoC | 系统配置 | 模型目标 | 验收状态 |
| --- | --- | --- | --- |
| QCS8550 | Ubuntu 22.04 | qcs8550_qnn248 | 已在本板验证 |
| QCS8625 | Ubuntu 22.04 | qcs8625_qnn248 | 资源可获取，运行待验证 |
| IQ8 / QCS8275 | Ubuntu 24.04 | qcs8275_qnn248 | 资源可获取，运行待验证 |
| IQ9 / QCS9075 | Ubuntu 24.04 | qcs9075_qnn248 | 资源可获取，运行待验证 |

后面三项是资源/系统选择映射，不是 SDK 与整条 BSP 链路的兼容承诺。Ubuntu 26.04 未验收。80ms、160ms 各有独立 Agora HF 仓库，选择时同时更新 JSON 中的时钟、模型仓库及目录。

## 包结构

```text
$AGORA_MODELS_DIR/
├── models.json                # SDK 读取的模型包入口
├── agora-model.json           # Agora 资源声明，SDK 不依赖它
├── SHA256SUMS
├── embedding.bin / *.npy / tokenizer.json / token_bytes.json
├── frontend/ prefix/ semantic_vad/
├── targets/<所选SoC>_qnn248/
└── LICENSES/ NOTICE README.md
```

单目标约 3.3 GiB。无需解压或挪动文件；--models 传包含 models.json 的包根目录。公共资源和所选目标一次下载，不下载其它目标图。当前改造没有改变模型张量、图、models.json 格式或 SDK 0.9.0 ABI；原有 [模型包约定](../sdk/MODEL_PACKAGE.md)、[Python API](../sdk/PYTHON_API.md) 和 [许可范围](../LICENSING.md) 继续有效。

## 校验与重复执行

SHA256SUMS 检查下载文件完整性，--ignore-missing 允许其它未选 SoC 缺席，但不会证明包齐全。Web 启动还会验证必需路径、资源及哈希。HF 下载可复用缓存；修改 workspace 或时钟后重新运行环境检查，切勿将两个模型覆盖在一个目录。

模型资源是数据，GitHub 提供应用、SDK、依赖与示例。HF README 不维护另一套安装流程，统一链接回上述部署指南。资源和预编译 SDK 保留 Pandora 与上游许可，不因 Agora 命名变化而改变授权。
