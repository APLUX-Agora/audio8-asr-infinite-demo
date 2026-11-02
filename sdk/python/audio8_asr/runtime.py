"""Audio8 provider-local Pandora Runtime; QNN execution remains inside AidLite.

The public shape matches Pandora Runtime/QnnOptions; opaque native handles and
Python implementations remain provider-local, not a cross-SDK shared ABI.
"""
import ctypes as C
from dataclasses import dataclass
import os
from itertools import islice
from collections.abc import Iterable

_MODES = {"burst": 0, "sustained_high_performance": 3, "high_performance": 4,
          "balanced": 1, "low_balanced": 5, "high_power_saver": 6,
          "power_saver": 7, "low_power_saver": 8, "extreme_power_saver": 9,
          "system_settings": 2}
_PRIORITIES = {"low": 0, "normal": 100, "normal_high": 150, "high": 200}
_LOCKS = {"off": 0, "best_effort": 1}

@dataclass(frozen=True)
class QnnOptions:
    performance_mode: str = "burst"
    priority: str = "normal"
    rpc_control_latency_us: int | None = None
    rpc_polling_time_us: int | None = None
    def __post_init__(self):
        for name, choices in (("performance_mode", _MODES), ("priority", _PRIORITIES)):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(name + " must be a string")
            if value not in choices: raise ValueError(name + " must be one of: " + ", ".join(choices))
        for name, limit in (("rpc_control_latency_us", 2**32-1), ("rpc_polling_time_us", 9999)):
            value = getattr(self, name)
            if value is not None:
                if type(value) is not int: raise TypeError(name + " must be an integer or None")
                if not 0 <= value <= limit: raise ValueError(name + " is outside the supported range")

@dataclass(frozen=True)
class CpuOptions:
    """Model execution affinity: inherit, default, or an immutable CPU ID collection.

    This provider binds model execution and backend-created workers by inheritance.
    CPU sets constrain placement; they do not reserve cores or change NPU priority.
    """
    affinity: str | Iterable[int] = "inherit"

    def __post_init__(self):
        value = self.affinity
        if isinstance(value, str):
            if value not in ("inherit", "default"):
                raise ValueError("affinity must be 'inherit', 'default', or a CPU ID collection")
        else:
            if isinstance(value, (bytes, bytearray, dict)) or not isinstance(value, Iterable):
                raise TypeError("affinity must be a policy string or CPU ID collection")
            values = tuple(islice(iter(value), 1025))
            if not values or len(values) > 1024:
                raise ValueError("explicit affinity needs 1..1024 CPU IDs")
            if any(type(cpu) is not int for cpu in values):
                raise TypeError("CPU IDs must be integers, not bool/float")
            if any(cpu < 0 or cpu > 2**32-1 for cpu in values):
                raise ValueError("CPU IDs must be nonnegative uint32 values")
            object.__setattr__(self, "affinity", tuple(sorted(set(values))))

class _Cpu(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("abi_version", C.c_uint32),
                ("policy", C.c_uint32), ("cpu_count", C.c_uint32),
                ("cpu_ids", C.POINTER(C.c_uint32)), ("reserved", C.c_uint32 * 2)]
class _CpuStatus(C.Structure):
    _fields_ = [(key,C.c_uint32) for key in ("struct_size","abi_version","policy","coverage",
        "supported_policies","backend_override_supported","active_workers","observed_threads",
        "verified_threads","profile_id")] + [("reserved",C.c_uint32*2),("affinity_failures",C.c_uint64)]
class _CpuThread(C.Structure):
    _fields_ = [("struct_size",C.c_uint32),("abi_version",C.c_uint32),("tid",C.c_uint64),
                ("scope",C.c_uint32),("cpu_count",C.c_uint32),("verified",C.c_uint32),("reserved",C.c_uint32)]

class _Qnn(C.Structure):
    _fields_ = [("mode", C.c_uint32), ("priority", C.c_int32), ("reserved", C.c_uint32 * 2)]
class _Config(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("abi_version", C.c_uint32),
                ("backend", C.c_uint32), ("memory_lock", C.c_uint32), ("qnn", _Qnn), ("override_flags", C.c_uint32),
                ("rpc_control_latency_us", C.c_uint32), ("rpc_polling_time_us", C.c_uint32), ("reserved", C.c_uint32), ("cpu", _Cpu)]
class _Status(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("abi_version", C.c_uint32),
                ("performance_mode", C.c_uint32), ("priority", C.c_int32),
                ("memory_lock", C.c_uint32), ("active_contexts", C.c_uint32),
                ("power_client_created", C.c_uint32), ("active_executions", C.c_uint32),
                ("accepted_active_votes", C.c_uint64), ("accepted_release_votes", C.c_uint64),
                ("rpc_control_latency_us", C.c_uint32), ("rpc_polling_time_us", C.c_uint32),
                ("process_rpc_polling_time_us", C.c_uint32), ("deferred_vote_failures", C.c_uint32)]

class RuntimeNativeError(RuntimeError):
    """Native provider failure with a machine-readable SDK error code."""
    def __init__(self, code, message):
        super().__init__(message + " (code " + str(code) + ")")
        self.code = self.native_code = code


class _Capabilities(C.Structure):
    _fields_ = [(k,C.c_uint32) for k in ("struct_size","abi_version","provider","supported_fields","supported_performance_modes")] + [("reserved",C.c_uint32*3)]
class _Submission(C.Structure):
    _fields_ = [(k,C.c_uint32) for k in ("struct_size","abi_version","configured_fields","submitted_fields","active_contexts","backend_performance_mode","backend_rpc_control_latency_us","reserved")]
_FIELDS={"performance_mode":1,"priority":2,"rpc_control_latency_us":4,"rpc_polling_time_us":8,"memory_lock":16}

def _mode(value): return next(k for k,v in _MODES.items() if v==value)
def _priority(value): return next(k for k,v in _PRIORITIES.items() if v==value)

class Runtime:
    """Immutable provider-local hardware configuration. Bind through ASRModel.

    Unsupported but reserved performance/priority/polling settings are validated
    and retained; query status() to distinguish requested and submitted values.
    Model load/invoke/release use a private execution worker. No NPU scheduler,
    own power votes or model decryption is added.
    """
    def __init__(self, *, backend="qnn", options=None, memory_lock="off", cpu=None):
        if backend!="qnn":raise ValueError("This provider uses AidLite's qnn backend")
        if options is None:options=QnnOptions()
        if not isinstance(options,QnnOptions):raise TypeError("options must be audio8_asr.QnnOptions")
        if memory_lock!="off":raise ValueError("Only memory_lock='off' is available; AidLite owns model buffers")
        if cpu is None:cpu=CpuOptions()
        if not isinstance(cpu,CpuOptions):raise TypeError("cpu must be audio8_asr.CpuOptions")
        self._cpu=cpu
        self._options,self._memory_lock=options,memory_lock
        self._pid=os.getpid();self._slot=C.c_void_p();self._lib=None;self._closed=False
    @property
    def cpu(self):return self._cpu
    @property
    def options(self):return self._options
    @property
    def memory_lock(self):return self._memory_lock
    def _check_process(self):
        if os.getpid()!=self._pid:raise RuntimeError("Runtime inherited through fork; initialize after spawn/exec")
    def _check(self):
        self._check_process()
        if self._closed:raise RuntimeError("Runtime is closed")
    def _error(self,rc):
        if rc<0:raise RuntimeNativeError(rc,self._lib.pandora_runtime_last_error().decode(errors="replace"))
    def _bind(self,lib):
        self._check()
        if self._lib is not None and self._lib._handle!=lib._handle:raise RuntimeError("Runtime cannot bind another provider library")
        if not self._slot.value:
            self._lib=lib
            signatures={"pandora_runtime_create":([C.POINTER(_Config),C.POINTER(C.c_void_p)],C.c_int),
             "pandora_runtime_get_status":([C.c_void_p,C.POINTER(_Status)],C.c_int),
             "pandora_runtime_get_capabilities":([C.c_void_p,C.POINTER(_Capabilities)],C.c_int),
             "pandora_runtime_get_submission_status":([C.c_void_p,C.POINTER(_Submission)],C.c_int),
             "pandora_runtime_destroy":([C.POINTER(C.c_void_p)],C.c_int),
             "pandora_runtime_last_error":([],C.c_char_p),
             "pandora_runtime_get_cpu_status":([C.c_void_p,C.POINTER(_CpuStatus)],C.c_int),
             "pandora_runtime_get_cpu_ids":([C.c_void_p,C.c_uint32,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)],C.c_int),
             "pandora_runtime_get_cpu_thread":([C.c_void_p,C.c_uint32,C.POINTER(_CpuThread),C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)],C.c_int)}
            for name,(args,res) in signatures.items():f=getattr(lib,name);f.argtypes=args;f.restype=res
            c=_Config(C.sizeof(_Config),3,1,0,_Qnn(_MODES[self.options.performance_mode],_PRIORITIES[self.options.priority],(C.c_uint32*2)()))
            for name,flag in (("rpc_control_latency_us",1),("rpc_polling_time_us",2)):
                value=getattr(self.options,name)
                if value is not None:c.override_flags|=flag;setattr(c,name,value)
            affinity=self.cpu.affinity
            cpu_ids=None if isinstance(affinity,str) else (C.c_uint32*len(affinity))(*affinity)
            c.cpu=_Cpu(C.sizeof(_Cpu),1,0 if affinity=="inherit" else 1 if affinity=="default" else 2,
                       0 if cpu_ids is None else len(cpu_ids),cpu_ids)
            try:self._error(lib.pandora_runtime_create(C.byref(c),C.byref(self._slot)))
            except BaseException:
                if self._slot.value:lib.pandora_runtime_destroy(C.byref(self._slot))
                raise
        return self._slot.value
    def status(self):
        self._check();o=self.options
        requested={"performance_mode":o.performance_mode,"priority":o.priority,"rpc_control_latency_us":o.rpc_control_latency_us,"rpc_polling_time_us":o.rpc_polling_time_us,"memory_lock":self.memory_lock}
        supported={k:k in ("performance_mode","rpc_control_latency_us") for k in _FIELDS}
        supported["performance_mode"]=o.performance_mode!="system_settings"
        configured={k:supported[k] for k in _FIELDS};submitted={k:False for k in _FIELDS}
        backend_mode=o.performance_mode if supported['performance_mode'] else "burst";control=100 if o.rpc_control_latency_us is None else o.rpc_control_latency_us
        result={"backend":"qnn","provider":"aidlite_qnn248","performance_mode":o.performance_mode,"priority":o.priority,"memory_lock":self.memory_lock,"active_contexts":0,"active_executions":0}
        if self._slot.value:
            s=_Status();s.struct_size,s.abi_version=C.sizeof(s),3
            caps=_Capabilities();caps.struct_size,caps.abi_version=C.sizeof(caps),3
            sub=_Submission();sub.struct_size,sub.abi_version=C.sizeof(sub),3
            self._error(self._lib.pandora_runtime_get_status(self._slot,C.byref(s)))
            self._error(self._lib.pandora_runtime_get_capabilities(self._slot,C.byref(caps)))
            self._error(self._lib.pandora_runtime_get_submission_status(self._slot,C.byref(sub)))
            requested.update(performance_mode=_mode(s.performance_mode),priority=_priority(s.priority))
            result.update(performance_mode=requested['performance_mode'],priority=requested['priority'],active_contexts=s.active_contexts,active_executions=s.active_executions)
            supported={k:bool(caps.supported_fields&flag) for k,flag in _FIELDS.items()}
            supported['performance_mode']=bool(caps.supported_performance_modes&(1<<s.performance_mode))
            configured={k:bool(sub.configured_fields&flag) for k,flag in _FIELDS.items()}
            submitted={k:bool(sub.submitted_fields&flag) for k,flag in _FIELDS.items()}
            backend_mode,control=_mode(sub.backend_performance_mode),sub.backend_rpc_control_latency_us
        result.update(requested=requested,supported=supported,configured=configured,submitted=submitted,
          backend_configuration={"performance_mode":backend_mode,"rpc_control_latency_us":control,"priority":None,"rpc_polling_time_us":None},
          process_rpc_polling_time_us=None, cpu=self._cpu_status())
        return result
    def _cpu_status(self):
        request=self.cpu.affinity
        value={"requested_affinity":request if isinstance(request,str) else list(request),
               "scope":"model_execution", "coverage":"model_owned_threads", "backend_override_supported":True,
               "aidlite_threads":"inherit_from_model_worker", "preexisting_process_threads":"unchanged", "binding_state":"unbound", "allowed_cpu_ids":None,
               "resolved_cpu_ids":None,"default_cpu_ids":None,"default_profile":None,
               "active_workers":0,"threads":[],"affinity_failures":0}
        if not self._slot.value:return value
        meta=_CpuStatus();meta.struct_size,meta.abi_version=C.sizeof(meta),1
        self._error(self._lib.pandora_runtime_get_cpu_status(self._slot,C.byref(meta)))
        def ids(kind):
            count=C.c_uint32(0);self._error(self._lib.pandora_runtime_get_cpu_ids(self._slot,kind,None,C.byref(count)))
            if not count.value:return []
            array=(C.c_uint32*count.value)();self._error(self._lib.pandora_runtime_get_cpu_ids(self._slot,kind,array,C.byref(count)))
            return list(array)[:count.value]
        threads=[]
        for index in range(meta.observed_threads):
            row=_CpuThread();row.struct_size,row.abi_version=C.sizeof(row),1
            count=C.c_uint32(0)
            self._error(self._lib.pandora_runtime_get_cpu_thread(self._slot,index,C.byref(row),None,C.byref(count)))
            array=(C.c_uint32*count.value)()
            self._error(self._lib.pandora_runtime_get_cpu_thread(self._slot,index,C.byref(row),array,C.byref(count)))
            threads.append({"tid":row.tid,"scope":"model_primary" if row.scope==3 else "head_primary" if row.scope==1 else "model_openmp",
                            "observed_cpu_ids":list(array)[:count.value],"verified":bool(row.verified)})
        value.update(allowed_cpu_ids=ids(0),resolved_cpu_ids=ids(1),default_cpu_ids=ids(2),
                     default_profile="qcs_kalamap-model-high-capacity-v1" if meta.profile_id==1 else None,
                     supported_policies=[name for i,name in enumerate(("inherit","default","explicit")) if meta.supported_policies&(1<<i)],
                     active_workers=meta.active_workers,threads=threads,affinity_failures=meta.affinity_failures,
                     binding_state="mismatch" if meta.observed_threads and meta.verified_threads!=meta.observed_threads else "inherited" if request=="inherit" and meta.observed_threads else "verified" if meta.observed_threads else "idle")
        return value

    def close(self):
        self._check_process()
        if self._closed:return
        if self._slot.value:
            if self.status()['active_contexts']:raise RuntimeError("Runtime still has attached model contexts; close models first")
            self._error(self._lib.pandora_runtime_destroy(C.byref(self._slot)))
        self._closed=True
    def __enter__(self):self._check();return self
    def __exit__(self,*_):self.close()
    def __del__(self):
        try:self.close()
        except BaseException:pass
