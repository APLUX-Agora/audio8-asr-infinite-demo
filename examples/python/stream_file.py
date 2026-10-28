#!/usr/bin/env python3
"""Streaming transcription in real time with the Audio8-ASR-Infinite SDK, for long audio.

The audio file is played into the engine at real-time speed in small chunks, as a microphone would deliver it. Each
piece of text is printed as soon as the engine produces it. Every paragraph starts with the time its first word was
spoken, and a new paragraph starts after each end of turn predicted by the model's semantic VAD.

Long real-world audio (talks with music, applause, video inserts) needs the same two business-layer helpers as the web
demo, imported from demo/:
  - vad_gate.SileroGate: replaces the non-speech before the first speech onset with silence;
  - reset_policy.ResetPolicy: after a long non-speech stretch the model can stay silent although speech is back; the
    policy then calls ASRStream.soft_reset (the model re-listens to the last seconds). Without it the transcript can stop
    for minutes (try --plain on examples/audio/xiaomi18pro_highlights_10min_16k.flac).
At the end the processing lag is reported: how long after its audio had arrived each piece of text came out (the
model's fixed 480 ms transcription delay comes on top of it).

usage: python3 examples/python/stream_file.py examples/audio/xiaomi18pro_highlights_10min_16k.flac --lang zh
       [--clock-ms 160|80] [--chunk-ms 80] [--eot-horizon 2] [--eot-threshold 0.6] [--fast] [--plain]
"""
import argparse
import codecs
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "demo"))
from audio8_asr import ASRModel, A8Error, resolve_model_dir  # noqa: E402
from reset_policy import ResetPolicy  # noqa: E402
from transcribe_file import SR, load_audio  # noqa: E402
from example_lifecycle import managed_engine, ExampleInterrupted  # noqa: E402

PUNCT = " .,!?;:)]\"'”’。，！？；：、）》」』"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("audio")
    ap.add_argument("--clock-ms", type=int, default=None, choices=[160, 80],
                    help="audio clock: 160 or 80 ms; default: the installed one (160 first)")
    ap.add_argument("--lang", default="en", choices=["en", "zh"], help="language spoken in the audio")
    ap.add_argument("--models", default=os.environ.get("A8_MODELS"),
                    help="package root containing manifest.json; default: discover this demo models directory")
    ap.add_argument("--chunk-ms", type=int, default=80, help="audio delivered per chunk (like a microphone buffer)")
    ap.add_argument("--eot-horizon", type=float, default=2.0, choices=[0.5, 1.0, 2.0, 3.0],
                    help="end of turn = P(no speech within this many seconds)")
    ap.add_argument("--eot-threshold", type=float, default=0.6, help="end-of-turn probability that starts a new paragraph")
    ap.add_argument("--fast", action="store_true", help="feed as fast as possible instead of real time")
    ap.add_argument("--plain", action="store_true", help="no silence gate and no soft-reset policy (the bare engine)")
    a = ap.parse_args()
    try:
        a.models = resolve_model_dir(a.models, models_root=os.path.join(ROOT, "models"))
    except A8Error as error:
        ap.error(str(error))
    print(f"[example] model package: {a.models}", file=sys.stderr)

    audio = load_audio(a.audio)
    with managed_engine(ASRModel.from_pretrained, a.models, clock_ms=a.clock_ms) as (model, check_interrupted), model.create_stream(sample_rate=SR, language=a.lang) as eng:
        gate, pol = None, None
        if not a.plain:
            from vad_gate import SileroGate                          # needs onnxruntime
            gate = SileroGate(os.path.join(ROOT, "demo", "assets", "silero_vad.onnx"))
            pol = ResetPolicy(eng)
        h = eng.info["eot_horizons_s"].index(a.eot_horizon)
        delay_s = eng.info["num_delay_tokens"] * eng.clock_s
        print(f"[{eng.info['clock_ms']} ms clock, {1000 * delay_s:.0f} ms model delay; "
              f"{len(audio) / SR:.1f} s of audio, {'fast' if a.fast else 'real time'}{', plain' if a.plain else ''}]",
              file=sys.stderr)

        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")   # a token can hold part of a character
        chunk = SR * min(a.chunk_ms, round(1000 * eng.clock_s)) // 1000  # <= one clock: the policy runs before each clock
        lags, n_tok, n_resets = [], 0, 0
        started, armed, due, pending = False, False, None, False
        t0 = time.time()

        def show(toks):
            nonlocal n_tok, started, armed, due, pending
            for t in toks:
                n_tok += 1
                # End of turn. The prediction of a step is about audio whose text is still num_delay_tokens tokens away,
                # so the paragraph break waits for that text (one break per end-of-turn episode).
                on = t.eot[h] >= a.eot_threshold
                if on and armed:
                    due, armed = n_tok + eng.info["num_delay_tokens"], False
                elif not on and started:
                    armed = True
                if due is not None and n_tok >= due:
                    due, pending = None, started
                piece = dec.decode(eng.token_bytes(t.id))
                if not piece:
                    continue
                if pending:                                       # closing punctuation stays with the previous paragraph
                    lead = piece[:len(piece) - len(piece.lstrip(PUNCT))]
                    print(lead.rstrip(), end="")
                    piece = piece[len(lead):]
                    if not piece.strip():
                        continue
                    print(flush=True)
                    pending, started = False, False
                if not started:
                    if not piece.strip():
                        continue
                    print(f"[{max(0.0, t.audio_t - delay_s):7.2f} s] ", end="")   # when the first word was spoken
                    piece, started = piece.lstrip(), True
                print(piece, end="", flush=True)
                lags.append(time.time() - t0 - t.audio_t)         # text out vs. its audio having arrived

        def feed(x):
            nonlocal pending, n_resets
            if pol is not None:
                toks = pol.check(*gate.segment())                 # soft reset (re-listen) if the model got stuck
                if len(pol.resets) > n_resets:
                    n_resets, pending = len(pol.resets), started  # the replayed text starts a new paragraph
                show(toks)
            check_interrupted()
            eng.feed(x)
            new = list(eng.last_tokens)
            check_interrupted()
            if pol is not None:
                pol.observe(new)
            show(new)

        check_interrupted()
        for i in range(0, len(audio), chunk):
            if not a.fast:                                        # wait until this chunk "has been spoken"
                time.sleep(max(0.0, t0 + (i + chunk) / SR - time.time()))
            x = audio[i:i + chunk]
            if gate is not None:
                x = gate.process(x)                               # released audio (the gate may hold some back briefly)
                if i + chunk >= len(audio):
                    x = np.concatenate([x, gate.flush()])
            for j in range(0, len(x), chunk):                     # at most one clock per feed
                feed(x[j:j + chunk])
        check_interrupted()
        result = eng.finish()
        show(eng.last_tokens)
        print(f"[finish_reason={result.finish_reason}]", file=sys.stderr)
        check_interrupted()
        print(dec.decode(b"", final=True), flush=True)
        if lags and not a.fast:
            lags.sort()
            print(f"[processing lag: median {lags[len(lags) // 2]:.2f} s, max {lags[-1]:.2f} s "
                  f"(+ {1000 * delay_s:.0f} ms model delay); wall {time.time() - t0:.1f} s; soft resets {n_resets}]",
                  file=sys.stderr)
        elif a.fast:
            print(f"[wall {time.time() - t0:.1f} s; soft resets {n_resets}]", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except ExampleInterrupted as error:
        print(str(error), file=sys.stderr)
        sys.exit(128 + error.signum)
