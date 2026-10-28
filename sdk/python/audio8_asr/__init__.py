"""Audio8-ASR-Infinite task API with owned synchronous recording sessions."""
from __future__ import annotations
import codecs
from functools import wraps
from contextlib import contextmanager
import json
from pathlib import Path
import signal
import threading

import numpy as np
from ._native import (_Native, A8Error, resolve_model_dir, installed_clocks,
                                    extra_file, model_files, _manifest)
from .audio import prepare_audio, mono, rate, StreamingResampler
from .types import (ASRCapabilities, ASRError, ASRLoadError, ASRInferenceError,
                       ASRStateError, ASRUnsupportedError, HotwordConfig,
                       TranscriptionResult, TranscriptionUpdate,
                       generation_limit, hotword_config)


@contextmanager
def _native_signals():
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def _failure(error, category=ASRInferenceError):
    return category(str(error), native_code=getattr(error, 'code', None))


def _language(value):
    if value is not None and not isinstance(value, str):
        raise TypeError('language must be a string or None')
    if value not in (None, 'zh', 'en'):
        raise ASRUnsupportedError('Infinite supports default Chinese or explicit zh/en, not auto')
    return value or 'zh'


class ASRModel:
    _capabilities = ASRCapabilities(True, ('zh', 'en'), ('zh', 'en'), False, False, True, True)

    @classmethod
    def from_pretrained(cls, model_dir=None, *, library=None, clock_ms=None, roll_s=28.8,
                        stable_rows=-1, semantic_vad=True, replay_max_s=10.0):
        model = cls.__new__(cls)
        model._native = None
        model._request = threading.Lock()
        model._failed = False
        model._stats = {}
        try:
            model.model_dir = resolve_model_dir(model_dir)
            if clock_ms is not None and (isinstance(clock_ms, bool) or clock_ms not in (80, 160)):
                raise ValueError('clock_ms must be 80, 160 or None')
            if isinstance(stable_rows, bool) or not isinstance(stable_rows, int) or stable_rows < -1:
                raise ValueError('stable_rows must be -1 or a nonnegative integer')
            if not isinstance(semantic_vad, bool):
                raise TypeError('semantic_vad must be a bool')
            for name, value in [('roll_s', roll_s), ('replay_max_s', replay_max_s)]:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
                    raise ValueError(f'{name} must be a finite nonnegative number')
            # Assign the owner before entering native create, including its return handoff.
            model._native = _Native.__new__(_Native)
            model._native._h = None
            with _native_signals():
                model._native.__init__(model.model_dir, clock_ms, 'zh', roll_s, stable_rows,
                                       semantic_vad, replay_max_s, library=library)
            native = model._native
            model._info = dict(native.info)
            model._stats = native.stats()
            model.sdk_version = native._lib.a8_version().decode()
            manifest = _manifest(model.model_dir)
            clock = manifest['clocks'][str(model._info['clock_ms'])]
            vocabulary_file = Path(model.model_dir) / clock['token_bytes']
            # Existing packages store the token-byte table in this clock's manifest.
            model._vocabulary = len(json.loads(vocabulary_file.read_text()))
            return model
        except BaseException as error:
            if model._native is not None:
                with _native_signals():
                    model._native.close()
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            raise _failure(error, ASRLoadError) from error

    @property
    def capabilities(self):
        return self._capabilities

    @property
    def info(self):
        """Read-only-by-copy native profile for Infinite's advanced integrations."""
        return dict(self._info)

    def stats(self):
        """Last owned-call snapshot; querying does not race an active native call."""
        return dict(self._stats)

    def _claim(self):
        if not self._request.acquire(blocking=False):
            raise ASRStateError('Model is busy; close its recording before another request')
        if self._native is None or self._failed:
            self._request.release()
            raise ASRStateError('Model is closed or requires recreation after a native failure')

    def _stream(self, *, sample_rate, channels, channel, language, prompt, hotwords, max_new_tokens):
        language = _language(language)
        if prompt is not None:
            if not isinstance(prompt, str):
                raise TypeError('prompt must be a string or None')
            raise ASRUnsupportedError('Infinite does not support a free-text prompt')
        limit = generation_limit(max_new_tokens, default=0, maximum=2**63-1)
        source_rate = rate(sample_rate)
        if isinstance(channels, bool) or not isinstance(channels, int):
            raise TypeError('channels must be a positive integer')
        if channels < 1:
            raise ValueError('channels must be positive')
        # Validate source selection without waiting for the first real chunk.
        mono(np.empty((0, channels), np.float32), channel, channels=channels)
        config = hotword_config(hotwords, max_words=256, max_bytes=1024,
                                max_boost=100, vocabulary=self._vocabulary)
        stream = ASRStream(self, source_rate, channels, channel, language)
        try:
            with _native_signals():
                self._native.begin_request(int(language == 'en'), limit)
                self._native.set_hotwords(config.words, top_k=config.top_k,
                    start_boost=config.start_boost, continuation_boost=config.continuation_boost)
        except BaseException as error:
            self._failed = True
            if isinstance(error, A8Error):
                raise _failure(error) from error
            raise
        return stream

    def create_stream(self, *, sample_rate, channels=1, channel=None, language=None,
                      prompt=None, hotwords=None, max_new_tokens=None):
        self._claim()
        try:
            return self._stream(sample_rate=sample_rate, channels=channels, channel=channel,
                                language=language, prompt=prompt, hotwords=hotwords,
                                max_new_tokens=max_new_tokens)
        except BaseException:
            self._request.release()
            raise

    def transcribe(self, audio, *, sample_rate=None, channel=None, language=None,
                   prompt=None, hotwords=None, max_new_tokens=None):
        self._claim()
        stream = None
        try:
            # Validate unsupported request options before opening an input file.
            _language(language)
            if prompt is not None:
                if not isinstance(prompt, str):raise TypeError('prompt must be a string or None')
                raise ASRUnsupportedError('Infinite does not support a free-text prompt')
            generation_limit(max_new_tokens, default=0, maximum=2**63-1)
            pcm, duration = prepare_audio(audio, sample_rate=sample_rate, channel=channel)
            if len(pcm) > 2**31-1:
                raise ValueError('Finite audio exceeds native call capacity; use a live stream')
            stream = self._stream(sample_rate=16000, channels=1, channel=None,
                                  language=language, prompt=prompt, hotwords=hotwords,
                                  max_new_tokens=max_new_tokens)
            return stream._finish_audio(pcm, duration)
        finally:
            if stream is None:
                self._request.release()
            else:
                stream.close()

    def close(self):
        if not self._request.acquire(blocking=False):
            raise ASRStateError('Close the active recording and wait for native calls before closing')
        try:
            if self._native is not None:
                with _native_signals():self._native.close()
                self._native = None
        finally:
            self._request.release()

    def __enter__(self):
        if self._native is None:raise ASRStateError('Model is closed')
        return self

    def __exit__(self, *_):self.close()


def _owned_call(function):
    @wraps(function)
    def call(self, *args, **kwargs):
        if not self._operation.acquire(blocking=False):
            raise ASRStateError('Recording has an active operation; wait before calling again')
        try:
            return function(self, *args, **kwargs)
        finally:
            self._operation.release()
    return call


class ASRStream:
    """One live recording; owner serializes feed, finish and close."""
    def __init__(self, model, sample_rate, channels, channel, language):
        self._operation = threading.Lock()
        self._model = model
        self.sample_rate, self.channels, self.channel = sample_rate, channels, channel
        self.language = language
        self._converter = StreamingResampler(sample_rate)
        self._decoder = codecs.getincrementaldecoder('utf-8')('strict')
        self._pieces = []
        self._frames = 0
        self._result = None
        self._closed = False
        self._last_tokens = ()

    @property
    def info(self):
        return dict(self._model._info, lang=self.language)

    @property
    def sampling_rate(self):return 16000

    @property
    def samples_per_token(self):return self.info['samples_per_token']

    @property
    def clock_s(self):return self.samples_per_token / 16000

    @property
    def last_tokens(self):
        """Copied native token/EOT diagnostics from the last owned operation."""
        return self._last_tokens

    def stats(self):return self._model.stats()

    def _open(self):
        if self._closed:raise ASRStateError('Recording is closed')
        if self._model._failed:raise ASRStateError('Model requires recreation after native failure')

    def _execute(self, function, *args):
        try:
            with _native_signals():return function(*args)
        except BaseException as error:
            self._model._failed = True
            if isinstance(error, A8Error):raise _failure(error) from error
            raise

    def _collect(self, tokens):
        self._last_tokens = tuple(tokens)
        try:
            delta = ''.join(self._decoder.decode(self._model._native.token_bytes(t.id))
                            for t in tokens if t.is_text)
        except UnicodeError as error:
            self._model._failed = True
            raise ASRInferenceError('Invalid UTF-8 from native token stream') from error
        if delta:self._pieces.append(delta)
        self._model._stats = self._execute(self._model._native.stats)
        return delta

    def _final(self, reason, duration):
        try:
            tail = self._decoder.decode(b'', final=reason == 'stop')
        except UnicodeError as error:
            self._model._failed = True
            raise ASRInferenceError('Incomplete UTF-8 at normal native completion') from error
        if tail:self._pieces.append(tail)
        self._result = TranscriptionResult(''.join(self._pieces), self.language, duration, reason)
        return self._result

    @_owned_call
    def feed(self, pcm):
        self._open()
        if self._result is not None:raise ASRStateError('Recording has already finished')
        samples = mono(pcm, self.channel, channels=self.channels)
        self._frames += len(samples)
        converted = self._converter.feed(samples)
        if len(converted) > 2**31-1:raise ValueError('PCM chunk exceeds native capacity')
        native = self._model._native
        tokens = self._execute(native.feed, converted) if len(converted) else []
        delta = self._collect(tokens)
        if self._execute(native.request_state) == 2:
            result = self._final('length', self._frames / self.sample_rate)
            return TranscriptionUpdate(result.text, delta, 'length')
        return TranscriptionUpdate(''.join(self._pieces), delta)

    @_owned_call
    def _finish_audio(self, pcm, duration):
        self._open()
        native = self._model._native
        tokens = self._execute(native.finish_audio, pcm)
        self._collect(tokens)
        reason = 'length' if self._execute(native.request_state) == 2 else 'stop'
        return self._final(reason, duration)

    @_owned_call
    def finish(self):
        if self._result is not None:return self._result
        self._open()
        if not self._frames:raise ValueError('Recording must contain audio before finish')
        native = self._model._native
        # EOF is declared before the converter's remaining samples reach native.
        tokens = self._execute(native.finish_audio, self._converter.finish())
        self._collect(tokens)
        reason = 'length' if self._execute(native.request_state) == 2 else 'stop'
        return self._final(reason, self._frames / self.sample_rate)

    @_owned_call
    def token_bytes(self, tid):
        """Advanced byte access for the demo's token-timestamp policy."""
        self._open()
        return self._execute(self._model._native.token_bytes, tid)

    def text_of(self, ids):return b''.join(self.token_bytes(tid) for tid in ids)

    @_owned_call
    def eot_probs(self):
        self._open()
        return self._execute(self._model._native.eot_probs)

    @_owned_call
    def soft_reset(self, replay_from_s):
        """Advanced replay; caller owns the text-revision/endpoint policy."""
        self._open()
        if self._result is not None:raise ASRStateError('Recording is finished')
        tokens = self._execute(self._model._native.soft_reset, replay_from_s)
        # Replay starts a new native language sequence, not a continuation byte.
        self._decoder = codecs.getincrementaldecoder('utf-8')('strict')
        self._collect(tokens)
        if self._execute(self._model._native.request_state) == 2:
            self._final('length', self._frames / self.sample_rate)
        return list(self._last_tokens)

    @_owned_call
    def close(self):
        if not self._closed:
            self._closed = True
            self._model._request.release()

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, *_):self.close()
