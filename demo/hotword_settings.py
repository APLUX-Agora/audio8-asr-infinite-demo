"""Validation of user-selected demo controls; inference belongs to the SDK."""
import math


def validate_hotwords(config):
    if not isinstance(config, dict):
        raise ValueError("hotwords must be an object")
    words = config.get("words", [])
    if not isinstance(words, list) or len(words) > 256 or any(
            not isinstance(w, str) or not w.strip() or len(w.encode("utf-8")) > 1024 for w in words):
        raise ValueError("Enter at most 256 nonempty hotwords, up to 1024 bytes each")
    if isinstance(config.get("top_k", 50), bool) or not isinstance(config.get("top_k", 50), int):
        raise ValueError("Top-k must be an integer")
    top_k = config.get("top_k", 50)
    if not 0 <= top_k <= 151936:
        raise ValueError("Top-k must be between 0 and vocabulary size")
    boosts = {}
    for name, default in [("start_boost", 6.0), ("continuation_boost", 8.0)]:
        value = config.get(name, default)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Hotword boosts must be finite numbers between 0 and 100")
        boosts[name] = float(value)
    return dict(words=list(words), top_k=top_k, **boosts)
