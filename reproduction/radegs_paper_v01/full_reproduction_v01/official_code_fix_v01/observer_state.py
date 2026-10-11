"""Passive diagnostic status classifier. Never dispatches or counts training."""
def classify(status,live,verified_seal):
    if status=='ENGINEERING_NOT_READY':return status
    if status=='CUDA_REPLAY_DIAGNOSTIC_COMPLETE':
        return 'REPLAY_PASSED_OFFICIAL_NATIVE_GPU_VALIDATION_PENDING' if verified_seal else 'ENGINEERING_NOT_READY_UNVERIFIED_DIAGNOSTIC'
    if not live:return 'ENGINEERING_NOT_READY_DEAD_RUNNER'
    if status=='RUNNING':return 'BOUNDED_MEMCHECK_RUNNING'
    if status.startswith('WAITING_'):return 'WAITING_FOR_LOW_LOAD_GPU'
    return 'BOUNDED_MEMCHECK_PENDING_TERMINAL_VERIFICATION'
