# C ABI integration from C/C++

Use [include/audio8_asr.h](include/audio8_asr.h) and the delivered `lib/libaudio8_asr.so`.
The header has `extern "C"` guards and can be included from C++ directly. There is no additional C++ class SDK
or separate inference implementation. Core engine sources and build tools are maintained internally.

## Target and linking

The prebuilt library is Linux AArch64, with AidLite and its QNN 2.48 backend plus the matching board BSP/driver.
It does not run natively on Windows, macOS or x86 Linux. Required Linux symbol versions include GLIBC 2.34
and GLIBCXX 3.4.30; install the platform-supported C++ runtime, not a library copied from another OS.
Direct dependencies include `libaidlite.so`, `libstdc++.so.6`, `libm.so.6`, `libgcc_s.so.1`, `libc.so.6`
and the AArch64 loader. ICU code and Unicode data are embedded. QNN/RPC/driver dependencies remain external.

Build the [complete example](../examples/cpp/transcribe_file.cpp) on the board, from the checkout root:

```bash
cmake -S examples/cpp -B examples/cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build examples/cpp/build -j2
examples/cpp/build/transcribe_file --models models/qnn248_qcs8550 --lang en input.wav
```

The build needs a C++11 compiler and CMake 3.16+, installed separately if absent (`sudo apt install g++ cmake`).
It links the existing `.so`, without rebuilding the engine. `-DAUDIO8_SDK_ROOT=/absolute/path/to/sdk` selects
another matched SDK installation. The example accepts only nonempty mono 16 kHz PCM16 RIFF/WAV input, explicitly
converts samples to float32, and requires the package-root `--models` path. It does not resample or read FLAC/video.
For another source format, convert first, for example:

```bash
ffmpeg -i examples/audio/jobs_keynote_10min_16k.flac -ac 1 -ar 16000 -c:a pcm_s16le input.wav
```

An equivalent direct build (repository root) is:

```bash
g++ -std=c++11 -O2 -Wall -Wextra -Wpedantic examples/cpp/transcribe_file.cpp \
  -Isdk/include -Lsdk/lib -laudio8_asr -Wl,-rpath,'$ORIGIN/sdk/lib' -o audio8-example
./audio8-example --models models/qnn248_qcs8550 --lang en input.wav
```

The `$ORIGIN` above is the executable's directory, not the shell's current directory. CMake embeds the selected
SDK's absolute build RPATH for the example. Moving the executable requires adjusting its RPATH or setting
`LD_LIBRARY_PATH=/absolute/path/to/sdk/lib:/usr/local/lib`; the vendor runtime must also be discoverable.
The SDK `.so` itself has no RPATH/RUNPATH. Use `ldd` on the target to diagnose missing dependencies.

## Ownership and call order

1. Fill `a8_options` using `a8_default_options`, then set the desired clock/language and supported options.
2. Call `a8_create` with a directory directly containing the matching manifest. `NULL` means failure; immediately
   read `a8_create_error()` (thread-local). No engine may be used on failure.
3. Call `a8_reset` for the session; optionally configure hotwords before feeding audio.
4. Feed audio and drain all queued tokens. Calls are synchronous, and one engine is used by one thread at a time.
5. Call `a8_finish` once, then drain its final tokens. To feed or soft-reset again, first start a session with reset.
6. Call `a8_destroy` exactly once for each successful creation, including on application errors and interruption.

The example uses a local `unique_ptr` deleter for exception-safe ownership; this is example code, not a new SDK
wrapper. Its SIGTERM/SIGINT handler records a request only. It waits for native creation/inference to return
before unwinding and destroying. Do not throw from a signal handler, destroy from a competing thread, or rely on
process exit to reclaim DSP resources. A SIGKILL/crash cannot run application cleanup. Graceful interruption may
wait for the current synchronous native call; it is not an immediate cancel API.

The SDK owns the engine and its graphs/caches. PCM, options, output buffers and result structs are supplied by the
caller. Do not free native error/version string pointers. Copy an error message before making another operation
on the same engine. The library neither owns a file reader nor creates a background worker.

## Options and data structures

Use the declarations and field comments in the header as the exact layout; do not repack/reorder structs.

| Structure | Fields and units |
| --- | --- |
| `a8_options` | `clock_ms`: 160(default)/80; `lang`: A8_LANG_ZH(default)/A8_LANG_EN; `roll_s`: 28.8 seconds(default), 0 disables rolling; `stable_rows`: -1 selects default, otherwise valid retained cache rows; `semantic_vad`: 1(default)/0; `replay_max_s`: 10 seconds(default), nonnegative and within the context/replay budget. |
| `a8_token` | `id` int32; `is_text` int32 flag; `audio_t` float seconds from session start excluding synthetic padding; `eot[4]` no-speech probabilities at 0.5/1/2/3 seconds, zero when disabled. EOS is not emitted. |
| `a8_info` | Sampling rate, samples/clock, clock/language, four horizon seconds, delay-token count, pad ID, default tail clocks and rolling seconds. Read after creation; use `samples_per_token/sampling_rate` for clock duration. |
| `a8_stats` | Audio seconds; emitted token count; absolute LM position; trim/reset counts; cumulative stage milliseconds. Full field names and integer widths are in the header and [Python result reference](PYTHON_API.md#results-and-attributes). |

Do not change an engine's creation options in-place. Use the package for the selected clock/SoC. The 80ms and
160ms resources remain independent, with complete manifests and checksums; see [model placement](../models/README.md).

## Function reference

Functions returning `int` use a nonnegative success/count and negative `A8_ERR_*` errors unless noted.
Read `a8_last_error(engine)` immediately on failure; Python error-code meanings are listed in [Errors](PYTHON_API.md#errors).

| Function | Parameters and result |
| --- | --- |
| `a8_version()` | Returns a library-owned NUL-terminated version string. |
| `a8_default_options(opt)` | Fills the caller's non-NULL options pointer; returns void. |
| `a8_create(model_dir,opt)` | Package-root UTF-8/filesystem path and initialized options pointer. Returns engine handle or NULL; creation is synchronous. |
| `a8_create_error()` | Library-owned description of the last creation failure on this thread. |
| `a8_destroy(engine)` | Releases the handle/resources; returns void. After destruction the handle is invalid; do not double-destroy or race an in-flight call. |
| `a8_get_info(engine,out)` | Fills caller-owned `a8_info`, returns 0 on success. |
| `a8_last_error(engine)` | Library-owned current error string, not a heap allocation for the caller to free. |
| `a8_reset(engine)` | Resets session state, positions, time, token queue and counters. Returns 0; retains hotword configuration but clears its matching history. |
| `a8_feed(engine,pcm,n)` | `n` finite mono float32 samples at 16 kHz in [-1,1], `n` fits C int; data is consumed before return. Returns count of newly queued tokens, possibly 0. Chunk size is caller-selected. Feed after finish is a state error. |
| `a8_read_tokens(engine,out,cap)` | Caller array of at least `cap` a8_token structs, with nonnegative capacity. Pops up to cap oldest queued tokens; returns number written. Repeatedly drain until the queue is empty. |
| `a8_token_bytes(engine,id,buf,cap)` | Writes up to cap UTF-8 bytes to caller storage, not NUL-terminated. Returns the full required byte count, which can exceed cap; then allocate a larger buffer and retry. Empty for non-text tokens. Never treat the required size as bytes already written. Characters can span tokens, so preserve/incrementally decode the byte stream. |
| `a8_finish(engine,tail_tokens)` | `-1` default silent tail (5/7 clocks for160/80ms), or a nonnegative clock count. Returns new token count. Call once per session and drain; no further feed/soft_reset until reset. Drain token bytes before resetting or destroying the handle. |
| `a8_soft_reset(engine,replay_from_s)` | Replay cached rows newer than this session time in seconds, up to replay_max_s. Requires a token and unfinished session; returns new replay token count. Does not reset the audio tower. |
| `a8_eot_probs(engine,out)` | Caller float array `[4][8]`; reads the last token's semantic-VAD class distribution. Enable semantic VAD and query after a token. |
| `a8_get_stats(engine,out)` | Fills caller-owned a8_stats, returns 0. |
| `a8_set_hotwords(engine,tokenizer_path,words_json,top_k,start_boost,continuation_boost)` | After reset, before audio: matching tokenizer file; JSON array of UTF-8 strings (`[]` disables); top_k 0 or1..vocabulary; finite boosts [0,100]. Returns 0. Limits:256 terms,1024 UTF-8 bytes/term,128 tokens/variant,65536 JSON bytes. Configuration survives reset; matching history clears. The bias is a preference, not a spelling guarantee. |

For optional hotwords the example accepts repeated `--hotword TERM` and `--tokenizer FILE`; it defaults to the
current package's `tokenizer.json`. `--realtime` paces 100ms input blocks; omit it for unpaced file processing.
Normal stdout is transcript UTF-8 bytes plus a newline. Diagnostics go to stderr. Exit status is 0 on success,
1 on an input/SDK error, or 128+signal (130 for SIGINT,143 for SIGTERM) after cooperative cleanup.

## Compatibility

One SDK0.6.1 binary passed Ubuntu22.04/24.04/26.04 arm64 userspace checks; existing actual NPU coverage is
QCS8550/Ubuntu22.04/160ms. That is not a claim of NPU/BSP validation on24.04/26.04 or every resource target.
Keep model, runtime and SDK versions matched; do not infer hardware compatibility from the folder name alone.

## SDK 0.7.0 request controls

These additive C ABI functions underpin the new Python task API. Existing C calls retain their signatures.

| Function | Parameters and result |
| --- | --- |
| `a8_begin_request(e, int lang, int64_t max_new_tokens)` | Start a fresh exclusive request. `lang` is `A8_LANG_ZH` or `A8_LANG_EN`. Restore the selected language prefix and clear audio/LM/token/history/progress state without reloading graphs. `0` cap means native continuous policy; positive cap counts emitted tokens including controls. Configure/clear hotwords separately after beginning. Returns status `0` or negative error. |
| `a8_request_state(e)` | Returns `0` running, `1` normal known-EOF/drained completion, `2` generation cap, or negative error. Copy the last error immediately on failure. |
| `a8_finish_audio(e, const float *pcm, int n, int tail_tokens)` | Append final finite model-rate mono PCM and declare EOF before running remaining work/tails. Same PCM/ownership contract as feed; `n>=0`, pointer required when `n>0`; `tail_tokens=-1` uses native default. Returns count of queued tokens or negative error. Drain with `a8_read_tokens`. Unlike feed followed by finish, this preserves normal completion when the cap equals the precise final workload. |

After a live `a8_feed` exhausts the cap, state is terminal `2`; do not call native finish again. A new request must begin/reset before more audio. A finite final-audio call returns state `1` if all required clocks finish exactly at the cap, or `2` if the cap blocks required work. No text slicing implements this budget. `a8_reset` restores the currently selected language and the original uncapped legacy session behavior. Language switching changes only existing prefix/cache state, not weights. All calls remain synchronous and must not race destroy. The Python layer additionally reserves one recording and caches its idempotent finish result; raw C finish is still once-only.
