"""Public task data and errors for the independently delivered ASR model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Tuple


class ASRError(RuntimeError):
    """Model/runtime failure; native_code retains this SDK's original identity."""
    def __init__(self, message, *, native_code=None):
        super().__init__(message)
        self.native_code = native_code


class ASRLoadError(ASRError):
    pass


class ASRInferenceError(ASRError):
    pass


class ASRStateError(ASRError):
    pass


class ASRUnsupportedError(ASRError):
    pass


@dataclass(frozen=True)
class ASRCapabilities:
    streaming: bool
    supported_languages: Tuple[str, ...]
    selectable_languages: Tuple[str, ...]
    auto_language: bool
    prompt: bool
    hotwords: bool
    max_new_tokens: bool


@dataclass(frozen=True)
class HotwordConfig:
    words: Tuple[str, ...]
    top_k: int = 50
    start_boost: float = 6.0
    continuation_boost: float = 8.0

    def __post_init__(self):
        if isinstance(self.words, (str, bytes)):
            raise TypeError("HotwordConfig.words must be a sequence of strings")
        object.__setattr__(self, "words", tuple(self.words))


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: Optional[str]
    duration_s: float
    finish_reason: Literal["stop", "length"]

    @property
    def is_complete(self):
        return self.finish_reason == "stop"


@dataclass(frozen=True)
class TranscriptionUpdate:
    text: str
    delta: str
    finish_reason: Optional[Literal["stop", "length"]] = None

    @property
    def is_final(self):
        return self.finish_reason is not None


def hotword_config(value, *, max_words, max_bytes, max_boost, vocabulary):
    """Validate before touching native request state; do not truncate hints."""
    import math
    if value is None:
        value = HotwordConfig(())
    elif not isinstance(value, HotwordConfig):
        if not isinstance(value, (list, tuple)):
            raise TypeError("hotwords must be a list/tuple of strings or HotwordConfig")
        value = HotwordConfig(tuple(value))
    if len(value.words) > max_words:
        raise ValueError(f"At most {max_words} hotwords are supported")
    for word in value.words:
        if not isinstance(word, str):
            raise TypeError("Each hotword must be a string")
        if not word.strip() or "\0" in word or len(word.encode("utf-8")) > max_bytes:
            raise ValueError(f"Hotwords must be nonempty, NUL-free, at most {max_bytes} UTF-8 bytes")
    if isinstance(value.top_k, bool) or not isinstance(value.top_k, int):
        raise TypeError("Hotword top_k must be an integer")
    if not 0 <= value.top_k <= vocabulary:
        raise ValueError(f"Hotword top_k must be in 0..{vocabulary}")
    for boost in (value.start_boost, value.continuation_boost):
        if isinstance(boost, bool) or not isinstance(boost, (int, float)):
            raise TypeError("Hotword boosts must be finite numbers")
        if not math.isfinite(boost) or not 0 <= boost <= max_boost:
            raise ValueError(f"Hotword boosts must be in 0..{max_boost}")
    return value


def generation_limit(value, *, default, maximum=None):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_new_tokens must be a positive integer or None")
    if value < 1 or (maximum is not None and value > maximum):
        raise ValueError("max_new_tokens is outside this model's supported range")
    return value
