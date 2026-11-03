# Agora 开发者部署指南

本指南以流式 ASR / 160ms / QCS8550 / Ubuntu 22.04 为例。网页按已选内容和硬件生成同样的配置与命令；没有 Agora CLI，也没有隐藏的一键安装。

## 参数只定义一次

`agora-run.json` 是可编辑的声明。第一步检查 JSON 的 workspace、仓库、SoC、系统、模型目标与端口，再检查实际设备。仅在配置有效且无 FAILED 设备项时生成 `agora-env.sh`，其中都是经过 shell 转义的普通环境变量。配置是数据，检查脚本不执行 JSON 中的代码。

推荐从 Agora 网页自定义 workspace 后点击“复制检查命令”：会一并保存配置和检查脚本。独立使用本 README 时，复制下面第一步也可以，不依赖 Agora 登录服务。示例里只有第一步定义路径和参数，后续从文件加载；打开新终端同样有效。

**配置不含凭据。** 正式 GitHub 与 HF 仓库均公开，使用 HTTPS clone 和匿名模型下载即可；不用拷贝私钥，不需要 token。将来改用私有资源时再单独使用服务原生认证。

修改 JSON 时需保持 SoC / 系统 / 模型目标匹配；80ms 应同时改 `audio_clock_ms`、HF 仓库和模型目录。完成修改后重新检查，不沿用旧的 agora-env.sh。

## 1. 环境检查

复制命令会保存配置声明和检查脚本。先校验参数与设备，再生成 agora-env.sh；后续步骤只加载这份参数文件。修改 JSON 后重新检查即可。

从网页复制时，workspace 与 JSON 会自动保持一致；独立使用时请把配置文件保存在你选择的 workspace，并保持声明路径一致。CHECKED 代表静态检查满足；FAILED 先修正；NEEDS_SETUP 在第三步处理；REVIEW 按板卡/BSP 文档确认。非零退出码不会自动安装任何东西。

```bash
export AGORA_WORKSPACE="$HOME/my-asr-demo"
mkdir -p "$AGORA_WORKSPACE"
cat > "$AGORA_WORKSPACE/agora-run.json" <<'AGORA_RUN_JSON'
{
  "schema_version": "1.0",
  "content": {
    "id": "live-transcribe",
    "title": "7×24 小时实时流式转录",
    "module": "solution"
  },
  "workspace": {
    "root": "~/my-asr-demo",
    "code": "audio8-asr-infinite-demo",
    "models": "models"
  },
  "target": {
    "soc": "QCS8550",
    "architecture": "aarch64",
    "os": {
      "name": "Ubuntu",
      "version": "22.04"
    },
    "board": {
      "id": "rhino-pi-x1"
    }
  },
  "source": {
    "repository": "https://github.com/APLUX-Agora/audio8-asr-infinite-demo.git",
    "revision": "main"
  },
  "model": {
    "repository": "APLUX-Agora/Audio8-ASR-Infinite-160ms",
    "revision": "main",
    "target": "qcs8550_qnn248",
    "directory": "$AGORA_WORKSPACE/models/audio8-160ms"
  },
  "runtime": {
    "sdk": "0.9.0",
    "qnn": "2.48",
    "python": [
      "3.10",
      "3.11",
      "3.12"
    ],
    "aidlite_qualified": "2.5.0.284"
  },
  "application": {
    "audio_clock_ms": 160,
    "port": 8765
  },
  "guide": {
    "repository_path": "docs/MODEL_SETUP.md",
    "qualification": "qualified"
  }
}
AGORA_RUN_JSON
cat > "$AGORA_WORKSPACE/check-environment.py" <<'AGORA_ENV_PY'
#!/usr/bin/env python3
"""Agora preflight: inspect the device; create only the requested workspace."""
import argparse
import importlib.util
import json
import shlex
import os
import platform
import re
import shutil
from pathlib import Path


def inspect_device(workspace, expected_soc, expected_ubuntu):
    results = []
    def add(status, name, expected, actual):
        results.append({'status': status, 'check': name, 'expected': expected, 'actual': actual})
    def read(path):
        try:
            return Path(path).read_text().replace('\x00', ' ').strip()
        except OSError:
            return ''
    arch = platform.machine()
    add('CHECKED' if arch == 'aarch64' else 'FAILED', '架构', 'aarch64', arch)
    release = dict(re.findall(r'^([A-Z_]+)=["\']?([^"\'\n]*)', read('/etc/os-release'), re.M))
    os_ok = release.get('ID') == 'ubuntu' and release.get('VERSION_ID') == expected_ubuntu
    add('CHECKED' if os_ok else 'FAILED', '系统', 'Ubuntu ' + expected_ubuntu, release.get('PRETTY_NAME', '未知'))
    machine = read('/sys/devices/soc0/machine')
    soc_id = read('/sys/devices/soc0/soc_id')
    fingerprint = (machine + ' ' + read('/proc/device-tree/compatible')).lower()
    # The supplied QCS8550 lab board reports QCS_KALAMAP / soc_id 603.
    detected = 'QCS8550' if 'kalamap' in fingerprint and soc_id == '603' else None
    aliases = {'QCS6490': ['qcs6490'], 'QCS8550': ['qcs8550'], 'QCS8625': ['qcs8625'], 'IQ8': ['qcs8275', 'iq8'], 'IQ9': ['qcs9075', 'iq9'], 'IQ10': ['iq10']}
    if detected is None:
        detected = next((name for name, values in aliases.items() if any(re.search(r'(?<![a-z0-9])' + re.escape(v) + r'(?![a-z0-9])', fingerprint) for v in values)), None)
    add('CHECKED' if detected == expected_soc else 'FAILED' if detected else 'REVIEW', 'SoC', expected_soc, detected or machine or '未识别，请按板卡文档确认')
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        with __import__('tempfile').TemporaryFile(dir=workspace) as f:
            f.write(b'agora-check')
        available = shutil.disk_usage(workspace).free / 1024**3
        add('CHECKED' if available >= 8 else 'NEEDS_SETUP', '可用空间', '建议至少 8 GiB（单目标模型约 3.3 GiB，另需代码与环境空间）', f'{available:.1f} GiB')
        add('CHECKED', '工作目录', '存在且可写', str(workspace) + f'（剩余 {available:.1f} GiB）')
    except OSError as exc:
        add('FAILED', '工作目录', '存在且可写', str(exc))
    py_ok = (3, 10) <= __import__('sys').version_info[:2] <= (3, 12)
    add('CHECKED' if py_ok else 'NEEDS_SETUP', 'Python', '3.10 / 3.11 / 3.12', platform.python_version())
    add('CHECKED' if shutil.which('git') else 'FAILED', 'Git', '已安装', shutil.which('git') or '缺失，先执行 sudo apt install git，再重新检查')
    add('CHECKED' if importlib.util.find_spec('venv') else 'NEEDS_SETUP', 'Python venv', '所选 Python 带有 venv 模块', '已找到' if importlib.util.find_spec('venv') else '缺失')
    add('CHECKED' if shutil.which('ffmpeg') else 'NEEDS_SETUP', 'FFmpeg', '已安装（用于音频转换和 Web Demo）', shutil.which('ffmpeg') or '未安装')
    libraries = [Path('/usr/local/lib') / f for f in ['libaidlite.so', 'libaidlite_qnn248.so']]
    add('CHECKED' if all(p.is_file() for p in libraries) else 'NEEDS_SETUP', 'AidLite / QNN', 'AidLite 与 QNN 2.48 库存在', '已找到库文件（仅静态检查）' if all(p.is_file() for p in libraries) else '默认路径缺少库文件，请在环境搭建中确认')
    rpc = list(Path('/dev').glob('*adsprpc*')) + list(Path('/dev').glob('*fastrpc*'))
    accessible = [p.name for p in rpc if os.access(p, os.R_OK | os.W_OK)]
    add('CHECKED' if accessible else 'REVIEW', 'NPU 设备接口', '当前账号可读写 RPC 节点', ', '.join(accessible) or '未找到可访问节点，请确认 BSP / 驱动和权限')
    return results


TARGETS = {'QCS8550': ('22.04', 'qcs8550_qnn248'), 'QCS8625': ('22.04', 'qcs8625_qnn248'), 'IQ8': ('24.04', 'qcs8275_qnn248'), 'IQ9': ('24.04', 'qcs9075_qnn248')}

def load_configuration(path):
    data = json.loads(Path(path).read_text())
    if data.get('schema_version') != '1.0':
        raise ValueError('schema_version 必须为 1.0')
    soc = data['target']['soc']
    ubuntu = data['target']['os']['version']
    target = data['model']['target']
    if soc not in TARGETS or (ubuntu, target) != TARGETS[soc]:
        raise ValueError('SoC、Ubuntu 与模型目标不匹配')
    if data['target']['architecture'] != 'aarch64' or data['target']['os']['name'] != 'Ubuntu':
        raise ValueError('此项目需要 Ubuntu / aarch64')
    clock = data['application']['audio_clock_ms']
    port = data['application']['port']
    if type(clock) is not int or clock not in (80, 160) or type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('audio_clock_ms 必须为 80/160，port 必须为 1024–65535')
    repo = data['source']['repository']
    if not re.fullmatch(r'(?:git@github\.com:|https://github\.com/)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git', repo):
        raise ValueError('代码仓库应为 GitHub HTTPS 或 SSH URL')
    model_repo = data['model']['repository']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', model_repo):
        raise ValueError('模型仓库应为 owner/repository')
    if data['source'].get('revision') != 'main' or data['model'].get('revision') != 'main':
        raise ValueError('当前指南使用 main；如需固定版本请自行使用 Git / HF 原生命令')
    raw = data['workspace']['root']
    if not isinstance(raw,str) or not (raw.startswith('~/') or raw.startswith('/')) or any(c in raw for c in '\r\n\0'):
        raise ValueError('workspace 应为 ~/ 开头或绝对路径')
    workspace = Path(raw).expanduser().resolve()
    code = data['workspace']['code']
    models = data['workspace']['models']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', code) or not re.fullmatch(r'[A-Za-z0-9_-]+', models):
        raise ValueError('代码与模型目录名应为单个目录名')
    model_dir = workspace / models / ('audio8-' + str(clock) + 'ms')
    expected_dir = '$AGORA_WORKSPACE/' + models + '/audio8-' + str(clock) + 'ms'
    if data['model']['directory'] != expected_dir:
        raise ValueError('模型目录声明与 workspace 不一致')
    values = {'AGORA_WORKSPACE': str(workspace), 'AGORA_CODE_REPO': repo,
              'AGORA_CODE_DIR': str(workspace / code), 'AGORA_MODEL_REPO': model_repo,
              'AGORA_MODEL_TARGET': target, 'AGORA_MODELS_DIR': str(model_dir),
              'AGORA_SOC': soc, 'AGORA_UBUNTU': ubuntu, 'AGORA_PYTHON': 'python3',
              'A8_CLOCK_MS': str(clock), 'A8_PORT': str(port)}
    return workspace, soc, ubuntu, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='Agora 运行声明 JSON；检查后生成 agora-env.sh')
    parser.add_argument('--workspace', default=str(Path.home() / 'agora-workspace'))
    parser.add_argument('--soc')
    parser.add_argument('--ubuntu')
    args = parser.parse_args()
    values = None
    if args.config:
        try:
            workspace, soc, ubuntu, values = load_configuration(args.config)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print('[FAILED] 配置声明 | ' + str(exc))
            return 1
        print('[CHECKED] 配置声明 | workspace、仓库、SoC、系统、模型目标及运行参数一致')
    else:
        if not args.soc or not args.ubuntu:
            parser.error('请提供 --config，或同时提供 --soc 和 --ubuntu')
        workspace, soc, ubuntu = Path(args.workspace).expanduser().absolute(), args.soc, args.ubuntu
    results = inspect_device(workspace, soc, ubuntu)
    for result in results:
        print(f"[{result['status']}] {result['check']} | 预期：{result['expected']} | 实际：{result['actual']}")
    failed = sum(r['status'] == 'FAILED' for r in results)
    pending = sum(r['status'] in ('NEEDS_SETUP', 'REVIEW') for r in results)
    if values and not failed:
        envfile = workspace / 'agora-env.sh'
        envfile.write_text('# Generated from agora-run.json; rerun the check after editing JSON.\n' + ''.join('export ' + name + '=' + shlex.quote(value) + '\n' for name, value in values.items()))
        envfile.chmod(0o600)
        print('参数文件已生成。后续终端加载：. ' + shlex.quote(str(envfile)))
    print(f'\n检查结束：失败 {failed} 项，待安装或确认 {pending} 项。静态检查不代表模型推理已通过。')
    return 1 if failed else 2 if pending else 0


if __name__ == '__main__':
    raise SystemExit(main())

AGORA_ENV_PY
python3 "$AGORA_WORKSPACE/check-environment.py" --config "$AGORA_WORKSPACE/agora-run.json"
```

## 2. 获取代码

从公共仓库获取代码，无需 GitHub 登录；仓库和目录均从配置读取。已有代码时跳过 clone，更新由开发者自行执行 git pull --ff-only。

```bash
. "$HOME/my-asr-demo/agora-env.sh" &&
(
  set -eu
  cd "$AGORA_WORKSPACE"
  if [ ! -e "$AGORA_CODE_DIR" ]; then
    git clone "$AGORA_CODE_REPO" "$AGORA_CODE_DIR"
  else
    echo "已有目录，跳过 clone；需要更新时自行执行 git pull --ff-only"
  fi
)
```

首次迁移建议选择一个新的 workspace，避免复用旧 Pandora checkout。再次执行会保留现有目录。需要更新时，在代码目录自行执行 `git pull --ff-only`，先处理自己的修改；不自动 reset 或覆盖代码。公共仓库无需 SSH 密钥；访问失败时先检查网络和 URL。

## 3. 环境搭建

各段独立执行；任意命令报错就停在当前段。云真机已有系统运行时，无需重复安装；系统工具缺什么补什么，venv 始终属于本项目。

### 系统运行时：已有 AidLite / QNN 时跳过

```bash
. "$HOME/my-asr-demo/agora-env.sh" &&
(
  set -eu
  cd "$AGORA_CODE_DIR"
  if [ ! -f /usr/local/lib/libaidlite.so ]; then
    sudo aid-pkg install aidlite-sdk
  fi
  if [ ! -f /usr/local/lib/libaidlite_qnn248.so ]; then
    sudo aid-pkg install aidlite-qnn248
  fi
  test -f /usr/local/lib/libaidlite.so
  test -f /usr/local/lib/libaidlite_qnn248.so
  echo "CHECKED: AidLite / QNN 2.48 libraries present"
)
```

### 系统工具：缺少依赖时安装

```bash
. "$HOME/my-asr-demo/agora-env.sh" &&
(
  set -eu
  cd "$AGORA_CODE_DIR"
  sudo apt-get update
  sudo apt-get install -y git ffmpeg libsndfile1 python3-venv
  echo "CHECKED: system dependencies installed"
)
```

### 项目环境：独立 venv

```bash
. "$HOME/my-asr-demo/agora-env.sh" &&
(
  set -eu
  cd "$AGORA_CODE_DIR"
  "$AGORA_PYTHON" -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/python -m pip check
  echo "CHECKED: project environment ready"
)
```

云真机公共 AidLite/QNN 已预置时跳过系统运行时安装。自有设备先按 BSP/厂商说明确认 aid-pkg；每次只安装一个包。出现锁占用不要删锁或强制继续，等待当前安装完成或联系管理员。系统安装需要当前设备用户的 sudo 权限，不是 Agora 网页密码。Python 默认取已检查的 python3，需要其他已支持版本时可改生成后的 AGORA_PYTHON 或按自己项目创建 venv。

每段使用子 shell 的 set -eu，失败立即结束该段但不会关闭交互终端。看到对应 CHECKED 才继续；不能因为最后 pip check 成功，就认定前面系统安装也成功。已有工具时无需重复 apt 安装。

## 4. 获取资源

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

公共资源直接匿名下载，无需 hf auth login。单次 hf download 解析 main 并下载选定文件，避免两次下载之间分支变化。缓存可复用；重新下载不会删除其它目录。`--ignore-missing` 允许未下载其它 SoC 的文件，只校验存在的文件；不能据此认定资源齐全，启动时还会按 models.json 检查必需资源。

模型根目录是 `$AGORA_MODELS_DIR`，不是 targets 子目录。每种时钟独立目录，不覆盖混用。模型大小约 3.3 GiB/目标（约 3.55 GB），workspace 建议至少 8 GiB 可用空间。

## 5. 运行测试

先选一个方式运行。文件示例显示加载、识别、完成三段提示；首跑用 20 秒音频，完成后输出文本与 finish_reason。Web 服务独立启动，Ctrl+C 停止。

### 先做 20 秒文件识别

```bash
. "$HOME/my-asr-demo/agora-env.sh" &&
(
  set -eu
  cd "$AGORA_CODE_DIR"
  .venv/bin/python examples/python/transcribe_file.py examples/audio/quickstart_en_20s.wav --models "$AGORA_MODELS_DIR" --clock-ms "$A8_CLOCK_MS" --lang en
)
```

### 或启动 Web Demo（前台运行）

```bash
. "$HOME/my-asr-demo/agora-env.sh" &&
(
  set -eu
  cd "$AGORA_CODE_DIR"
  demo/run.sh --models "$AGORA_MODELS_DIR" --port "$A8_PORT"
)
```

文件识别会依次显示 `[1/3] Loading model`、`[2/3] Transcribing`、`[3/3] Transcription complete`，随后输出文本和 finish_reason / audio / wall。20 秒样例避免首次等待十分钟音频；实际加载和识别耗时依设备而异，Ctrl+C 可停止。供应商加载日志可能穿插，看到日志不等于识别完成。

Web Demo 会先校验并加载模型，等服务显示监听地址后再打开浏览器。云真机：从远程桌面打开 `http://localhost:8765/`（配置改端口时相应修改地址），在 Agora 会话页开启声音。自己的设备：设备本机浏览器同样打开 localhost；同一网络的电脑使用 `http://<板卡IP>:8765/`。先选视频再 Start，Stop 停止识别，服务终端 Ctrl+C 结束服务。不要把文件测试和服务启动串在一起。

10 分钟音频保留在 examples/audio，首次通过后可任选长音频继续测试。20 秒样例的来源、许可和变更见 [媒体署名](MEDIA_ATTRIBUTION.md#agora-quickstart-audio)。

