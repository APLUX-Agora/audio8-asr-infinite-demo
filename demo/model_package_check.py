"""Delivery-file preflight for the web application, before changing a loaded engine.

This verifies package completeness and supplied SHA256SUMS; model execution remains in the SDK.
Checksums detect damaged downloads, not an attacker replacing both files and their checksum list.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import threading

REQUIRED = ('config', 'rows_const', 'mel_filters', 'token_bytes', 'encoder', 'adapter',
            'encoder_prefix_kv', 'decoder_1', 'decoder_2', 'decoder_prefix_kv_zh',
            'decoder_prefix_kv_en', 'embedding', 'rotation', 'vad_W', 'vad_b', 'vad_meta')


class PackageVerifier:
    def __init__(self, model_dir):
        self.root = Path(model_dir)
        self._lock = threading.Lock()

    @staticmethod
    def relative(name):
        if not isinstance(name, str) or not name or '\\' in name:
            raise ValueError('invalid model file path')
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or p.as_posix() != name or name == '.':
            raise ValueError('invalid model file path')
        return name

    def _document(self, name):
        try:
            return json.loads((self.root / name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise ValueError('missing or invalid ' + name) from None

    def _checksums(self):
        try:
            lines = (self.root / 'SHA256SUMS').read_text(encoding='utf-8').splitlines()
        except (OSError, ValueError):
            raise ValueError('missing or invalid SHA256SUMS') from None
        result = {}
        for line in lines:
            if not line.strip():
                continue
            fields = line.split(None, 1)
            if len(fields) != 2 or not re.fullmatch('[a-fA-F0-9]{64}', fields[0]):
                raise ValueError('invalid SHA256SUMS entry')
            name = self.relative(fields[1][1:] if fields[1].startswith('*') else fields[1])
            if name in result:
                raise ValueError('duplicate SHA256SUMS entry')
            result[name] = fields[0].lower()
        return result

    @staticmethod
    def _fingerprint(s):
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

    def _verify(self, name, expected):
        path = self.root / name
        try:
            before = path.stat()
            if not stat.S_ISREG(before.st_mode) or not before.st_size:
                raise ValueError('missing or empty model file: ' + name)
            fingerprint = self._fingerprint(before)
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                opened = self._fingerprint(os.fstat(stream.fileno()))
                if opened != fingerprint:
                    raise ValueError('model file changed during verification: ' + name)
                for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    digest.update(block)
                after_read = self._fingerprint(os.fstat(stream.fileno()))
            if opened != after_read or self._fingerprint(path.stat()) != fingerprint:
                raise ValueError('model file changed during verification: ' + name)
            if digest.hexdigest() != expected:
                raise ValueError('checksum mismatch: ' + name)
        except OSError:
            raise ValueError('missing or unreadable model file: ' + name) from None

    def error(self, clock):
        """None for a complete verified clock; otherwise a safe, package-relative reason."""
        with self._lock:
            try:
                manifest = self._document('manifest.json')
                if not isinstance(manifest, dict) or manifest.get('format') not in (1, 2):
                    raise ValueError('unsupported model manifest')
                clocks = manifest.get('clocks')
                if not isinstance(clocks, dict) or not isinstance(clocks.get(str(clock)), dict):
                    raise ValueError('audio clock is not installed')
                layout = clocks[str(clock)]
                missing = [key for key in REQUIRED if key not in layout]
                if missing:
                    raise ValueError('incomplete clock manifest: ' + ', '.join(missing))
                shared_embedding = manifest.get('format') == 2
                names = {self.relative(value) for key, value in layout.items()
                         if not (shared_embedding and key == 'embedding')}
                if shared_embedding:
                    spec = manifest.get('shared', {}).get('embedding', {})
                    if (layout['embedding'] != 'shared:embedding' or spec.get('file') != 'embedding.bin'
                            or spec.get('dtype') != 'float32-le' or spec.get('shape') != [151936, 2048]
                            or spec.get('bytes') != 151936 * 2048 * 4
                            or not re.fullmatch('[a-f0-9]{64}', spec.get('sha256', ''))):
                        raise ValueError('invalid shared embedding metadata')
                    container = self.root.resolve().parent
                    shared_path = container / 'shared' / 'embedding.bin'
                    if shared_path.resolve() != shared_path:
                        raise ValueError('shared embedding must stay inside the model container')
                    if not shared_path.is_file() or shared_path.stat().st_size != spec['bytes']:
                        raise ValueError('missing or incorrect-size shared embedding.bin')
                    shared_verifier = PackageVerifier(container / 'shared')
                    shared_sums = shared_verifier._checksums()
                    if shared_sums.get('embedding.bin') != spec['sha256']:
                        raise ValueError('shared embedding checksum does not match manifest')
                    shared_verifier._verify('embedding.bin', spec['sha256'])
                sums = self._checksums()
                for name in sorted(names):
                    if name not in sums:
                        raise ValueError('no checksum for model file: ' + name)
                    self._verify(name, sums[name])
                return None
            except (ValueError, TypeError) as exc:
                return str(exc)

    def available(self):
        errors = {clock: self.error(clock) for clock in ('160', '80')}
        return [clock for clock, error in errors.items() if error is None], {
            clock: error for clock, error in errors.items() if error is not None}
