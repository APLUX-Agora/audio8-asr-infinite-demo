# Agora 开发者部署指南

以流式 ASR / 160ms / QCS8550 / Ubuntu22.04 为例。使用普通 Git、Python venv、HF CLI 和项目脚本，没有 Agora CLI。

**一份配置，加载一次，后面正常执行命令。** 第一步创建 `agora.env`，把 workspace、代码仓库、模型仓库、SoC、系统、目录和运行参数定义好；执行 `source` 后在当前 Bash 终端生效。配置可编辑，路径和名字可自行选择。打开新终端时重新 source 一次即可，不必每一步加载。

`agora.env` 是可读的 Bash 参数文件，其中的数组只声明本次要下载的模型文件。里面没有安装动作、凭据或条件判断。JSON 不是这套部署流程的输入，也不再生成第二份环境变量文件。

GitHub 与两个 HF 仓库均公开，可以直接 HTTPS clone、匿名下载，不需要 SSH 密钥或 token。按顺序逐条执行命令；一条失败就先解决，不继续后面的命令。指南不替你覆盖已有目录或决定如何更新代码。

首次建议使用新 workspace，避免复用旧 Pandora checkout。后续目录如下：

```text
~/my-asr-demo/                         # 名字与路径自定义
├── agora.env                         # 唯一的部署参数文件
├── check-environment.py              # 只检查，不安装
├── audio8-asr-infinite-demo/          # 代码与项目 .venv
└── models/audio8-160ms/               # 独立模型根目录
```

## 1. 环境检查

参数在 agora.env 中定义一次。source 后在当前终端生效，再检查设备环境；后续命令直接使用这些变量。

### 1. 创建配置文件 · agora.env

```bash
mkdir -p "$HOME/my-asr-demo"
cat > "$HOME/my-asr-demo/agora.env" <<'AGORA_CONFIG'
export AGORA_WORKSPACE="$HOME/my-asr-demo"
export AGORA_CODE_REPO='https://github.com/APLUX-Agora/audio8-asr-infinite-demo.git'
export AGORA_CODE_DIR="$AGORA_WORKSPACE/audio8-asr-infinite-demo"
export AGORA_SOC='QCS8550'
export AGORA_UBUNTU='22.04'
export AGORA_PYTHON=python3
export AGORA_MODEL_REPO='APLUX-Agora/Audio8-ASR-Infinite-160ms'
export AGORA_MODEL_TARGET='qcs8550_qnn248'
export AGORA_MODELS_DIR="$AGORA_WORKSPACE/models/audio8-160ms"
export A8_CLOCK_MS=160
export A8_PORT=8765

AGORA_MODEL_FILES=(
  README.md models.json agora-model.json SHA256SUMS NOTICE "LICENSES/*"
  embedding.bin mel_filters.npy rotation.npy token_bytes.json tokenizer.json
  "frontend/*" "prefix/*" "semantic_vad/*" "targets/$AGORA_MODEL_TARGET/*"
)
AGORA_CONFIG
```

### 2. 加载配置并检查环境

```bash
source "$HOME/my-asr-demo/agora.env"
mkdir -p "$AGORA_WORKSPACE"
curl -fL https://raw.githubusercontent.com/APLUX-Agora/audio8-asr-infinite-demo/main/tools/check-environment.py \
  -o "$AGORA_WORKSPACE/check-environment.py"
"$AGORA_PYTHON" "$AGORA_WORKSPACE/check-environment.py"
```

配置中的路径、SoC、系统、模型目标由网页按选型填好。独立使用时可自行修改；修改后重新 source 再检查。使用 Bash 执行，因为模型文件列表采用 Bash 数组。检查脚本只读取环境并确保 workspace 可写，不安装软件。CHECKED 是静态条件满足；FAILED 先修正；NEEDS_SETUP 在环境搭建中补齐；REVIEW 按板卡文档确认。

## 2. 获取代码

第一次直接 clone。已有代码时跳过这步；需要更新时在代码目录执行 git pull --ff-only。

```bash
git clone "$AGORA_CODE_REPO" "$AGORA_CODE_DIR"
cd "$AGORA_CODE_DIR"
```

已有代码时跳过 clone，不会自动更新或覆盖。要更新时先在代码目录处理自己的修改，再执行 `git pull --ff-only`。clone 提示目录已存在时，不要删除用户文件，换一个 workspace 或使用已有 checkout。

## 3. 环境搭建

按顺序逐条执行，报错先处理，不继续后面的安装。已有系统依赖时跳过相应安装，项目使用独立 venv。

### 系统运行时（云真机已预置，可跳过）

```bash
sudo aid-pkg install aidlite-sdk
sudo aid-pkg install aidlite-qnn248
```

### 系统工具（缺少时安装）

```bash
sudo apt-get update
sudo apt-get install -y git ffmpeg libsndfile1 python3-venv
```

### 项目虚拟环境

```bash
cd "$AGORA_CODE_DIR"
"$AGORA_PYTHON" -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

云真机已预置 AidLite/QNN，直接跳过第一段。自有设备安装前先看 BSP/厂商运行时说明，aid-pkg 每次安装一个包；锁占用时等待当前安装完成或联系管理员，不删锁。系统安装需要设备账号的 sudo 权限。已有系统工具时无需重复 apt 安装。venv 所用 Python 要带 venv 模块，支持的版本是 3.10/3.11/3.12；安装中报错先处理，不凭最后 pip check 成功推断前面也成功。

## 4. 获取资源

模型约 3.3 GiB，workspace 建议预留 8 GiB。公共仓库无需登录；仓库、下载目录和所选 SoC 文件均已在配置中声明。

```bash
.venv/bin/python -m pip install huggingface_hub
.venv/bin/hf download "$AGORA_MODEL_REPO" \
  --local-dir "$AGORA_MODELS_DIR" --include "${AGORA_MODEL_FILES[@]}"
```

单次 HF 下载取得公共资源和所选 SoC，不下载其它 SoC 图。资源缓存可复用，--models 应指向包含 models.json 的根目录，不是 targets 子目录。80ms、160ms 用各自独立目录。要自行检查哈希，可以执行：

```bash
cd "$AGORA_MODELS_DIR"
sha256sum --ignore-missing -c SHA256SUMS
cd "$AGORA_CODE_DIR"
```

--ignore-missing 只检查存在的文件，允许其它未选 SoC 缺席，不代表必需资源齐全；Web 启动会继续校验必需资源与哈希。需要固定历史版本时自行使用 Git/HF 原生 revision 选项，默认指南使用 main。

## 5. 运行测试

文件识别与 Web Demo 按需选择一个运行。20 秒样例会显示加载、识别和完成；Web 服务在当前终端运行，Ctrl+C 停止。

### 20 秒文件识别

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/quickstart_en_20s.wav \
  --models "$AGORA_MODELS_DIR" --clock-ms "$A8_CLOCK_MS" --lang en
```

### Web Demo（按需启动）

```bash
demo/run.sh --models "$AGORA_MODELS_DIR" --port "$A8_PORT"
```

文件示例依次输出 `[1/3] Loading model`、`[2/3] Transcribing`、`[3/3] Transcription complete`，然后输出文本与 finish_reason、audio、wall。文本在文件识别完成后返回，供应商加载日志可能穿插；首次用20秒样例即可，10分钟音频留作后续可选测试。

Web 服务会先检查并加载模型，等待终端显示监听地址。云真机：在完整远程桌面的浏览器打开 `http://localhost:8765/`，Agora 会话页点“开启声音”。自己的设备：设备本机打开 localhost，同一网络电脑使用 `http://<板卡IP>:8765/`；若配置改端口则使用对应端口。Start 开始，Stop 停止识别，服务终端 Ctrl+C 结束服务。文件测试和 Web 启动分别选择，不自动串起来执行。

20秒音频来源与许可见 [媒体署名](MEDIA_ATTRIBUTION.md#agora-quickstart-audio)。

