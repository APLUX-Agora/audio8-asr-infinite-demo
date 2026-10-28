"""Package the unchanged released native library; do not compile the engine during installation."""
import hashlib
import json
from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.errors import SetupError
from wheel.bdist_wheel import bdist_wheel

ROOT = Path(__file__).resolve().parent


class BuildSDK(build_py):
    def run(self):
        pairing = json.loads((ROOT / "native-library.json").read_text())
        library = ROOT / "lib" / pairing["filename"]
        if not library.is_file():
            raise SetupError("Missing lib/libaudio8_asr.so: obtain the matching prebuilt SDK Release before installing")
        payload = library.read_bytes()
        if payload[:4] != b"\x7fELF" or int.from_bytes(payload[18:20], "little") != 183:
            raise SetupError("The packaged native library must be an AArch64 ELF")
        if hashlib.sha256(payload).hexdigest() != pairing["sha256"]:
            raise SetupError("Native library SHA256 does not match native-library.json; use the matched release")
        for name in ("LICENSE", "LICENSE.zh-CN.txt", "THIRD_PARTY_NOTICES.txt", "LICENSES"):
            if not (ROOT / "lib" / name).exists():
                raise SetupError("Missing required native SDK license: " + name)
        super().run()
        target = Path(self.build_lib) / "audio8_asr" / "lib"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(library, target / library.name)
        for name in ("LICENSE", "LICENSE.zh-CN.txt", "THIRD_PARTY_NOTICES.txt", "LICENSES"):
            source = ROOT / "lib" / name
            if source.is_dir():
                shutil.copytree(source, target / name, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target / name)
        shutil.copy2(ROOT / "native-library.json", Path(self.build_lib) / "audio8_asr" / "native-library.json")


class LinuxAArch64Wheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False
        self.plat_name = "linux_aarch64"

    def get_tag(self):
        # ctypes uses a C ABI, not a CPython extension ABI. The payload is still platform-specific.
        return "py3", "none", "linux_aarch64"


setup(cmdclass={"build_py": BuildSDK, "bdist_wheel": LinuxAArch64Wheel})
