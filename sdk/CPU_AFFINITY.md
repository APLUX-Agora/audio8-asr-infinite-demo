# CPU affinity — Python and C

Both 80ms and 160ms use the same interface and native core. AidLite still loads,
decrypts and invokes QNN graphs. CPU placement is separate from QNN performance
and priority; it neither reserves cores nor changes the QNN scheduler.

## Python

```python
from audio8_asr import ASRModel, Runtime, CpuOptions, QnnOptions

with Runtime(cpu=CpuOptions(affinity=[3, 4]),
             options=QnnOptions(performance_mode="burst")) as runtime:
    with ASRModel.from_pretrained("models/audio8-80ms", clock_ms=80,
                                  runtime=runtime) as model:
        result = model.transcribe("speech.wav", language="en")
        print(result.text)
        print(runtime.status()["cpu"])
```

Use the independent 160ms model root and `clock_ms=160` for 160ms. CPU IDs in this
example must be available to your application; they are not universal defaults.

| affinity | Meaning |
| --- | --- |
| `"inherit"` | SDK default, including omitted runtime/cpu. The model worker inherits the Runtime-creating thread's allowed placement; the application thread is not rebound. |
| `"default"` | Versioned platform profile intersected with the creator's online allowed CPUs. Official Web and file examples explicitly choose this. |
| Nonempty iterable of integer CPU IDs | Explicit placement, copied and sorted/deduplicated. Booleans, floats, bytes, mappings and negative/non-uint32 IDs are rejected. At most 1024 input IDs; actual Linux IDs must be below CPU_SETSIZE (1024 in this build), online and allowed. |

`CpuOptions` is immutable and copies iterables. `Runtime.cpu` is read-only. Native
Runtime creation happens on first model binding, when online/allowed CPUs are
validated. A thread that subsequently creates a model must allow the resolved
set too: the worker cannot widen inherited host restrictions. Use independent
Runtime objects for different settings. Models retain native state; close all
models before Python Runtime.close(). Do not pass this provider's Runtime or
opaque handles to another SDK, or reuse them after fork; initialize after spawn/exec.

The first qualified `default` profile is `qcs_kalamap-model-high-capacity-v1`:
Linux soc603, heterogeneous `cpuinfo_max_freq`, selects CPUs faster than the
lowest frequency class. On the qualified Linux image this resolves to 3,4,5. No fixed
mask is applied on other/unknown topologies: unavailable profiles or an empty
allowed intersection fail with an actionable native error. Choose `inherit` or
an explicit set on those systems; other platforms have not been board-qualified
for this profile. All masks respect the creating thread's allowed set/cpuset.

The model owns one native execution thread for creation, graph loading, frontend,
LM/decoder, token/KV operations and destruction. AidLite-created compute workers
inherit from that execution thread. Existing application/vendor service threads
are not traversed or rebound. Python resampling, boundary decoding and user
callbacks retain their application threading behavior. There is no global
OpenMP/Eigen setting, process-wide affinity change, or cross-process queue.
Model calls remain synchronous. Wait for in-flight calls before closing.
Cleanup runs on the owner even after an affinity/inference error, without
allocating a new task to destroy the engine. A changed mask causes a state error;
the SDK does not silently repair it by expanding application permissions.

### Status

`runtime.status()["cpu"]` contains `requested_affinity`, `allowed_cpu_ids`,
`resolved_cpu_ids`, `default_cpu_ids`, `default_profile`, `supported_policies`,
`active_workers`, `affinity_failures`, and `threads`. Each recorded model worker
contains a live kernel TID, `observed_cpu_ids`, and `verified`. Binding states are
`unbound`, `idle`, `inherited`, `verified`, or `mismatch`; verified means the
recorded live worker's kernel mask matches, not measured performance or proof of
all opaque vendor helper activity. `aidlite_threads` describes the inheritance
adaptation method, not individual helper observations. `backend_override_supported` describes the SDK adapter, not a public AidLite
CPU-mask API. Backend helper inheritance
and lifecycle coverage are checked separately with private qualification probes.

Queries are snapshots. Serialize model create/close with thread-index queries;
records disappear on close, and no exited TID is reported as verified. No models
means idle, not successful inference. An affinity mismatch is observable even
for inherit. Status before native binding has no resolved mask.

## C (C99/C++)

```c
#include "audio8_asr.h"

pandora_runtime_config_t cfg = PANDORA_RUNTIME_CONFIG_INIT;
uint32_t ids[] = {3, 4};
cfg.cpu.policy = PANDORA_CPU_AFFINITY_EXPLICIT;
cfg.cpu.cpu_ids = ids;
cfg.cpu.cpu_count = 2;
pandora_runtime_t *runtime = NULL;
int rc = pandora_runtime_create(&cfg, &runtime);
/* Check rc; ids can now be modified or released. */
a8_options options; a8_default_options(&options);
options.clock_ms = 80; /* 160 with the independent 160ms root */
a8_engine *engine = NULL;
/* rc = a8_create_with_runtime(package_root, &options, runtime, &engine); */
/* Feed/read/finish as usual; wait for calls before a8_destroy_owned(&engine). */
/* pandora_runtime_destroy(&runtime); */
```

Policies: `PANDORA_CPU_AFFINITY_INHERIT=0`, `DEFAULT=1`, `EXPLICIT=2`.
`PANDORA_CPU_OPTIONS_INIT` initializes size, CPU ABI1, inherit and zero reserved
fields. Use NULL/zero IDs for inherit/default; explicit requires a nonnull array
and nonzero count. The native Runtime copies it. Config ABI3 is append-only over
the exact ABI2/48-byte prefix; old ABI2 callers retain inherit. New config is
80 bytes on Linux AArch64. Legacy Runtime queries accept ABI2/3 with unchanged
sizes. CPU queries use independent CPU ABI1. Arbitrary sizes/versions fail before
reading an unsupported tail. Always use the matching public header/library.

- `pandora_runtime_get_cpu_status`: CPU policy, profile/support bits, controlled
  worker/observed/verified counts and cumulative affinity failures. Initialize
  `struct_size=sizeof(status)` and `abi_version=PANDORA_CPU_ABI_VERSION`.
- `pandora_runtime_get_cpu_ids`: kinds `PANDORA_CPU_IDS_ALLOWED` (0), `RESOLVED`
  (1), `DEFAULT` (2). Pass NULL and count=0 to obtain the count; then allocate and
  query again. Insufficient capacity returns ARGUMENT, updates required count,
  and writes no elements.
- `pandora_runtime_get_cpu_thread`: index of an active recorded worker, separate
  CPU ABI1 struct plus count/array convention above; `scope=MODEL`, TID, CPU count
  and fresh `verified` flag. Synchronize lifecycle across the two queries.

Runtime errors use `PANDORA_ERROR_*` and thread-local
`pandora_runtime_last_error()`. Model errors use `A8_ERR_*` and
`a8_create_error()/a8_last_error()`: numeric state codes differ. Invalid or
unavailable CPU configuration returns ARGUMENT; lost/mismatched worker placement
returns STATE. Opaque raw model BIN/pointer APIs are not introduced. Native model
owners retain Runtime state if a C caller releases its handle; Python requires
models to close first. Independent models/processes have their own workers;
QNN/AidLite continues to arbitrate NPU work.

## Demo and file commands

SDK default is inherit; official Web/file examples default to default. Override:

```bash
.venv/bin/python examples/python/transcribe_file.py speech.wav --models models/audio8-80ms --clock-ms 80 --cpu-affinity 3,4
.venv/bin/python examples/python/transcribe_file.py speech.wav --models models/audio8-160ms --clock-ms 160 --cpu-affinity inherit
./demo/run.sh --models models/audio8-80ms --cpu-affinity default
./demo/run.sh --models models/audio8-160ms --cpu-affinity 3,4
```

The existing `A8_CLOCK_MS=80/160` Web setting and independent model downloads
remain unchanged. Reload and model switching preserve the selected CPU policy.
[Runtime reference](RUNTIME.md) documents every performance/priority/RPC value;
reserved AidLite settings remain reserved in this release, without false claims
that they are submitted to QNN.
