# Pandora Runtime — Audio8 AidLite/QNN provider

SDK0.8.0 adds provider-local hardware configuration without changing the
approved 80ms/160ms graphs, quantization, models.json or separate package roots.
**AidLite still loads/decrypts and invokes every QNN2.48 graph.** This provider does
not use Cosy's direct-QNN loading or create a second inference engine.

## Python

```python
from audio8_asr import ASRModel, Runtime, QnnOptions

with Runtime(options=QnnOptions(performance_mode="balanced", priority="high",
             rpc_control_latency_us=0, rpc_polling_time_us=1000)) as runtime:
    print(runtime.status())  # No graph submitted yet.
    with ASRModel.from_pretrained("/path/to/audio8-80ms", runtime=runtime) as model:
        print(runtime.status())  # Four AidLite contexts.
        result = model.transcribe("speech.wav", language="en")
```

`Runtime(backend="qnn", options=None, memory_lock="off")` is immutable. Omitted
options use burst/normal with the AidLite Config control-latency default100us.
Omitting `runtime=` creates a model-owned default Runtime, closed with the model.
Caller-owned Runtime objects can be reused across model lifetimes; close all models
before Python Runtime.close(). Two loaded models were exercised on the tested board; this does not guarantee
unlimited instances (see resource limits below). C model owners retain the state if the caller's
Runtime handle is destroyed. Loading/closing a Runtime must be synchronized by the
caller; concurrent independent model execution is still arbitrated by AidLite/QNN.

The implementation is `audio8_asr.runtime`, re-exported at `audio8_asr`. It does not
install/overwrite Cosy's top-level pandora_runtime module. Native/Python objects
are provider-local: do not pass another SDK's Runtime into ASRModel or exchange
native handles. This is a uniform API shape, not a cross-SDK shared native ABI.

## Options and actual support

| Parameter | Values/default | This provider |
| --- | --- | --- |
| performance_mode | `burst` default; `sustained_high_performance`, `high_performance`, `balanced`, `low_balanced`, `high_power_saver`, `power_saver`, `low_power_saver`, `extreme_power_saver` | Assigned to each AidLite Config.performance_profile before init/load |
| performance_mode | `system_settings` | **Reserved, not forwarded**; AidLite's burst default remains |
| priority | `low` (0), `normal` (100, default), `normal_high` (150), `high` (200) | **Reserved, not forwarded**; actual backend priority is unknown |
| rpc_control_latency_us | None default100; integer0..4294967295 | Config.rpc_control_latency, microseconds; explicit0 preserved |
| rpc_polling_time_us | None default-unspecified; integer0..9999 | **Reserved, not forwarded**, including explicit0; backend polling unknown |
| memory_lock | `off` only | No SDK-owned decrypted-buffer locking; best_effort raises ValueError |

Enums are case-sensitive. Invalid names, negative/out-of-range values and bool/
non-integer RPC values raise ValueError/TypeError before native loading. Valid
reserved options succeed and retain their requested values under the owner's
chosen contract; they are not silently mapped to an applied priority or polling
value. `system_settings` may be combined with control-latency overrides: only the
supported control setting is sent, and the performance mode remains burst. This
is **not** Cosy's direct-QNN `system_settings` no-vote behavior. No llm_decode mode
is accepted. No automatic inference scheduler, cross-process queue or timer is added.

Defaults and accepted profile names come from AidLite2.5.0.284's installed Config
header. Actual hardware vote profiles/priority scheduling are vendor-owned; no
clock frequency, independent physical frequency or priority-preemption benefit
is inferred from a successful load. No backend-extension JSON is fabricated to
claim additional capabilities.

## Querying support and submission

`runtime.status()` returns a new dictionary:

- `requested`: immutable requested values (RPC None stays unspecified).
- `supported`: per-field booleans for the **selected** performance mode/other
  settings. Priority/polling/memory-lock are false. This describes the integration
  confirmed by this SDK, not every capability of all AidLite versions.
- `configured`: fields written into AidLite Config (performance is false for
  reserved system_settings; control is true). Priority/polling remain false.
- `submitted`: those supported fields with a successfully loaded attached graph;
  all false before load/after last graph closes.
- `backend_configuration`: actual Config profile/control submitted by this SDK;
  priority and polling are None. The fallback profile for system_settings is burst.
- `active_contexts`: currently attached graph count (four per complete model).
  `performance_mode`/`priority` at the top level are **requested configuration**,
  not physical measurements; use the explicit status fields above.

`configured` may remain true after close because immutable configuration still
exists; `submitted` becomes false. A failed later graph can leave temporary
partially loaded contexts during construction; constructor cleanup removes them.
RuntimeNativeError has `.code` and `.native_code`. Model errors retain a numeric
native_code when available. A model may not use a closed Runtime. Query/close
reject inherited Python Runtime objects after fork; use spawn/exec and initialize
independently. Do not assume that vendor state inherited via fork is reusable.

## C

Include both `audio8_asr.h` and `pandora_runtime.h`; link the same libaudio8_asr.so.
The [runnable C client](../examples/c/runtime_example.c) uses:

```c
pandora_runtime_config_t cfg = PANDORA_RUNTIME_CONFIG_INIT;
cfg.qnn.performance_mode = PANDORA_QNN_BALANCED;
cfg.qnn.priority = PANDORA_PRIORITY_HIGH; /* retained, not forwarded */
cfg.qnn_override_flags = PANDORA_QNN_OVERRIDE_RPC_CONTROL_LATENCY |
                         PANDORA_QNN_OVERRIDE_RPC_POLLING_TIME;
cfg.rpc_control_latency_us = 0;
cfg.rpc_polling_time_us = 1000; /* retained, not forwarded */
pandora_runtime_t *runtime = NULL;
int rc = pandora_runtime_create(&cfg, &runtime);
/* Check rc, then a8_create_with_runtime(package, &options, runtime, &engine). */
```

Mode constants: PANDORA_QNN_BURST, SUSTAINED_HIGH_PERFORMANCE, HIGH_PERFORMANCE,
BALANCED, LOW_BALANCED, HIGH_POWER_SAVER, POWER_SAVER, LOW_POWER_SAVER,
EXTREME_POWER_SAVER, SYSTEM_SETTINGS (each prefixed PANDORA_QNN_). Priorities:
PANDORA_PRIORITY_LOW/NORMAL/NORMAL_HIGH/HIGH. Numeric values match the header and
Python table. RPC bounds/units/reserved behavior are identical to Python.

Config ABI2 requires struct_size=sizeof(config), abi_version=2 and zero reserved
fields. Override bits distinguish omitted values from explicit0. Runtime queries
require their own sizeof and abi_version=2; bad sizes/versions fail without writing
a larger object. This first Audio8 Runtime does not promise Cosy's ABI1 prefix
compatibility; old Audio8 a8_options/a8_create/a8_destroy ABI remains intact.

- pandora_runtime_get_status: requested native config/context counts. AidLite owns
  power clients and votes: those SDK-owned counters stay zero; unobserved process
  polling/unspecified requested polling is UINT32_MAX, not a measured value.
- pandora_runtime_get_capabilities: provider=AIDLITE_QNN248, supported_fields bitmask,
  supported_performance_modes bits. Bits are (1u << PANDORA_QNN_<MODE>).
- pandora_runtime_get_submission_status: configured_fields/submitted_fields,
  active_contexts, backend_performance_mode and backend_rpc_control_latency_us.
  Field bits are PANDORA_FIELD_PERFORMANCE_MODE/PRIORITY/RPC_CONTROL_LATENCY/
  RPC_POLLING/MEMORY_LOCK. Only mode/control are supported; selected system_settings
  is not configured/submitted.

Runtime functions return0 or negative PANDORA_ERROR_ARGUMENT(-1), BACKEND(-3),
STATE(-4), INTERNAL(-5), with thread-local pandora_runtime_last_error(). Model
functions return A8_ERR_* and a8_create_error()/a8_last_error(); the two error
namespaces must not be mixed. Owned model creation writes a persistent output
slot before returning; a8_destroy_owned clears it and is idempotent for an empty
slot. The caller waits for in-flight calls before destruction.

## Host integration

The SDK does not redirect stdout/stderr, configure global AidLite logging, change
signal masks/handlers, dumpable state, core/memlock limits, or multiprocessing
start methods. Applications own these choices. Vendor license/RPC notices may
appear on their configured streams. AidLite owns the decrypted model buffers;
this SDK does not expose plaintext/address APIs, but does not establish dump
exclusion, zeroization or debugger resistance for opaque vendor-owned copies.
Memory locking remains unavailable in this provider.

Python native calls are synchronous. A Python signal handler may run only after a
vendor call returns; no immediate driver cancellation is promised. Model/Runtime
creation uses persistent output slots. A return-handoff interruption can clean the
recorded native owner; destroy clears its slot so explicit close can be retried
without double destruction. Applications must wait for in-flight work to finish
before closing; repeated hostile interruptions are not a cleanup guarantee.

Model, recording and Runtime objects are process-local. Python checks PID before
ownership locks. Every C model operation rejects inherited handles; checked owned
destroy preserves the slot on this error. Legacy void destroy refuses to free an
inherited handle and records a create error. The initialized AidLite provider must
not be reused or reinitialized in a fork child; use spawn or exec and initialize
there. Initialization by unrelated SDKs is not tracked by this provider.
The SDK never changes the application's multiprocessing start method.

C model options reject non-finite/negative roll_s or replay_max_s, stable_rows below
-1, semantic_vad outside0/1 and rounded rolling windows above480 clocks, before
model loading. The latter is38.4s at80ms /76.8s at160ms (rounded clock boundary).
Python stable_rows is restricted to int32. soft_reset requires a finite replay
start; invalid input is rejected before altering the session.

The Demo owns startup shutdown coordination because a shutdown signal can
interrupt this AidLite/QNN initialization path. The application temporarily blocks
SIGINT/SIGTERM while assigning Session ownership, then restores the main thread's
original mask; this is not installed SDK behavior. Integrators own their signal
policy and must wait for vendor calls before cleanup.

## Resource limits

Two loaded models and independent-process cleanup were tested on the qualified
board. This is not an unlimited-instance or all-duration memory guarantee.
Vendor calls remain synchronous; applications must coordinate shutdown and wait
for in-flight work before destruction. AidLite/QNN/BSP resources are external to
Python venv isolation. See the SDK compatibility guide for the tested platform.
