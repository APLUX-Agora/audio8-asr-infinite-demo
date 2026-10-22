"""ctypes binding of libaudio8_asr.so (sdk/include/audio8_asr.h) for the Python business layer.

    from audio8_asr import Engine
    eng = Engine(lang="zh")             # clock_ms: 160 or 80, default = the installed one
    eng.reset()
    for chunk in audio_chunks:                     # float32 16 kHz mono, any chunk size
        for tok in eng.feed(chunk):                # Token(id, is_text, audio_t, eot)
            text_bytes += eng.token_bytes(tok.id)
    tail = eng.finish()

Library lookup: $AUDIO8_ASR_LIB, then sdk/lib/libaudio8_asr.so, then sdk/build/libaudio8_asr.so (next to this file's
parent), then the system loader path.
"""
import ctypes
import json
import os
import shlex
from collections import namedtuple
from pathlib import Path

import numpy as np

LANG_ZH, LANG_EN = 0, 1
EOT_HORIZONS, EOT_CLASSES = 4, 8
ERRORS = {-1: "A8_ERR_ARG", -2: "A8_ERR_MODEL", -3: "A8_ERR_NPU", -4: "A8_ERR_FULL", -5: "A8_ERR_STATE", -6: "A8_ERR_INTERNAL"}

Token = namedtuple("Token", "id is_text audio_t eot")


class _Options(ctypes.Structure):
    _fields_ = [("clock_ms", ctypes.c_int), ("lang", ctypes.c_int), ("roll_s", ctypes.c_double), ("stable_rows", ctypes.c_int),
                ("semantic_vad", ctypes.c_int), ("replay_max_s", ctypes.c_double)]


class _Token(ctypes.Structure):
    _fields_ = [("id", ctypes.c_int32), ("is_text", ctypes.c_int32), ("audio_t", ctypes.c_float),
                ("eot", ctypes.c_float * EOT_HORIZONS)]


class _Info(ctypes.Structure):
    _fields_ = [("sampling_rate", ctypes.c_int), ("samples_per_token", ctypes.c_int), ("clock_ms", ctypes.c_int),
                ("lang", ctypes.c_int), ("eot_horizons_s", ctypes.c_float * EOT_HORIZONS), ("num_delay_tokens", ctypes.c_int),
                ("streaming_pad_id", ctypes.c_int), ("default_tail_tokens", ctypes.c_int), ("roll_s", ctypes.c_double)]


class _Stats(ctypes.Structure):
    _fields_ = [("audio_fed_s", ctypes.c_double), ("n_tokens", ctypes.c_int64), ("lm_pos", ctypes.c_int64),
                ("lm_trims", ctypes.c_int32), ("soft_resets", ctypes.c_int32)] + \
               [(f"ms_{k}", ctypes.c_double) for k in ("mel", "tower_prep", "tower_npu", "tower_post", "projector_npu",
                                                       "lm_prep", "lm_npu", "lm_post")]


class A8Error(RuntimeError):
    """code: an A8_ERR_* value, or None when a8_create failed (the C API reports only a message for that)."""

    def __init__(self, code, msg):
        super().__init__(f"{'a8_create failed' if code is None else ERRORS.get(code, code)}: {msg}")
        self.code = code


def _load():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.environ.get("AUDIO8_ASR_LIB"), f"{here}/../lib/libaudio8_asr.so", f"{here}/../build/libaudio8_asr.so",
             "libaudio8_asr.so"]
    err = None
    for c in cands:
        if not c or (c != "libaudio8_asr.so" and not os.path.exists(c)):
            continue
        try:
            lib = ctypes.CDLL(c)
            break
        except OSError as e:
            err = e
    else:
        raise OSError(f"libaudio8_asr.so not found ({err})")
    P, I, D, F = ctypes.c_void_p, ctypes.c_int, ctypes.c_double, ctypes.POINTER(ctypes.c_float)
    sig = {"a8_version": (ctypes.c_char_p, []), "a8_default_options": (None, [ctypes.POINTER(_Options)]),
           "a8_create": (P, [ctypes.c_char_p, ctypes.POINTER(_Options)]), "a8_create_error": (ctypes.c_char_p, []),
           "a8_destroy": (None, [P]), "a8_get_info": (I, [P, ctypes.POINTER(_Info)]), "a8_last_error": (ctypes.c_char_p, [P]),
           "a8_reset": (I, [P]), "a8_feed": (I, [P, F, I]), "a8_finish": (I, [P, I]),
           "a8_read_tokens": (I, [P, ctypes.POINTER(_Token), I]), "a8_token_bytes": (I, [P, ctypes.c_int32, ctypes.c_char_p, I]),
           "a8_soft_reset": (I, [P, D]), "a8_eot_probs": (I, [P, F]), "a8_get_stats": (I, [P, ctypes.POINTER(_Stats)])}
    for name, (res, args) in sig.items():
        f = getattr(lib, name)
        f.restype, f.argtypes = res, args
    if hasattr(lib, "a8_set_hotwords"):
        lib.a8_set_hotwords.restype = I
        lib.a8_set_hotwords.argtypes = [P, ctypes.c_char_p, ctypes.c_char_p, I, ctypes.c_float, ctypes.c_float]
    return lib


_LIB = None


def lib():
    global _LIB
    if _LIB is None:
        _LIB = _load()
    return _LIB


def version():
    return lib().a8_version().decode()


def resolve_model_dir(model_dir=None, *, models_root=None):
    """Resolve a package root, never silently replacing an explicit path.

    Defaults are anchored to this checkout, independent of the caller's working directory.
    A flat package takes precedence; otherwise exactly one immediate child package is required.
    Discovery locates a manifest; package integrity and hardware compatibility are checked separately.
    """
    if model_dir is not None:
        raw = os.fspath(model_dir)
        if not raw:
            raise A8Error(-2, "empty model package path; pass the directory containing manifest.json")
        path = Path(raw).expanduser().absolute()
        if not (path / "manifest.json").is_file():
            raise A8Error(-2, f"missing manifest.json at {path}; pass the package root, not its parent directory")
        return str(path.resolve())
    root = Path(models_root) if models_root is not None else Path(__file__).resolve().parents[2] / "models"
    root = root.expanduser().absolute()
    if (root / "manifest.json").is_file():
        return str(root.resolve())
    try:
        candidates = sorted(p for p in root.iterdir() if p.is_dir() and (p / "manifest.json").is_file())
    except OSError:
        candidates = []
    if len(candidates) == 1:
        return str(candidates[0].resolve())
    if len(candidates) > 1:
        choices = "; ".join(str(p) for p in candidates)
        raise A8Error(-2, f"multiple model packages found: {choices}. Select one explicitly, e.g. --models {shlex.quote(str(candidates[0]))}")
    raise A8Error(-2, f"no model package found; checked {root}/manifest.json and {root}/*/manifest.json. "
                     "Download your chip folder into models/, or pass the package root explicitly with --models.")


def _manifest(model_dir):
    try:
        with open(os.path.join(model_dir, "manifest.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def extra_file(model_dir, name):
    """Path of a package file the SDK itself does not use (manifest.json "extras", e.g. "silero_vad"), or None."""
    model_dir = resolve_model_dir(model_dir)
    rel = _manifest(model_dir).get("extras", {}).get(name)
    return os.path.join(model_dir, rel) if rel else None


def installed_clocks(model_dir=None):
    """Audio clocks (ms) of the model package in model_dir (manifest.json) whose files are present, preferred first
    (160, then 80)."""
    model_dir = resolve_model_dir(model_dir)
    clocks = _manifest(model_dir).get("clocks", {})
    return [c for c in (160, 80) if str(c) in clocks and os.path.exists(os.path.join(model_dir, clocks[str(c)]["config"]))]


class Engine:
    """One engine = one audio clock + language (destroy and create to switch). Not thread-safe: use it from one thread."""

    def __init__(self, model_dir=None, clock_ms=None, lang="zh", roll_s=28.8, stable_rows=-1, semantic_vad=True, replay_max_s=10.0):
        """clock_ms None = the first installed audio clock (installed_clocks)."""
        self._h = None
        self.model_dir = model_dir = resolve_model_dir(model_dir)
        if clock_ms is None:
            clocks = installed_clocks(model_dir)
            if not clocks:
                raise A8Error(-2, f"no model package in {model_dir} (models/README.md)")
            clock_ms = clocks[0]
        L = lib()
        o = _Options()
        L.a8_default_options(ctypes.byref(o))
        o.clock_ms, o.lang, o.roll_s, o.stable_rows = int(clock_ms), LANG_EN if lang == "en" else LANG_ZH, float(roll_s), int(stable_rows)
        o.semantic_vad, o.replay_max_s = int(bool(semantic_vad)), float(replay_max_s)
        self._h = L.a8_create(os.fsencode(model_dir), ctypes.byref(o))
        if not self._h:
            raise A8Error(None, L.a8_create_error().decode())
        i = _Info()
        self._check(L.a8_get_info(self._h, ctypes.byref(i)))
        self.info = {"sampling_rate": i.sampling_rate, "samples_per_token": i.samples_per_token, "clock_ms": i.clock_ms,
                     "lang": "en" if i.lang == LANG_EN else "zh", "eot_horizons_s": list(i.eot_horizons_s),
                     "num_delay_tokens": i.num_delay_tokens, "streaming_pad_id": i.streaming_pad_id,
                     "default_tail_tokens": i.default_tail_tokens, "roll_s": i.roll_s}
        self.sampling_rate, self.samples_per_token = i.sampling_rate, i.samples_per_token
        self.clock_s = i.samples_per_token / i.sampling_rate
        self._buf = (_Token * 256)()
        self._bytes = {}

    # ------------------------------------------------------------------ helpers
    def _check(self, rc):
        if rc < 0:
            raise A8Error(rc, lib().a8_last_error(self._h).decode())
        return rc

    def _drain(self, n):
        out = []
        while n > 0:
            k = self._check(lib().a8_read_tokens(self._h, self._buf, len(self._buf)))
            if k == 0:
                break
            out += [Token(t.id, bool(t.is_text), float(t.audio_t), tuple(t.eot)) for t in self._buf[:k]]
            n -= k
        return out

    # ------------------------------------------------------------------ API
    def reset(self):
        self._check(lib().a8_reset(self._h))

    def set_hotwords(self, words=(), *, tokenizer_path=None, top_k=50, start_boost=6.0, continuation_boost=8.0):
        """Set optional token bias after reset, before audio. Empty list disables it.

        tokenizer_path is a matching tokenizer.json (or manifest extras.tokenizer).
        No encoding or model-specific inference is implemented in this binding.
        """
        if isinstance(words, (str, bytes)) or not isinstance(words, (list, tuple)):
            raise ValueError("words must be a list or tuple of strings")
        if not all(isinstance(w, str) and w.strip() for w in words):
            raise ValueError("hotwords must be nonempty strings")
        fn = getattr(lib(), "a8_set_hotwords", None)
        if fn is None:
            if not words:
                return  # legacy disabled behavior remains compatible
            raise A8Error(-5, "this SDK does not support hotwords; use SDK 0.6.0 or newer")
        path = (tokenizer_path or extra_file(self.model_dir, "tokenizer")) if words else None
        if words and not path:
            candidate = Path(self.model_dir) / "tokenizer.json"
            if candidate.is_file():
                path = candidate
            else:
                raise A8Error(-2, "hotwords require the matching tokenizer.json; pass tokenizer_path")
        self._check(fn(self._h, os.fsencode(path) if path else None,
                       json.dumps(list(words), ensure_ascii=False).encode("utf-8"), int(top_k),
                       float(start_boost), float(continuation_boost)))

    def feed(self, pcm):
        """float32 samples (16 kHz mono) -> new tokens."""
        x = np.ascontiguousarray(pcm, np.float32)
        n = self._check(lib().a8_feed(self._h, x.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), int(x.size)))
        return self._drain(n)

    def finish(self, tail_tokens=-1):
        return self._drain(self._check(lib().a8_finish(self._h, int(tail_tokens))))

    def soft_reset(self, replay_from_s):
        """LM back to the prefix + replay of the cached audio rows after replay_from_s -> the replayed tokens."""
        return self._drain(self._check(lib().a8_soft_reset(self._h, float(replay_from_s))))

    def token_bytes(self, tid):
        b = self._bytes.get(tid)
        if b is None:
            buf = ctypes.create_string_buffer(64)
            n = self._check(lib().a8_token_bytes(self._h, int(tid), buf, 64))
            if n > 64:
                buf = ctypes.create_string_buffer(n)
                lib().a8_token_bytes(self._h, int(tid), buf, n)
            b = self._bytes[tid] = buf.raw[:n]
        return b

    def text_of(self, ids):
        return b"".join(self.token_bytes(i) for i in ids)

    def eot_probs(self):
        p = np.zeros((EOT_HORIZONS, EOT_CLASSES), np.float32)
        self._check(lib().a8_eot_probs(self._h, p.ctypes.data_as(ctypes.POINTER(ctypes.c_float))))
        return p

    def stats(self):
        s = _Stats()
        self._check(lib().a8_get_stats(self._h, ctypes.byref(s)))
        return {k: getattr(s, k) for k, _ in s._fields_}

    def close(self):
        if self._h:
            lib().a8_destroy(self._h)
            self._h = None

    def __del__(self):
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass
