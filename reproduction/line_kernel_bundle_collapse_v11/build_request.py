"""Metadata only. Invoke after recorded passing small tests; never starts science."""
import limits
import json
from pathlib import Path
from io_tools import sha, write_json

def main():
    source=Path(__file__).resolve().parent
    root=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_bundle_collapse_v11_20261103')
    runtime=root/'orchestration';unit=root/'units/unit_001'
    window=json.loads((runtime/'WINDOW.json').read_text())
    extract=json.loads((runtime/'SOURCE_CONFIG_EXTRACT.json').read_text())
    locks=json.loads((runtime/'INPUT_LOCK.json').read_text())
    decision=unit/'DECISION.json'
    # Only frozen parameters. The source arrays are not loaded by this builder.
    files={str(p):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    helper_paths=[Path(extract['renderer']),Path(extract['renderer']).with_name('common.py'),
                  Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_joint_gs_v01/build/libjoint.so')]
    helpers={str(p):sha(p) for p in helper_paths}
    stage=Path(window['input_stage'])
    config={**extract,'unit_root':str(unit),'runtime_root':str(runtime),'output_root':str(root),'unit':'unit_001',
            'decision_path':str(decision),'decision_sha256':sha(decision),'science_deadline':window['science_wrap_jst'],
            'absolute_deadline_jst':window['science_wrap_jst'],'canonical_geometry_frozen':True,
            'derived_geometry_edit_allowed':True,'final_ink_carrier':'derived_line_gaussians',
            'target_group_id':30579,'target_kernel_count':596,'target_version':21779,
            'target_rows_sha256':'5b0e387c307bc0a02e4737351f8c0eee3e635ea3da5aaa6f087f9eace8d4a9f6',
            'kernel_count':279616,'edit_scope':'target_group_only','uses_gpu':False,'uses_training':False,
            'membership':str(stage/'MEMBERSHIP.npz'),'groups':str(stage/'GROUPS.json'),'checkpoint':str(stage/'CHECKPOINT.json'),
            'source_files':files,'helper_files':helpers,'input_files':{**locks,str(stage/'CHECKPOINT.json'):sha(stage/'CHECKPOINT.json'),
                str(runtime/'WINDOW.json'):sha(runtime/'WINDOW.json'),str(runtime/'SOURCE_CONFIG_EXTRACT.json'):sha(runtime/'SOURCE_CONFIG_EXTRACT.json'),str(runtime/'INPUT_LOCK.json'):sha(runtime/'INPUT_LOCK.json')},
            'views':['0012','0036'],'max_seconds':900,'budgets':dict(readiness=60,transform=60,render=600,audit=180),
            'max_output_bytes':window['max_output_bytes'],'cpu_threads':2,'serial':True,
            'sh_source_relocation':dict(original='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/source/utils/sh_utils.py',
                frozen_copy=str(source/'sh_utils_pinned.py'),sha256=sha(source/'sh_utils_pinned.py'),
                byte_identical=True,only_renderer_ast_change='SH_PATH assignment; all equations unchanged'),
            'stages':['ORIGINAL','POSITION_ONLY','DERIVED'],
            'settings':dict(principal_axis_sign='largest absolute component positive, lowest coordinate tie',
                transverse_axis='least aligned world coordinate, lowest coordinate tie',
                curve='single equal-row-weight cubic Legendre graph over original min/max principal projections',
                ridge=0.01,ridge_degrees=[2,3],preserve_each_original_axial_coordinate=True,
                axial_span_fail_p=1e-8,eigen_gap_fail_factor=1e-12,
                sigma_perp_p=.15,sigma_parallel_p_min=.5,sigma_parallel_p_max=1.5,
                opacity_policy='unchanged',colors_policy='unchanged',background=[1,1,1],
                renderer_floor=.12**2,crop_sigma=3,crop_padding=16,display_enlargement=4,display_resampler='nearest',
                no_old_q_fit=True,no_view_dependent_geometry=True,no_parameter_scan=True),
            'scientific_contract':json.loads(decision.read_text())}
    config_path=unit/'CONFIG.json';write_json(config_path,config)
    receipt_path=unit/'TESTS_RECEIPT.json';receipt=json.loads(receipt_path.read_text())
    if receipt.get('returncode')!=0:raise ValueError('tests not passed')
    for item in receipt['logs']:
        if sha(item['path'])!=item['sha256']:raise ValueError('test log mismatch')
    request=dict(script=str(source/'runner.py'),config_path=str(config_path),config_sha256=sha(config_path),
                 source_files=files,helper_files=helpers,tests_receipt=str(receipt_path),max_seconds=900,
                 python=window['python'],command=[window['python'],'-B',str(source/'runner.py'),'--config',str(config_path)])
    write_json(unit/'RUN_REQUEST.json',request)
    print(json.dumps(dict(config_path=str(config_path),run_request=str(unit/'RUN_REQUEST.json'),
                         config_sha256=request['config_sha256'],source_file_count=len(files),tests_returncode=0)))

if __name__=='__main__':main()
