"""Orchestration helpers; stages receive explicitly separated image inputs."""
import json,time,hashlib
from pathlib import Path
import numpy as np
from .foundation import freeze_json
from .corrected_probe import infer_queries,save_probe,_json
from .multiscene import independent_eligibility
from .multiscene_report import pair_measurements


def run_inference_arm(directory,queries,cameras,fields,layers,box,delta,cfg,arm,split):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    freeze_json(directory/'queries.json',queries)
    start=time.monotonic();result=infer_queries(queries,cameras,fields,layers,box,delta,cfg)
    result.update(elapsed_seconds=time.monotonic()-start,arm=arm,split=split)
    summary=save_probe(directory,result)
    print(arm,split,summary,flush=True)
    return result


def scope_decisions(scenes):
    by_name={s['scene']:s for s in scenes};eligible=[s for s in scenes if s['eligible']]
    def combine(rows):
        if not rows or any(not s['eligible'] for s in rows):return 'INSUFFICIENT_POSTERIOR_QUALITY'
        if any(s['verdict']=='ENGINEERING_NOT_READY' for s in rows):return 'ENGINEERING_NOT_READY'
        if any(s['verdict']=='STOP_B' for s in rows):return 'STOP_B'
        if all(s['verdict']=='FOUNDATION_GO' for s in rows):return 'FOUNDATION_GO'
        if all(s['verdict']=='PIVOT_IMAGE_ONLY' for s in rows):return 'PIVOT_IMAGE_ONLY'
        if all(s['verdict'] in ['FOUNDATION_GO','MACHINE_FOUNDATION_GO_MANUAL_PENDING'] for s in rows):return 'MACHINE_FOUNDATION_GO_MANUAL_PENDING'
        return 'UNDETERMINED'
    core=[by_name[n] for n in ['lego','chair']]
    expanded=len(eligible)>=3 and any(s['scene'] in ['drums','ficus'] for s in eligible)
    return dict(core=dict(verdict=combine(core),per_scene={s['scene']:s['verdict'] for s in core}),expanded=dict(verdict=combine(eligible) if expanded else 'INSUFFICIENT_POSTERIOR_QUALITY',eligible_scenes=[s['scene'] for s in eligible],scope_requirement_passed=expanded,required_minimum=3,requires_drums_or_ficus=True))


def prepare_eligibility(root,scene,cfg):
    directory=Path(root)/'scenes'/scene;directory.mkdir(parents=True,exist_ok=True)
    quality=[json.loads((Path(root)/f'quality/{scene}/seed_{seed}/measurements/quality.json').read_text()) for seed in [1729,2718]]
    paths=[Path(root)/f'quality/{scene}/seed_{seed}/measurements/native' for seed in [1729,2718]]
    pair_rows=pair_measurements(paths,cfg);pair=independent_eligibility([q['rows'] for q in quality],pair_rows,cfg)
    controlled=json.loads((Path(root)/f'controlled/{scene}/measurements/qualification.json').read_text())
    geometry=controlled['valid_parent_geometry'];doses=[v['name'] for v in controlled['variants'] if v['eligibility']['passed']]
    a=bool(pair['passed'] and all(q['eligibility']['calibration_pass'] for q in quality) and geometry)
    b=bool(quality[0]['eligibility']['passed'] and geometry and doses)
    result=dict(scene=scene,eligible=a or b,route_a=a,route_b=b,qualified_doses=doses,posterior_eligible=[q['eligibility']['passed'] for q in quality],valid_parent_geometry=geometry,delta=controlled['delta'],box=controlled['box'],quality=[q['eligibility'] for q in quality],pair=pair)
    freeze_json(directory/'pair.json',dict(rows=pair_rows,eligibility=pair));freeze_json(directory/'eligibility.json',result)
    return result
