"""Freeze metadata after small tests; never executes the full-data runner."""
import limits
import json
from pathlib import Path
from io_tools import sha,write_json

def main():
    source=Path(__file__).resolve().parent
    root=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_full_bundle_collapse_v12_20261103')
    runtime=root/'orchestration';unit=root/'units/unit_001'
    window=json.loads((runtime/'WINDOW.json').read_text());extract=json.loads((runtime/'SOURCE_CONFIG_EXTRACT.json').read_text())
    locks=json.loads((runtime/'INPUT_LOCK.json').read_text());inventory=json.loads((runtime/'INPUT_INVENTORY.json').read_text())
    files={str(p):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    helper_paths=[Path(extract['renderer']),Path(extract['renderer']).with_name('common.py'),
        Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_joint_gs_v01/build/libjoint.so')]
    helpers={str(p):sha(p) for p in helper_paths};stage=Path(window['input_stage']);decision=unit/'DECISION.json'
    inputs={**locks,str(stage/'CHECKPOINT.json'):sha(stage/'CHECKPOINT.json')}
    for n in ['BRIEF.md','WINDOW.json','INPUT_LOCK.json','INPUT_INVENTORY.json','SOURCE_CONFIG_EXTRACT.json']:
        inputs[str(runtime/n)]=sha(runtime/n)
    regression=Path(window['old_output'])/'units/unit_001/POSITION_ONLY_GAUSSIANS.npz'
    config={**extract,'unit_root':str(unit),'runtime_root':str(runtime),'output_root':str(root),'unit':'unit_001',
        'decision_path':str(decision),'decision_sha256':sha(decision),'science_deadline':window['science_wrap_jst'],
        'absolute_deadline_jst':window['science_wrap_jst'],'canonical_geometry_frozen':True,
        'derived_geometry_edit_allowed':True,'final_ink_carrier':'derived_line_gaussians',
        'edit_scope':'all_existing_edge_groups','all_existing_groups':True,
        'geometry_policy':'position_only_ridge_legendre_v11','unknown_policy':'preserve_original',
        'membership_frozen':True,'uses_gpu':False,'uses_training':False,
        'kernel_count':inventory['rows'],'expected_inventory':inventory,
        'membership':str(stage/'MEMBERSHIP.npz'),'groups':str(stage/'GROUPS.json'),'checkpoint':str(stage/'CHECKPOINT.json'),
        'source_files':files,'helper_files':helpers,'input_files':inputs,
        'views':['0012','0036'],'max_seconds':900,'budgets':dict(readiness=60,transform=240,render=420,audit=180),
        'max_output_bytes':window['max_output_bytes'],'cpu_threads':2,'serial':True,'checkpoint_groups':128,
        'regression_asset':str(regression),'regression_group_id':30579,'regression_atol_p':1e-12,
        'regression_rows_sha256':'5b0e387c307bc0a02e4737351f8c0eee3e635ea3da5aaa6f087f9eace8d4a9f6',
        'stages':['ORIGINAL','FULL_POSITION_ONLY'],
        'settings':dict(group_order='ascending edge_id; ascending original row within group',
            enumeration='all edge_id>=0 from complete MEMBERSHIP, not 13 tracked MODELS',
            curve='exact v11 core.collapse on group-local original arrays; use position_only.means only',
            ridge=.01,ridge_degrees=[2,3],preserve_original_axial_coordinates=True,
            principal_axis_sign='largest absolute component positive; lowest coordinate tie',
            transverse_axis='least aligned world coordinate; lowest coordinate tie',
            eigen_gap_fail_factor=1e-12,axial_span_fail_p=1e-8,
            finite_numeric_group_failures='retain original group and record SKIPPED_NUMERICAL',
            unknown_exceptions='FAILED, remaining NOT_RUN, no false complete result',
            covariance_policy='bitwise unchanged',opacity_policy='bitwise unchanged',colors_policy='bitwise unchanged',
            background=[1,1,1],renderer_floor=.12**2,quadrant_x=[0,388,777],quadrant_y=[0,290,581],
            quadrant_display_scale=2,display_resampler='nearest',
            worst_case_selection='top3 maximum displacement/p, group ID tie',worst_crop_sigma=3,worst_crop_padding=16,
            no_parameter_scan=True,no_view_dependent_geometry=True,no_auxiliary_curve_ink=True),
        'scientific_contract':json.loads(decision.read_text()),'next_action':'stop_full_model_demo_finished'}
    path=unit/'CONFIG.json';write_json(path,config)
    receipt_path=unit/'TESTS_RECEIPT.json';receipt=json.loads(receipt_path.read_text())
    if receipt['returncode']!=0:raise ValueError('tests not green')
    for item in receipt['logs']:
        if sha(item['path'])!=item['sha256']:raise ValueError('test log hash mismatch')
    request=dict(script=str(source/'runner.py'),config_path=str(path),config_sha256=sha(path),
        source_files=files,helper_files=helpers,tests_receipt=str(receipt_path),max_seconds=900,
        python=window['python'],command=[window['python'],'-B',str(source/'runner.py'),'--config',str(path)])
    write_json(unit/'RUN_REQUEST.json',request)
    print(json.dumps(dict(run_request=str(unit/'RUN_REQUEST.json'),config_sha256=sha(path),source_count=len(files))))

if __name__=='__main__':main()
