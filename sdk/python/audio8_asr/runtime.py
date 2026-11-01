"""Audio8 provider-local Pandora Runtime; QNN execution remains inside AidLite.

The public shape matches Pandora Runtime/QnnOptions; opaque native handles and
Python implementations remain provider-local, not a cross-SDK shared ABI.
"""
import ctypes as C
from dataclasses import dataclass
import os

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

class _Qnn(C.Structure):
    _fields_ = [("mode", C.c_uint32), ("priority", C.c_int32), ("reserved", C.c_uint32 * 2)]
class _Config(C.Structure):
    _fields_ = [("struct_size", C.c_uint32), ("abi_version", C.c_uint32),
                ("backend", C.c_uint32), ("memory_lock", C.c_uint32), ("qnn", _Qnn), ("override_flags", C.c_uint32),
                ("rpc_control_latency_us", C.c_uint32), ("rpc_polling_time_us", C.c_uint32), ("reserved", C.c_uint32)]
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
    No device scheduling, worker, own power votes or model decryption is added.
    """
    def __init__(self, *, backend="qnn", options=None, memory_lock="off"):
        if backend!="qnn":raise ValueError("This provider uses AidLite's qnn backend")
        if options is None:options=QnnOptions()
        if not isinstance(options,QnnOptions):raise TypeError("options must be audio8_asr.QnnOptions")
        if memory_lock!="off":raise ValueError("Only memory_lock='off' is available; AidLite owns model buffers")
        self._options,self._memory_lock=options,memory_lock
        self._pid=os.getpid();self._slot=C.c_void_p();self._lib=None;self._closed=False
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
             "pandora_runtime_last_error":([],C.c_char_p)}
            for name,(args,res) in signatures.items():f=getattr(lib,name);f.argtypes=args;f.restype=res
            c=_Config(C.sizeof(_Config),2,1,0,_Qnn(_MODES[self.options.performance_mode],_PRIORITIES[self.options.priority],(C.c_uint32*2)()))
            for name,flag in (("rpc_control_latency_us",1),("rpc_polling_time_us",2)):
                value=getattr(self.options,name)
                if value is not None:c.override_flags|=flag;setattr(c,name,value)
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
            s=_Status();s.struct_size,s.abi_version=C.sizeof(s),2
            caps=_Capabilities();caps.struct_size,caps.abi_version=C.sizeof(caps),2
            sub=_Submission();sub.struct_size,sub.abi_version=C.sizeof(sub),2
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
          process_rpc_polling_time_us=None)
        return result
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
