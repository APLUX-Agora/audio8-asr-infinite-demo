#!/usr/bin/env python3
"""Agora preflight: inspect the device; create only the requested workspace."""
import argparse
import importlib.util
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



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default=os.environ.get('AGORA_WORKSPACE', str(Path.home() / 'agora-workspace')))
    parser.add_argument('--soc', default=os.environ.get('AGORA_SOC'))
    parser.add_argument('--ubuntu', default=os.environ.get('AGORA_UBUNTU'))
    args = parser.parse_args()
    if not args.soc or not args.ubuntu:
        parser.error('请先 source agora.env，或提供 --soc 与 --ubuntu')
    results = inspect_device(Path(args.workspace).expanduser().absolute(), args.soc, args.ubuntu)
    for result in results:
        print(f"[{result['status']}] {result['check']} | 预期：{result['expected']} | 实际：{result['actual']}")
    failed = sum(r['status'] == 'FAILED' for r in results)
    pending = sum(r['status'] in ('NEEDS_SETUP', 'REVIEW') for r in results)
    print(f'\n检查结束：失败 {failed} 项，待安装或确认 {pending} 项。静态检查不代表模型推理已通过。')
    return 1 if failed else 2 if pending else 0


if __name__ == '__main__':
    raise SystemExit(main())
