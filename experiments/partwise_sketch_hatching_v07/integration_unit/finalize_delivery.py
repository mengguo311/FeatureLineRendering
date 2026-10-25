"""Freeze the delivery content manifest and archive; no new scientific work."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,sha,now
from pathlib import Path
import json,shutil,tarfile,subprocess,datetime
PACKAGE=ROOT/'delivery_20261025'
ARCHIVE=ROOT/'delivery_20261025.tar.gz'
WORKTREE=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07')
def load(p):return json.loads(p.read_text())
def write(p,x):
    assert p in (ROOT/'DEMO_README_ZH.md',ROOT/'DELIVERY_STATUS.json') or PACKAGE in p.parents
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    from run_integration import protocol,check_assets
    protocol();check_assets()
    assert load(UNIT/'portable_diagnostic_replay/REPLAY_RECEIPT.json')['all_equal']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORKTREE,text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=WORKTREE,text=True).strip();assert branch=='partwise-sketch-hatching-gaussian-link-v07'
    for p in (ROOT/'replay_package').rglob('*'):
        if p.is_file():assert sha(p)==sha(PACKAGE/'cold_baseline'/p.relative_to(ROOT/'replay_package'))
    receipt=load(ROOT/'units/unit_001/cold_hybrid/RELOAD_RECEIPT.json')
    for name,h in receipt['inputs'].items():assert sha(PACKAGE/'cold_baseline/data/lego'/name)==h
    out=PACKAGE/'evidence/unit_011'
    for name in ('REPORT_ZH.md','STATUS.json','NEXT.json','EXECUTION_RECORDS.json'):
        shutil.copyfile(UNIT/name,out/name)
    for p in (UNIT/'logs').iterdir():
        if p.is_file() and not p.name.startswith('finalize_delivery.'):shutil.copyfile(p,out/'logs'/p.name)
    shutil.copyfile(UNIT/'portable_diagnostic_replay/REPLAY_RECEIPT.json',out/'PORTABLE_REPLAY_RECEIPT.json')
    for p in HERE.iterdir():
        if p.is_file():shutil.copyfile(p,PACKAGE/'source/integration_unit'/p.name)
    shutil.copyfile(WORKTREE/'docs/partwise_sketch_hatching_v07/unit011_generation_carrier.md',PACKAGE/'source/unit011_generation_carrier.md')
    write(PACKAGE/'DELIVERY_PROVENANCE.json',dict(created_utc=now(),branch=branch,commit=commit,unit='unit_011',scientific_seal=False,parent_verification='pending',
        cold_bootstrap='unit001 completed once; copied input hashes and all cold_baseline source files equal current v07 replay package; no repeat cold run',
        portable_diagnostic=load(UNIT/'portable_diagnostic_replay/REPLAY_RECEIPT.json'),
        scope='Archive is a frozen delivery snapshot, not mutable orchestration or later execution bookkeeping.'))
    files={str(p.relative_to(PACKAGE)):sha(p) for p in sorted(PACKAGE.rglob('*')) if p.is_file() and p!=PACKAGE/'MANIFEST.json'}
    write(PACKAGE/'MANIFEST.json',dict(created_utc=now(),files=files,scope='Content manifest, not science seal. Orchestration excluded.'))
    for name,h in files.items():assert sha(PACKAGE/name)==h,name
    assert not ARCHIVE.exists()
    with tarfile.open(ARCHIVE,'w:gz',compresslevel=1) as tar:tar.add(PACKAGE,arcname=PACKAGE.name)
    # Read the entire archive and independently compare every member to its manifest.
    import hashlib
    checked=0
    with tarfile.open(ARCHIVE,'r:gz') as tar:
        for member in tar:
            if not member.isfile():continue
            relative=str(Path(member.name).relative_to(PACKAGE.name));h=hashlib.sha256()
            with tar.extractfile(member) as f:
                for block in iter(lambda:f.read(2**20),b''):h.update(block)
            expected=sha(PACKAGE/'MANIFEST.json') if relative=='MANIFEST.json' else files[relative]
            assert h.hexdigest()==expected,relative;checked+=1
    archive_sha=sha(ARCHIVE);manifest_sha=sha(PACKAGE/'MANIFEST.json')
    unit_results={f'unit_{i:03d}':load(ROOT/'units'/f'unit_{i:03d}'/'STATUS.json').get('scientific_verdict','See immutable unit report') for i in range(1,12)}
    result=dict(execution_state='completed',stage='science_frozen_delivery_archive_verified',created_utc=now(),branch=branch,source_commit=commit,
        scientific_verdict='No whole-object NPR winner established. Preserve original A as replay reference; H remains local PARTIAL only; unit011 D not promoted.',
        gaussian_link_progress='Original310475 PLY rows, geometry/fullSH/opacity/order, paper41058/ink21006 and M1/UNKNOWN195279 unchanged. Original-GS regional paper and alpha*T S gating of proxy paths; no new per-path Gaussian ownership certification.',
        final_unit='unit_011',unit_results=unit_results,scientific_seal=False,parent_verification='pending',
        bootstrap=dict(unit='unit_001',actual_cold_hybrid=True,verified_layers=5,all_array_equal=True,repeated_this_unit=False),
        latest_replay=load(UNIT/'cached_integration_replay/REPLAY_RECEIPT.json'),portable_replay=load(UNIT/'portable_diagnostic_replay/REPLAY_RECEIPT.json'),
        delivery=dict(package=str(PACKAGE),archive=str(ARCHIVE),archive_sha256=archive_sha,archive_bytes=ARCHIVE.stat().st_size,manifest_sha256=manifest_sha,manifest_files=len(files),archive_files_fully_read_and_hashed=checked),
        actual_backend='Linux CPU EWA fullSH3 original-GS layers; Open3D proxy visibility; original GS cached for unit011; not native CUDA or native Gaussian hatch',
        dependencies=dict(python='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python',numpy='2.2.6',scipy='1.15.3',plyfile='1.1.5',Pillow='12.2.0',open3d='0.20.0',cold_renderer_compiler='g++'),
        certifications=dict(local_linux_cpu=True,cross_platform=False,semantic_part_truth=False,physical_surface_truth=False,per_path_gaussian_ownership=False,temporal_stability=False),
        media=dict(full_objects=str(UNIT/'ALL_DEV_MATCHED.png'),natural=str(UNIT/'ALL_DEV_NATURAL.png'),rear_three_cameras=str(UNIT/'REAR_CAMERA_SEQUENCE.png'),continuous_movie_created_this_unit=False),
        negatives_preserved=['v05 far8.044%,eroded31px,author-region4.49%','v06 failed single-direction/gap/tone/contour/paper/local-frame outcomes','v07 unit001-011 negative/partial outcomes','H zero_step_cycle and partial style confound','Old independent cold-hybrid acceptance missing Open3D'],
        deadlines=dict(no_new_science_after_jst='2026-10-25T14:25:00+09:00',science_wrap_jst='2026-10-25T14:45:00+09:00',hardstop_jst='2026-10-25T15:00:00+09:00'),
        stop_reason='No-new-science deadline reached; current authorized experiment and delivery completed before wrap.',remaining_required_work='Parent independent verification only; no pending local producer, tests or renders.',
        resources=dict(cpu_affinity=2,numeric_threads=1,serial=True,GPU=False,training=False,installs=False,nested_models=False,push_merge=False))
    write(ROOT/'DELIVERY_STATUS.json',result)
    text=f'''# v07 实验与交付

**unit011已完成，整体排线优势未建立，默认不变。** 固定380条材料种子与请求长度，在保存的降噪载体C上执行同一展开行走后映回原载体O；完整前后图仍有碎线和交叉网格。弱后侧B/D覆盖35.658%/35.625%，不能以微小支持增益宣称成功。H仅局部PARTIAL，未升级。14:25新科学启动截止已到，本次已完成当前实验与交付收尾，没有新开科学单元。

## 直接查看

- [unit011中文报告](units/unit_011/REPORT_ZH.md)
- [完整物体配平对照](units/unit_011/ALL_DEV_MATCHED.png) / [自然强度](units/unit_011/ALL_DEV_NATURAL.png)
- [后侧231/241/251三相机](units/unit_011/REAR_CAMERA_SEQUENCE.png)：三帧，非连续视频或时序认证。
- [执行状态](units/unit_011/STATUS.json) / [独立审计](units/unit_011/AUDIT.json)
- [H局部效果，非默认](units/unit_006/ALL_DEV_MATCHED.png)
- [总交付状态](DELIVERY_STATUS.json)

6项针对性测试先RED后GREEN；真实O控制逐值恢复旧B；43份冻结输入与380条D路径独立审计通过。单位内新进程和完全包内诊断入口均实际重栅格化A/B/D，35数组逐值恢复。原源行身份、PLY、几何、完整SH、opacity、纸底/墨权重及M1/UNKNOWN保持。

## 包与运行

[交付目录](delivery_20261025/README_ZH.md) / [压缩包](delivery_20261025.tar.gz) / [内容清单](delivery_20261025/MANIFEST.json)

压缩包SHA256：`{archive_sha}`。共{len(files)}个内容文件；完整读取归档并核对{checked}个文件哈希。分支`{branch}`，源码提交`{commit}`。内容哈希不等于科学封印，父级独立验证待完成。

现有解释器：`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python`。依赖NumPy2.2.6、SciPy1.15.3、plyfile1.1.5、Pillow12.2.0、Open3D0.20.0；冷GS另需g++。没有安装或修改旧环境。

完全包内的诊断回放使用保存的GS source/paper/S，实际重画三臂墨层。输出必须不存在：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/delivery_20261025/diagnostic/code/replay.py --view orbit_241_24_5.3 --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/user_diagnostic_replay_001
```

冷GS入口对应原A，不是新D。unit001曾实际冷重放一次，source/paper/S/pre-S墨/hybrid五层逐值一致；本轮不重复bootstrap。供用户重放：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/delivery_20261025/cold_baseline/code/linked_source_cli.py render --scene lego --hybrid --verify --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/user_cold_baseline_001
```

## 结论范围与负结果

unit001同载体展开行走、unit002固定切片载体降噪、unit003局部场、unit004种子重排、unit005投影引导均未建立整物体优势。unit006全局场H仅局部PARTIAL且交叉风格改变；unit007恢复交叉关系后后侧网格回归。unit008边界留白、unit009固定H材料路径换嵌入、unit010切片布局/嵌入四组合、unit011生成载体控制也未建立整物体收益。各真实协议、结果和失败保留于包内evidence及原units，未靠调整角度、白度或门槛回填。

这是既有NeRF Synthetic冻结vanilla-GS的CPU深度/TSDF代理实验，非本轮真实物体采集、RaDe训练或GT。输出为原GS区域纸底加原行alpha*T责任S门控代理墨。新路径有稳定身份和face/bary来源，没有逐路径原Gaussian所有权、原生Gaussian排线、完整语义分部或真实表面认证。区域S没有建立NPR质量优势，仍可与同墨预算ungated对照使用。

v05 far8.044%、31像素腐蚀目标及4.49%作者区域变化失败、v06各负结果、H zero_step_cycle、旧独立验收缺Open3D失败均未改写。只验证本机Linux CPU，未进行跨平台认证；四DEV和三arc共六不同曝光相机，不构成时序稳定性证明。没有GPU、训练、下载、嵌套模型或push/merge。
'''
    write(ROOT/'DEMO_README_ZH.md',text)
    print(json.dumps(dict(archive=str(ARCHIVE),sha256=archive_sha,bytes=ARCHIVE.stat().st_size,verified_files=checked,source_commit=commit,root_status=str(ROOT/'DELIVERY_STATUS.json'))),flush=True)
if __name__=='__main__':main()
