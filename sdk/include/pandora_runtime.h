/* Pandora runtime configuration ABI v3 (legacy ABI2 accepted). This provider is delivered by libaudio8_asr via AidLite/QNN2.48.
 * Handles are process-local and provider-local. Never pass a handle to another SDK provider.
 * Models retain the runtime; destroying the caller handle does not invalidate attached models.
 * No model handle may be inherited through fork. Defaults: QNN / burst / normal / memory lock off. */
#ifndef PANDORA_RUNTIME_H
#define PANDORA_RUNTIME_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#if defined(_WIN32)
#define PANDORA_API __declspec(dllexport)
#else
#define PANDORA_API __attribute__((visibility("default")))
#endif
typedef struct pandora_runtime pandora_runtime_t;
enum { PANDORA_OK = 0, PANDORA_ERROR_ARGUMENT = -1, PANDORA_ERROR_BACKEND = -3,
       PANDORA_ERROR_STATE = -4, PANDORA_ERROR_INTERNAL = -5 };
enum { PANDORA_BACKEND_QNN = 1 };
/* Existing candidate values remain stable. These are profile IDs, not voltage values. */
enum { PANDORA_QNN_BURST = 0, PANDORA_QNN_BALANCED = 1, PANDORA_QNN_SYSTEM_SETTINGS = 2,
       PANDORA_QNN_SUSTAINED_HIGH_PERFORMANCE = 3, PANDORA_QNN_HIGH_PERFORMANCE = 4,
       PANDORA_QNN_LOW_BALANCED = 5, PANDORA_QNN_HIGH_POWER_SAVER = 6,
       PANDORA_QNN_POWER_SAVER = 7, PANDORA_QNN_LOW_POWER_SAVER = 8,
       PANDORA_QNN_EXTREME_POWER_SAVER = 9 };
enum { PANDORA_PRIORITY_LOW = 0, PANDORA_PRIORITY_NORMAL = 100,
       PANDORA_PRIORITY_NORMAL_HIGH = 150, PANDORA_PRIORITY_HIGH = 200 };
enum { PANDORA_MEMORY_LOCK_OFF = 0, PANDORA_MEMORY_LOCK_BEST_EFFORT = 1 };
typedef struct { uint32_t performance_mode; int32_t priority; uint32_t reserved[2]; } pandora_qnn_options_t;
#define PANDORA_RUNTIME_ABI_VERSION 3
#define PANDORA_CPU_ABI_VERSION 1
enum { PANDORA_CPU_AFFINITY_INHERIT=0, PANDORA_CPU_AFFINITY_DEFAULT=1, PANDORA_CPU_AFFINITY_EXPLICIT=2 };
typedef struct {
    uint32_t struct_size, abi_version, policy, cpu_count;
    const uint32_t *cpu_ids;
    uint32_t reserved[2];
} pandora_cpu_options_t;
#define PANDORA_CPU_OPTIONS_INIT {sizeof(pandora_cpu_options_t), PANDORA_CPU_ABI_VERSION, PANDORA_CPU_AFFINITY_INHERIT, 0, 0, {0,0}}

enum { PANDORA_QNN_OVERRIDE_RPC_CONTROL_LATENCY = 1, PANDORA_QNN_OVERRIDE_RPC_POLLING_TIME = 2 };
typedef struct {
    uint32_t struct_size, abi_version, backend, memory_lock;
    pandora_qnn_options_t qnn;
    /* ABI v2 append-only overrides. Flags distinguish explicit zero from preset defaults. */
    uint32_t qnn_override_flags, rpc_control_latency_us, rpc_polling_time_us, reserved;
    pandora_cpu_options_t cpu;
} pandora_runtime_config_t;
#define PANDORA_RUNTIME_CONFIG_INIT {sizeof(pandora_runtime_config_t), PANDORA_RUNTIME_ABI_VERSION, PANDORA_BACKEND_QNN, PANDORA_MEMORY_LOCK_OFF, {PANDORA_QNN_BURST, PANDORA_PRIORITY_NORMAL, {0, 0}}, 0, 0, 0, 0, PANDORA_CPU_OPTIONS_INIT}
typedef struct {
    uint32_t struct_size, abi_version, performance_mode;
    int32_t priority;
    uint32_t memory_lock, active_contexts, power_client_created, active_executions;
    uint64_t accepted_active_votes, accepted_release_votes;
    uint32_t rpc_control_latency_us, rpc_polling_time_us, process_rpc_polling_time_us, deferred_vote_failures;
} pandora_runtime_status_t;
/* Config ABI2/48 or ABI3/80 bytes and status ABI2/3/64 bytes are accepted by this
 * Audio8 provider. Handles cannot be exchanged with another provider. Status
 * mode/priority/overrides describe requested native configuration, not hardware
 * measurements. AidLite owns votes, so vote counters/power_client_created stay
 * zero and unknown polling is UINT32_MAX. Inspect capabilities/submission before
 * interpreting a reserved option as submitted. Only memory_lock=OFF is accepted.
 * The caller must serialize model creation/close with runtime destruction. */
PANDORA_API const char *pandora_runtime_last_error(void);
PANDORA_API int pandora_runtime_create(const pandora_runtime_config_t *, pandora_runtime_t **out);
PANDORA_API int pandora_runtime_get_status(pandora_runtime_t *, pandora_runtime_status_t *);
PANDORA_API int pandora_runtime_destroy(pandora_runtime_t **);
enum { PANDORA_FIELD_PERFORMANCE_MODE = 1, PANDORA_FIELD_PRIORITY = 2,
       PANDORA_FIELD_RPC_CONTROL_LATENCY = 4, PANDORA_FIELD_RPC_POLLING = 8,
       PANDORA_FIELD_MEMORY_LOCK = 16 };
enum { PANDORA_PROVIDER_AIDLITE_QNN248 = 1 };
typedef struct {
    uint32_t struct_size, abi_version, provider, supported_fields;
    uint32_t supported_performance_modes, reserved[3];
} pandora_runtime_capabilities_t;
typedef struct {
    uint32_t struct_size, abi_version, configured_fields, submitted_fields;
    uint32_t active_contexts, backend_performance_mode, backend_rpc_control_latency_us, reserved;
} pandora_runtime_submission_status_t;
/* Capabilities describe this SDK's confirmed integration, not every possible
 * AidLite extension. Priority, polling, and system_settings are validated and
 * retained but NOT forwarded in this version. An unavailable mode leaves
 * AidLite's burst default. Control latency remains configurable, including 0.
 * submitted_fields means attached Interpreter::load_model accepted the config;
 * it does not prove physical clocks or vendor-internal vote/scheduling state.
 * backend_* reports the Config actually supplied to AidLite. */
PANDORA_API int pandora_runtime_get_capabilities(pandora_runtime_t *, pandora_runtime_capabilities_t *);
PANDORA_API int pandora_runtime_get_submission_status(pandora_runtime_t *, pandora_runtime_submission_status_t *);
/* CPU options are copied during create; callers may release the input array.
 * Runtime ABI2/48-byte configs remain accepted as CPU inherit. ABI3 config is
 * 80 bytes on Linux AArch64. Existing queries accept ABI2 or ABI3, same sizes.
 * Affinity covers the model execution worker: model init/load/invoke/release
 * run there and backend workers inherit its mask. Existing process-global and
 * unrelated application threads are not rebound. No QNN scheduler is added.
 * DEFAULT uses the versioned QCS_KALAMAP/soc603 high-capacity model profile;
 * other unknown profiles are unsupported. EXPLICIT must be a nonempty subset
 * of online CPUs and the creating thread's affinity. No automatic widening.
 * Known controlled work is applied to a model-private execution worker;
 * INHERIT leaves the application threads affinity untouched. */
enum { PANDORA_CPU_IDS_ALLOWED=0, PANDORA_CPU_IDS_RESOLVED=1, PANDORA_CPU_IDS_DEFAULT=2 };
enum { PANDORA_CPU_COVERAGE_MODEL_EXECUTION=2 };
enum { PANDORA_CPU_THREAD_MODEL=3 };
enum { PANDORA_CPU_PROFILE_NONE=0, PANDORA_CPU_PROFILE_KALAMAP_MODEL_V1=1 };
typedef struct {
    uint32_t struct_size, abi_version, policy, coverage;
    uint32_t supported_policies, backend_override_supported, active_workers, observed_threads;
    uint32_t verified_threads, profile_id, reserved[2];
    uint64_t affinity_failures;
} pandora_cpu_status_t;
typedef struct {
    uint32_t struct_size, abi_version;
    uint64_t tid;
    uint32_t scope, cpu_count, verified, reserved;
} pandora_cpu_thread_status_t;
/* CPU query structs use PANDORA_CPU_ABI_VERSION. Array queries accept NULL
 * with *count=0 to report required size. Insufficient capacity updates *count,
 * writes no array elements and returns ARGUMENT. Query each thread by index
 * only while model lifecycles are quiescent; records disappear on model close.
 * Observed masks are freshly read from the kernel, not config echoes. */
PANDORA_API int pandora_runtime_get_cpu_status(pandora_runtime_t *, pandora_cpu_status_t *);
PANDORA_API int pandora_runtime_get_cpu_ids(pandora_runtime_t *, uint32_t kind, uint32_t *ids, uint32_t *count);
PANDORA_API int pandora_runtime_get_cpu_thread(pandora_runtime_t *, uint32_t index, pandora_cpu_thread_status_t *, uint32_t *ids, uint32_t *count);
#ifdef __cplusplus
}
#endif
#endif
