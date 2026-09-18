"""One-way evaluation of immutable local outputs; no selection or parameter update."""
import numpy as np


def compute_machine_gates(base,prediction,repeats,shifted,angles,valid,cfg):
    g=cfg['gates'];real=base['accepted_count'];null=shifted['accepted_count']
    real_rate=real/base['query_count'] if base['query_count'] else 0
    null_rate=null/shifted['query_count'] if shifted['query_count'] else 0
    gs_median=float(np.median(angles['gs'])) if angles['gs'] else None
    random_median=float(np.median(angles['random'])) if angles['random'] else None
    shift_pass=bool(real_rate>0 and null_rate<=real_rate*g['G4_shift_ratio_max'])
    random_pass=bool(gs_median is not None and random_median is not None and random_median>0 and gs_median<=g['G4_random_angle_ratio_max']*random_median)
    machine=dict(G0=bool(valid and base['resolution_ok']),G1=real>=g['G1_min_count'],G2_machine=bool(prediction['passed']),G3=bool(repeats) and all(r['passed'] for r in repeats.values()),G4_machine=shift_pass and random_pass)
    return dict(machine=machine,manual={k:'PENDING_INDEPENDENT_REVIEW' for k in ['G2','G4_GS_benefit','G5']},nonnull=dict(real_count=real,shifted_count=null,real_query_denominator=base['query_count'],shifted_query_denominator=shifted['query_count'],real_rate=real_rate,shifted_rate=null_rate,shift_pass=shift_pass,gs_angle_median=gs_median,random_angle_median=random_median,random_pass=random_pass),video_trigger=machine['G1'] and machine['G2_machine'])
