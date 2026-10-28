#!/usr/bin/env python3
"""Transcribe a local WAV/FLAC/MP3 file with the public task API."""
import argparse
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
from audio8_asr import ASRModel, HotwordConfig, resolve_model_dir
from audio8_asr.audio import prepare_audio
from example_lifecycle import managed_engine, ExampleInterrupted

SR = 16000


def load_audio(path):
    # Editable Python preprocessing, shared with ASRModel's file input.
    return prepare_audio(path)[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--models", default=os.environ.get("A8_MODELS"))
    ap.add_argument("--clock-ms", type=int, choices=[80, 160])
    ap.add_argument("--lang", default=None, choices=["en", "zh"])
    ap.add_argument("--max-new-tokens", type=int)
    ap.add_argument("--hotword", action="append", default=[])
    ap.add_argument("--hotword-top-k", type=int, default=50)
    ap.add_argument("--hotword-start-boost", type=float, default=6.0)
    ap.add_argument("--hotword-continuation-boost", type=float, default=8.0)
    a = ap.parse_args()
    hints = HotwordConfig(tuple(a.hotword), a.hotword_top_k,
                          a.hotword_start_boost, a.hotword_continuation_boost)
    with managed_engine(ASRModel.from_pretrained, resolve_model_dir(a.models, models_root=ROOT / "models"), clock_ms=a.clock_ms) as (model, check):
        check()
        start = time.monotonic()
        result = model.transcribe(a.audio, language=a.lang, hotwords=hints,
                                  max_new_tokens=a.max_new_tokens)
        check()
        print(result.text)
        print(f"[finish_reason={result.finish_reason}, audio={result.duration_s:.2f}s, "
              f"wall={time.monotonic()-start:.2f}s]", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except ExampleInterrupted as error:
        print(str(error), file=sys.stderr)
        sys.exit(128 + error.signum)
