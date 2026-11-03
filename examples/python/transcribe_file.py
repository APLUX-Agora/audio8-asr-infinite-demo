#!/usr/bin/env python3
"""Transcribe a local WAV/FLAC/MP3 file with the public task API."""
import argparse
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
from audio8_asr import Runtime, CpuOptions, ASRModel, HotwordConfig, resolve_model_dir
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
    ap.add_argument("--cpu-affinity", default="default", help="default, inherit, or comma-separated CPU IDs")
    a = ap.parse_args()
    try:
        affinity=a.cpu_affinity if a.cpu_affinity in ("inherit","default") else [int(x) for x in a.cpu_affinity.split(",")]
        runtime=Runtime(cpu=CpuOptions(affinity=affinity))
    except (TypeError, ValueError) as error:
        ap.error(str(error))
    hints = HotwordConfig(tuple(a.hotword), a.hotword_top_k,
                          a.hotword_start_boost, a.hotword_continuation_boost)
    print("[1/3] Loading model; please wait for initialization...", file=sys.stderr, flush=True)
    with runtime, managed_engine(ASRModel.from_pretrained, resolve_model_dir(a.models, models_root=ROOT / "models"), clock_ms=a.clock_ms, runtime=runtime) as (model, check):
        check()
        print("[2/3] Transcribing audio; text is printed when this file finishes. Ctrl+C to stop.", file=sys.stderr, flush=True)
        start = time.monotonic()
        result = model.transcribe(a.audio, language=a.lang, hotwords=hints,
                                  max_new_tokens=a.max_new_tokens)
        check()
        print("[3/3] Transcription complete.", file=sys.stderr, flush=True)
        print(result.text)
        print(f"[finish_reason={result.finish_reason}, audio={result.duration_s:.2f}s, "
              f"wall={time.monotonic()-start:.2f}s]", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except ExampleInterrupted as error:
        print(str(error), file=sys.stderr)
        sys.exit(128 + error.signum)
