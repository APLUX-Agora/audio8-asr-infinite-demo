#!/usr/bin/env python3
"""Transcribe an audio file with the Audio8-ASR-Infinite SDK: the smallest complete use of the Python binding.

The text is printed while the file is processed, then the speed is reported. This is the bare engine; for long audio with
music or long pauses use stream_file.py, which adds the silence gate and the soft-reset policy of the web demo.
Audio files that soundfile reads (wav, flac, ogg, mp3, ...): channels are averaged and other sample rates are resampled
to 16 kHz. For videos use the web demo (or extract the audio first).

usage: python3 examples/python/transcribe_file.py examples/audio/jobs_keynote_10min_16k.flac [--clock-ms 160|80] [--lang en|zh] [--models models]
"""
import argparse
import codecs
import os
import sys
import time
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "sdk", "python"))
from audio8_asr import Engine, A8Error, resolve_model_dir  # noqa: E402
from example_lifecycle import managed_engine, ExampleInterrupted  # noqa: E402

SR = 16000


def load_audio(path):
    """float32 mono 16 kHz samples in [-1, 1], (soundfile + resampling with scipy's polyphase
    resampler)."""
    try:
        x, fs = sf.read(path, dtype="float32", always_2d=True)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"cannot read {path} as audio ({e}).\nUse an audio file (wav, flac, ogg, mp3); for videos use the web demo "
                 "or extract the audio first.")
    x = x.mean(axis=1)
    if fs != SR:
        g = gcd(int(fs), SR)
        x = resample_poly(x, SR // g, int(fs) // g)
    return np.clip(x, -1.0, 1.0).astype(np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("audio")
    ap.add_argument("--clock-ms", type=int, default=None, choices=[160, 80],
                    help="audio clock: 160 or 80 ms; default: the installed one (160 first)")
    ap.add_argument("--lang", default="en", choices=["en", "zh"], help="language spoken in the audio")
    ap.add_argument("--models", default=os.environ.get("A8_MODELS"),
                    help="package root containing manifest.json; default: discover this demo models directory")
    ap.add_argument("--hotword", action="append", default=[], help="optional word/phrase; repeat for multiple terms")
    ap.add_argument("--tokenizer", help="matching tokenizer.json, required when the package has no tokenizer extra")
    ap.add_argument("--hotword-top-k", type=int, default=50)
    ap.add_argument("--hotword-start-boost", type=float, default=6.0)
    ap.add_argument("--hotword-continuation-boost", type=float, default=8.0)
    a = ap.parse_args()
    try:
        a.models = resolve_model_dir(a.models)
    except A8Error as error:
        ap.error(str(error))
    print(f"[example] model package: {a.models}", file=sys.stderr)

    audio = load_audio(a.audio)
    t0 = time.time()
    with managed_engine(Engine, a.models, clock_ms=a.clock_ms, lang=a.lang) as (eng, check_interrupted):
        print(f"[{eng.info['clock_ms']} ms clock models loaded in {time.time() - t0:.1f} s]", file=sys.stderr)

        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")   # a token can hold part of a character
        eng.reset()                                                 # new session
        if a.hotword:
            eng.set_hotwords(a.hotword, tokenizer_path=a.tokenizer, top_k=a.hotword_top_k,
                             start_boost=a.hotword_start_boost, continuation_boost=a.hotword_continuation_boost)
        t0 = time.time()
        check_interrupted()
        for i in range(0, len(audio), SR):                          # feed 1 s at a time (any chunk size works)
            check_interrupted()
            toks = eng.feed(audio[i:i + SR])
            check_interrupted()
            print(dec.decode(eng.text_of([t.id for t in toks])), end="", flush=True)
        check_interrupted()
        toks = eng.finish()                                         # end of input: flush the last words
        check_interrupted()
        print(dec.decode(eng.text_of([t.id for t in toks]), final=True), flush=True)
        wall = time.time() - t0
        dur = len(audio) / SR
        print(f"[{dur:.1f} s of audio in {wall:.1f} s, RTF {wall / dur:.2f}]", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except ExampleInterrupted as error:
        print(str(error), file=sys.stderr)
        sys.exit(128 + error.signum)
