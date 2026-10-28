#!/usr/bin/env python3
"""Silero VAD silence gate in front of the ASR engine (board CPU, onnxruntime).

Model: Silero VAD v5 ONNX. Framing: 512-sample frames (32 ms @ 16 kHz) prefixed with the previous 64 samples,
recurrent state [2, 1, 128], output = speech probability.

Parameters (set from the demo page, applied at the next reset, i.e. the next Start): threshold, preroll_s (look-ahead:
how long a possibly-silent frame waits for a speech onset), hangover_s.
Only the audio before the first speech onset of a run is gated; after that everything passes untouched. (Gating pauses
mid-stream leaves long stretches of digital silence that the model reads as the end of the audio: with the 30 s rolling
context it can stop transcribing for good.)
Before the onset: frame i is speech with hysteresis (on at p >= threshold, off once p < threshold - 0.15); frame i is
kept if a speech frame lies in [i - hangover, i + preroll], otherwise its samples are replaced by zeros (the engine
clock keeps running, so the text stays aligned with the video). Frames are released as soon as they are decided, so
there is no added latency while someone talks. Zeros are what the model sees in its own synthetic left pad, so gated
stretches look like "nobody talking".

usage:
    g = SileroGate(path_of_silero_vad_onnx); out = g.process(x_chunk) ...; out_tail = g.flush()
    python3 vad_gate.py --model demo/assets/silero_vad.onnx --wav in.wav --out gated.wav   (offline check)
"""
import argparse
from collections import deque

import numpy as np

FRAME, CTX, SR = 512, 64, 16000


class SileroGate:
    def __init__(self, model, threshold=0.5, preroll_s=0.5, hangover_s=1.0, enabled=True):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = so.inter_op_num_threads = 1
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
        self.enabled = enabled
        self.configure(threshold, preroll_s, hangover_s)
        self.reset()

    def configure(self, threshold=None, preroll_s=None, hangover_s=None):
        """New parameters, used from the next reset()."""
        self.params = {"threshold": float(threshold if threshold is not None else self.params["threshold"]),
                       "preroll_s": float(preroll_s if preroll_s is not None else self.params["preroll_s"]),
                       "hangover_s": float(hangover_s if hangover_s is not None else self.params["hangover_s"])}

    def reset(self):
        self.th = self.params["threshold"]
        self.P = int(round(self.params["preroll_s"] * SR / FRAME))       # look-ahead frames
        self.H = int(round(self.params["hangover_s"] * SR / FRAME))
        self.state = np.zeros((2, 1, 128), np.float32)
        self.ctx = np.zeros(CTX, np.float32)
        self.carry = np.zeros(0, np.float32)
        self.frames = deque()            # (samples, is_speech) waiting for their look-ahead
        self.speech_on = False
        self.last_speech = -10 ** 9       # index of the newest speech frame (for speech_recent)
        self.recent = deque(maxlen=int(round(2.0 * SR / FRAME)))   # speech flags of the last 2 s (segment())
        self.seg_start, self.silence_run = None, 10 ** 9
        self.speech_idx = deque()        # indices of speech frames (pruned as frames are released)
        self.n_in = self.n_out = 0       # frames seen / released
        self.n_gated = 0                 # released frames replaced by zeros
        self.opened = False              # lead-only gate: True after the first speech onset (pass-through from then on)
        self.prob = 0.0

    def _vad(self, frame):
        x = np.concatenate([self.ctx, frame])[None]
        p, self.state = self.sess.run(None, {"input": x, "state": self.state, "sr": np.array(SR, np.int64)})
        self.ctx = frame[-CTX:]
        p = float(p.reshape(-1)[0])
        self.speech_on = p >= self.th if not self.speech_on else p >= self.th - 0.15
        return p, self.speech_on

    def _release(self, upto_future):
        """Release frames in order as soon as their keep / gate decision is known (all frames when flushing).

        A frame with speech in [i - H, i] (talking, or within the hangover) is kept and released at once - no added
        latency while someone talks. Only a frame that may be gated waits: it is kept as soon as a speech frame shows up
        within its look-ahead [i + 1, i + P] (the held pre-roll then goes out in one burst and the engine catches up),
        and replaced by zeros once all P look-ahead frames were seen without speech. Same decisions as before, only
        released earlier."""
        out = []
        while self.frames:
            i = self.n_out
            near = self._speech_near(i)                                       # prune even after the gate opens
            later = [s for _, s in list(self.frames)[1:self.P + 1]]          # look-ahead frames seen so far
            if self.opened:
                keep = True                                                  # lead-only: everything after the first onset
            elif near or any(later):
                keep = self.opened = True
            elif upto_future or len(later) >= self.P:
                keep = False
            else:
                break                                                        # undecided: wait for more audio
            samples, _ = self.frames.popleft()
            self.n_out += 1
            if keep or not self.enabled:
                out.append(samples)
            else:
                out.append(np.zeros_like(samples)); self.n_gated += 1
        return out

    def _speech_near(self, i):
        """Is there a speech frame in [i - H, i]? (indices only grow, so older entries can be dropped)"""
        h = self.speech_idx
        while len(h) > 1 and h[1] <= i:
            h.popleft()
        return bool(h) and h[0] <= i and i - h[0] <= self.H

    def process(self, x):
        """Raw samples in -> gated samples out (held back only during possible pauses, up to the preroll; total length
        preserved after flush())."""
        x = np.concatenate([self.carry, np.asarray(x, np.float32)])
        n = x.shape[0] // FRAME
        self.carry = x[n * FRAME:]
        for k in range(n):
            f = x[k * FRAME:(k + 1) * FRAME]
            self.prob, s = self._vad(f)
            if s:
                self.speech_idx.append(self.n_in); self.last_speech = self.n_in
                if self.silence_run >= int(round(0.5 * SR / FRAME)):              # >= 0.5 s without speech: new segment
                    self.seg_start = self.n_in
                self.silence_run = 0
            else:
                self.silence_run += 1
            self.recent.append(s)
            self.frames.append((f, s))
            self.n_in += 1
        out = self._release(False)
        return np.concatenate(out) if out else np.zeros(0, np.float32)

    def flush(self):
        out = self._release(True)
        if self.carry.size:                                              # partial last frame: keep only near speech
            keep = (not self.enabled) or self._speech_near(self.n_out)
            out.append(self.carry if keep else np.zeros_like(self.carry))
            self.carry = np.zeros(0, np.float32)
        return np.concatenate(out) if out else np.zeros(0, np.float32)

    def speech_recent(self, window_s=1.0):
        """Silero heard speech within the last window_s of input (independent of the gate state / enabled)."""
        return self.n_in - 1 - self.last_speech < window_s * SR / FRAME

    def segment(self):
        """(active, onset_s): active = at least 1 s of speech within the last 2 s (debounce); onset_s = start of the current
        speech segment (first speech frame after >= 0.5 s without speech), seconds of input audio."""
        active = sum(self.recent) * FRAME / SR >= 1.0
        return active, (None if self.seg_start is None else round(self.seg_start * FRAME / SR, 3))

    def stats(self):
        return {"speech_prob": round(self.prob, 3), "speech": bool(self.speech_on), "opened": self.opened,
                "gated_s": round(self.n_gated * FRAME / SR, 2), "gated_frac": round(self.n_gated / max(1, self.n_out), 3),
                "enabled": self.enabled}


def main():
    import soundfile as sf
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", required=True, help="Silero VAD ONNX business asset")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--preroll", type=float, default=0.5)
    ap.add_argument("--hangover", type=float, default=1.0)
    a = ap.parse_args()
    x, fs = sf.read(a.wav, dtype="float32")
    assert fs == SR
    g = SileroGate(a.model, a.threshold, a.preroll, a.hangover)
    y = np.concatenate([g.process(x[i:i + 1280]) for i in range(0, x.shape[0], 1280)] + [g.flush()])
    assert y.shape == x.shape, (y.shape, x.shape)
    sf.write(a.out, y, SR, subtype="PCM_16")
    kept = np.abs(y).reshape(-1)[: x.shape[0] // FRAME * FRAME].reshape(-1, FRAME).max(1) > 0
    first = int(np.argmax(kept)) * FRAME / SR if kept.any() else None
    print({**g.stats(), "first_kept_s": first})


if __name__ == "__main__":
    main()
