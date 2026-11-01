#include "audio8_asr.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    if(argc!=3){fprintf(stderr,"Usage: %s PACKAGE CLOCK_MS\n",argv[0]);return 2;}
    a8_options model; a8_default_options(&model);model.clock_ms=atoi(argv[2]);
    pandora_runtime_config_t cfg=PANDORA_RUNTIME_CONFIG_INIT;
    cfg.qnn.performance_mode=PANDORA_QNN_BALANCED;cfg.qnn.priority=PANDORA_PRIORITY_HIGH;
    cfg.qnn_override_flags=PANDORA_QNN_OVERRIDE_RPC_CONTROL_LATENCY|PANDORA_QNN_OVERRIDE_RPC_POLLING_TIME;
    cfg.rpc_control_latency_us=0;cfg.rpc_polling_time_us=1000;
    pandora_runtime_t *r=NULL;a8_engine *e=NULL;int result=1;
    if(pandora_runtime_create(&cfg,&r)<0){fprintf(stderr,"%s\n",pandora_runtime_last_error());goto done;}
    if(a8_create_with_runtime(argv[1],&model,r,&e)<0){fprintf(stderr,"%s\n",a8_create_error());goto done;}
    pandora_runtime_capabilities_t cap={0};cap.struct_size=sizeof(cap);cap.abi_version=2;
    pandora_runtime_submission_status_t sub={0};sub.struct_size=sizeof(sub);sub.abi_version=2;
    if(pandora_runtime_get_capabilities(r,&cap)<0 || pandora_runtime_get_submission_status(r,&sub)<0)goto done;
    printf("contexts=%u supported_fields=%u submitted_fields=%u requested_priority=%d backend_profile=%u control_us=%u\n",sub.active_contexts,cap.supported_fields,sub.submitted_fields,cfg.qnn.priority,sub.backend_performance_mode,sub.backend_rpc_control_latency_us);
    /* Model feeds use the existing a8_feed/finish/read_tokens API. */
    result=0;
done:
    if(a8_destroy_owned(&e)<0)result=1;
    if(pandora_runtime_destroy(&r)<0)result=1;
    return result;
}
