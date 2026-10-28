"""Editable file/PCM preparation; no model inference or automatic segmentation."""
from __future__ import annotations

import math
import os

import numpy as np
from scipy.signal import firwin, upfirdn

TARGET_RATE = 16000


def rate(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("sample_rate must be a positive integer in Hz")
    if value <= 0:
        raise ValueError("sample_rate must be positive")
    return value


def mono(pcm, channel=None, *, channels=None):
    """Channel-last floating PCM only. Never guess encoding or axis order."""
    if not isinstance(pcm, np.ndarray):
        raise TypeError("PCM must be a NumPy float32 or float64 array")
    if pcm.dtype not in (np.dtype("float32"), np.dtype("float64")):
        raise TypeError("PCM must be float32 or float64; integer PCM is unsupported")
    if pcm.ndim not in (1, 2) or (pcm.ndim == 2 and pcm.shape[1] == 0):
        raise ValueError("PCM shape must be (samples,) or (samples, channels)")
    count = 1 if pcm.ndim == 1 else pcm.shape[1]
    if channels is not None and count != channels:
        raise ValueError("PCM channel count differs from this stream's declared channels")
    if not np.isfinite(pcm).all() or np.any(np.abs(pcm) > 1):
        raise ValueError("PCM must contain finite normalized samples in [-1, 1]")
    if channel is not None:
        if isinstance(channel, bool) or not isinstance(channel, int):
            raise TypeError("channel must be a zero-based integer or None")
        if not 0 <= channel < count:
            raise ValueError("Selected channel is out of range")
        result = pcm if pcm.ndim == 1 else pcm[:, channel]
    elif count == 1:
        result = pcm if pcm.ndim == 1 else pcm[:, 0]
    elif count == 2:
        result = pcm.mean(axis=1, dtype=np.float64)
    else:
        raise ValueError("More than two channels require explicit channel selection")
    return np.ascontiguousarray(result, dtype=np.float32)


class StreamingResampler:
    """Bounded-history, centered polyphase FIR matching resample_poly defaults.

    Delay outputs until their future input is available. Global rational phase
    and FIR history survive chunk boundaries; finish supplies only final zeros.
    """
    def __init__(self, sample_rate):
        self.sample_rate = rate(sample_rate)
        divisor = math.gcd(self.sample_rate, TARGET_RATE)
        self.up, self.down = TARGET_RATE // divisor, self.sample_rate // divisor
        self.received = self.emitted = self.start = 0
        self.closed = False
        self.buffer = np.empty(0, np.float32)
        if max(self.up, self.down) > 100000:
            raise ValueError("Source rate ratio requires an oversized FIR; resample explicitly before input")
        if self.up != self.down:
            self.half = 10 * max(self.up, self.down)
            h = firwin(2 * self.half + 1, 1 / max(self.up, self.down),
                       window=("kaiser", 5.0)).astype(np.float32) * self.up
            pad = self.down - self.half % self.down
            self.remove = (self.half + pad) // self.down
            self.filter = np.pad(h, (pad, 0))

    def feed(self, samples):
        if self.closed:
            raise ValueError("Resampler is already finished")
        self.received += len(samples)
        if self.up == self.down:
            self.emitted += len(samples)
            return samples.copy()
        self.buffer = np.concatenate((self.buffer, samples))
        limit = max(0, (self.received * self.up - self.half + self.down - 1) // self.down)
        return self._emit(limit)

    def _emit(self, limit):
        if limit <= self.emitted:
            return np.empty(0, np.float32)
        data = upfirdn(self.filter, self.buffer, up=self.up, down=self.down)
        offset = self.emitted + self.remove - self.start * self.up // self.down
        result = data[offset:offset + limit - self.emitted].copy()
        if len(result) != limit - self.emitted:
            raise RuntimeError("Resampler output accounting mismatch")
        self.emitted = limit
        # Align history starts to down so convolution output indexing stays exact.
        earliest = max(0, (self.emitted * self.down - self.half + self.up - 1) // self.up)
        new_start = min(earliest, self.received) // self.down * self.down
        self.buffer = self.buffer[new_start - self.start:].copy()
        self.start = new_start
        return result

    def finish(self):
        if self.closed:
            return np.empty(0, np.float32)
        self.closed = True
        if self.up == self.down or not self.received:
            return np.empty(0, np.float32)
        return self._emit((self.received * self.up + self.down - 1) // self.down)


def prepare_audio(audio, *, sample_rate=None, channel=None, max_duration_s=None):
    """Return model-rate mono PCM and original input duration.

    Extend this function to add other file decoders. The native SDK only sees
    prepared floating samples, so format changes do not require a library build.
    """
    if isinstance(audio, (str, os.PathLike)):
        import soundfile as sf
        path = os.fspath(audio)
        if not path or "://" in path:
            raise ValueError("audio must be a local file path")
        with sf.SoundFile(path) as stream:
            source_rate = int(stream.samplerate)
            duration = len(stream) / source_rate
            if sample_rate is not None and rate(sample_rate) != source_rate:
                raise ValueError("sample_rate conflicts with the audio file metadata")
            if max_duration_s is not None and duration > max_duration_s:
                raise ValueError(f"Audio exceeds this model's {max_duration_s:g}-second limit")
            pcm = stream.read(dtype="float32", always_2d=True)
    else:
        if sample_rate is None:
            raise ValueError("PCM input requires the original sample_rate")
        source_rate = rate(sample_rate)
        pcm = audio
    prepared = mono(pcm, channel)
    duration = len(prepared) / source_rate
    if not len(prepared):
        raise ValueError("Audio must contain samples")
    if max_duration_s is not None and duration > max_duration_s:
        raise ValueError(f"Audio exceeds this model's {max_duration_s:g}-second limit")
    converter = StreamingResampler(source_rate)
    result = np.concatenate((converter.feed(prepared), converter.finish()))
    return result, duration
