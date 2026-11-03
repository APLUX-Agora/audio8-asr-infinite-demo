#!/usr/bin/env python3
"""Agora preflight: inspect the device; create only the requested workspace."""
import argparse
import importlib.util
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path


def inspect_device(workspace, expected_soc, expected_ubuntu, expected_os="ubuntu"):
    results = []
    def add(status, name, expected, actual):
        results.append({'status': status, 'check': name, 'expected': expected, 'actual': actual})
    def read(path):
        try:
            return Path(path).read_text().replace('\x00', ' ').strip()
        except OSError:
            return ''
    arch = platform.machine()
    add('CHECKED' if arch == 'aarch64' else 'FAILED', 'Architecture', 'aarch64', arch)
    release = dict(re.findall(r'^([A-Z_]+)=["\']?([^"\'\n]*)', read('/etc/os-release'), re.M))
    os_ok = release.get('ID') == expected_os and release.get('VERSION_ID') == expected_ubuntu
    add('CHECKED' if os_ok else 'FAILED', 'Operating system', expected_os + ' ' + expected_ubuntu, release.get('PRETTY_NAME', 'Unknown'))
    machine = read('/sys/devices/soc0/machine')
    soc_id = read('/sys/devices/soc0/soc_id')
    fingerprint = (machine + ' ' + read('/proc/device-tree/compatible')).lower()
    # The supplied QCS8550 lab board reports QCS_KALAMAP / soc_id 603.
    detected = 'QCS8550' if 'kalamap' in fingerprint and soc_id == '603' else None
    aliases = {'QCS6490': ['qcs6490'], 'QCS8550': ['qcs8550'], 'QCS8625': ['qcs8625'], 'IQ8': ['qcs8275', 'iq8'], 'IQ9': ['qcs9075', 'iq9'], 'IQ10': ['iq10']}
    if detected is None:
        detected = next((name for name, values in aliases.items() if any(re.search(r'(?<![a-z0-9])' + re.escape(v) + r'(?![a-z0-9])', fingerprint) for v in values)), None)
    add('CHECKED' if detected == expected_soc else 'FAILED' if detected else 'REVIEW', 'SoC', expected_soc, detected or machine or 'Unknown; confirm against board documentation')
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        with __import__('tempfile').TemporaryFile(dir=workspace) as f:
            f.write(b'agora-check')
        available = shutil.disk_usage(workspace).free / 1024**3
        add('CHECKED' if available >= 12 else 'NEEDS_SETUP', 'Free space', 'At least 12 GiB recommended (about 6.6 GiB including LFS cache, plus code and environment)', f'{available:.1f} GiB')
        add('CHECKED', 'Workspace', 'Exists and writable', str(workspace) + f' (free: {available:.1f} GiB)')
    except OSError as exc:
        add('FAILED', 'Workspace', 'Exists and writable', str(exc))
    py_ok = (3, 10) <= __import__('sys').version_info[:2] <= (3, 12)
    add('CHECKED' if py_ok else 'NEEDS_SETUP', 'Python', '3.10 / 3.11 / 3.12', platform.python_version())
    add('CHECKED' if shutil.which('git') else 'FAILED', 'Git', 'Installed', shutil.which('git') or 'Missing; install Git and rerun the check')
    lfs = subprocess.run(['git', 'lfs', 'version'], capture_output=True, text=True) if shutil.which('git') else None
    add('CHECKED' if lfs and lfs.returncode == 0 else 'NEEDS_SETUP', 'Git LFS', 'Installed for model downloads', lfs.stdout.strip() if lfs and lfs.returncode == 0 else 'Missing; install git-lfs in step 3')
    add('CHECKED' if importlib.util.find_spec('venv') else 'NEEDS_SETUP', 'Python venv', 'venv module available in the selected Python', 'Found' if importlib.util.find_spec('venv') else 'Missing')
    add('CHECKED' if shutil.which('ffmpeg') else 'NEEDS_SETUP', 'FFmpeg', 'Installed (audio conversion and Web Demo)', shutil.which('ffmpeg') or 'Not installed')
    libraries = [Path('/usr/local/lib') / f for f in ['libaidlite.so', 'libaidlite_qnn248.so']]
    add('CHECKED' if all(p.is_file() for p in libraries) else 'NEEDS_SETUP', 'AidLite / QNN', 'AidLite and QNN 2.48 libraries present', 'Libraries found (static check only)' if all(p.is_file() for p in libraries) else 'Libraries missing from default paths; review runtime setup')
    rpc = list(Path('/dev').glob('*adsprpc*')) + list(Path('/dev').glob('*fastrpc*'))
    accessible = [p.name for p in rpc if os.access(p, os.R_OK | os.W_OK)]
    add('CHECKED' if accessible else 'REVIEW', 'NPU interface', 'RPC nodes readable and writable by the current user', ', '.join(accessible) or 'No accessible RPC node; review BSP, drivers and permissions')
    return results



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default=os.environ.get('AGORA_WORKSPACE', str(Path.home() / 'agora-workspace')))
    parser.add_argument('--soc', default=os.environ.get('AGORA_SOC'))
    parser.add_argument('--ubuntu', default=os.environ.get('AGORA_OS_VERSION'))
    parser.add_argument('--os', default=os.environ.get('AGORA_OS', 'ubuntu'))
    args = parser.parse_args()
    if not args.soc or not args.ubuntu:
        parser.error('Source agora.env first, or supply --soc and --ubuntu')
    results = inspect_device(Path(args.workspace).expanduser().absolute(), args.soc, args.ubuntu, args.os)
    for result in results:
        print(f"[{result['status']}] {result['check']} | Expected: {result['expected']} | Actual: {result['actual']}")
    failed = sum(r['status'] == 'FAILED' for r in results)
    pending = sum(r['status'] in ('NEEDS_SETUP', 'REVIEW') for r in results)
    print(f'\nChecks complete: {failed} failed, {pending} need setup or review. Static checks do not qualify model inference.')
    return 1 if failed else 2 if pending else 0


if __name__ == '__main__':
    raise SystemExit(main())
