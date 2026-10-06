"""Fixed CUDA-event/wall benchmark; CPU copies and kernel profiling are separate."""
import gc
import json
import time
import numpy as np
import torch
from runtime import EXP, guard

PROTOCOL = json.loads((EXP / 'protocol.json').read_text())

def summarize_ms(values):
    a = np.asarray(values, dtype=np.float64)
    median, p95 = float(np.median(a)), float(np.percentile(a, 95))
    fps = 1000 / a
    return dict(repeats=len(values), median_ms=median, p95_ms=p95,
                median_fps=float(np.median(fps)), p95_fps=float(np.percentile(fps, 95)),
                p05_fps=float(np.percentile(fps, 5)), samples_ms=a.tolist())

def run_benchmark(fn, label, attribution=False, profile_kernels=True):
    guard('benchmark_' + label)
    warmup, repeats = PROTOCOL['benchmark_warmup'], PROTOCOL['benchmark_repeats']
    for _ in range(warmup):
        value = fn(); torch.cuda.synchronize(); del value
    gc.collect(); torch.cuda.synchronize()
    base_allocated = torch.cuda.memory_allocated()
    base_reserved = torch.cuda.memory_reserved()
    torch.cuda.reset_peak_memory_stats()
    # Peak contains input/base allocation plus this one forward's output and workspace.
    value = fn(); torch.cuda.synchronize()
    peak_allocated, peak_reserved = torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()
    debug_bytes = {}
    if attribution:
        debug_bytes = {name: getattr(value, name).numel() * getattr(value, name).element_size()
                       for name in ('gaussian_ids', 'gaussian_weights', 'all_contribution_sum', 'final_T')}
    del value; gc.collect(); torch.cuda.synchronize()
    events, wall = [], []
    for _ in range(repeats):
        torch.cuda.synchronize()
        start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        t0 = time.perf_counter(); start.record()
        value = fn(); end.record(); torch.cuda.synchronize()
        wall.append((time.perf_counter() - t0) * 1000)
        events.append(start.elapsed_time(end))
        del value
    result = dict(label=label, warmup=warmup, repeats=repeats,
                  whole_forward_cuda_events=summarize_ms(events), whole_forward_wall=summarize_ms(wall),
                  memory=dict(base_allocated_bytes=base_allocated, base_reserved_bytes=base_reserved,
                    peak_allocated_bytes=peak_allocated, peak_reserved_bytes=peak_reserved,
                    forward_peak_delta_allocated_bytes=peak_allocated-base_allocated,
                    reserved_growth_bytes=peak_reserved-base_reserved, debug_tensor_bytes=debug_bytes,
                    debug_total_bytes=sum(debug_bytes.values())))
    if attribution:
        guard('cpu_copy_' + label)
        value = fn(); torch.cuda.synchronize()
        copies = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            cpu = [getattr(value, n).cpu() for n in debug_bytes]
            torch.cuda.synchronize(); copies.append((time.perf_counter()-t0)*1000)
            del cpu
        result['cpu_copy_all_debug_maps'] = summarize_ms(copies)
        del value
    if profile_kernels:
        # A separate pass avoids profiling or disk/PNG/copy overhead in forward timing.
        # CUPTI times the actual compositor kernel; results explicitly marked profiled.
        guard('kernel_profile_' + label)
        try:
            with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,
                                                   torch.profiler.ProfilerActivity.CUDA]) as prof:
                for _ in range(repeats):
                    value = fn(); torch.cuda.synchronize(); del value
            kernel_events = [e for e in prof.events()
                             if e.device_type == torch.autograd.DeviceType.CUDA and 'renderCUDA' in e.name
                             and 'preprocess' not in e.name]
            if len(kernel_events) != repeats:
                raise RuntimeError('expected one compositor kernel per forward; got ' + str(len(kernel_events)))
            result['compositor_kernel_profiled'] = dict(summarize_ms([(e.time_range.end-e.time_range.start)/1000 for e in kernel_events]),
                names=sorted(set(e.name for e in kernel_events)), method='separate torch.profiler CUDA/CUPTI pass')
        except Exception as e:
            result['compositor_kernel_profiled'] = dict(status='NOT_AVAILABLE', reason=str(e))
    gc.collect(); torch.cuda.synchronize()
    return result
