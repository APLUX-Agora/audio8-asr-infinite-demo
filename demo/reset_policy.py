"""Soft-reset trigger (business layer; the mechanism is Engine.soft_reset in the SDK).

Principle for long audio: never miss speech (noise turned into text is acceptable); the model and its decoding stay
untouched. After a long non-speech stretch the model can stay on STREAMING_PAD for minutes although speech is back
(the full-precision model does it too).
Trigger: Silero reports a speech segment (vad_active, vad_onset_s) and, reset_after_s after its onset, there has been
no output since (onset - reset_quiet_s). Action: Engine.soft_reset(onset - replay_pre_s): LM context back to the prefix,
the cached audio rows from there (at most replay_max_s, an engine option) are replayed, then live audio continues.
Limits: one reset per speech segment; after a reset that produced no output the next one waits backoff_s.
"Output" = any token other than STREAMING_PAD.
Call check() just before every feed of (at most) one audio clock, i.e. before the engine runs the next clock.
"""
import os


class ResetPolicy:
    def __init__(self, engine, enabled=None):
        self.eng = engine
        self.pad = engine.info["streaming_pad_id"]
        self.enabled = (os.environ.get("A8_RECOVER", "reset") == "reset") if enabled is None else enabled
        self.reset_after = float(os.environ.get("A8_RESET_AFTER_S", "2.0"))
        self.reset_quiet = float(os.environ.get("A8_RESET_QUIET_S", "2.0"))
        self.backoff = float(os.environ.get("A8_RESET_BACKOFF_S", "10"))
        self.replay_pre = 0.5
        self.reset()

    def reset(self):
        """New session."""
        self.next_t = None                  # audio time of the next clock's row (known once the first token is out)
        self.last_text_t = -1e9             # row time of the newest non-PAD token
        self.reset_onset, self.last_reset_t, self.backoff_until = None, None, -1e9
        self.resets = []                    # last 200 {t, onset, replay_rows}; total is separate
        self.reset_count = 0

    def observe(self, tokens):
        """Every token the engine returns (feed / soft_reset / finish)."""
        for t in tokens:
            if t.id != self.pad:
                self.last_text_t = t.audio_t
            self.next_t = t.audio_t + self.eng.clock_s

    def check(self, vad_active, vad_onset_s):
        """Soft-reset now if the trigger holds; returns the replayed tokens (already observed)."""
        on, row_t = vad_onset_s, self.next_t
        if not self.enabled or row_t is None or not vad_active or on is None or on == self.reset_onset:
            return []
        if row_t - on < self.reset_after or self.last_text_t > on - self.reset_quiet:
            return []
        if self.last_reset_t is not None and self.last_text_t < self.last_reset_t:     # previous reset brought no output
            self.backoff_until = max(self.backoff_until, self.last_reset_t + self.backoff)
        if row_t < self.backoff_until:
            return []
        self.reset_onset, self.last_reset_t = on, row_t
        toks = self.eng.soft_reset(on - self.replay_pre)
        self.observe(toks)
        self.resets.append({"t": round(row_t, 2), "onset": round(on, 2), "replay_rows": len(toks)})
        del self.resets[:-200]
        self.reset_count += 1
        return toks
