"""Build a bounded evidence/replay handoff. Never modifies old assets or orchestration."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,VENDOR,sha,now
from pathlib import Path
import shutil,json
PACKAGE=ROOT/'delivery_20261025'

def write(path,value):
    assert path==ROOT/'DEMO_README_ZH.md' or path==ROOT/'DELIVERY_STATUS.json' or PACKAGE in path.parents
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
    assert not PACKAGE.exists();PACKAGE.mkdir()
    source=ROOT/'replay_package';shutil.copytree(source,PACKAGE/'cold_baseline')
    diagnostic=PACKAGE/'diagnostic';code=diagnostic/'code';data=diagnostic/'data';code.mkdir(parents=True);data.mkdir()
    for p in VENDOR.iterdir():
        if p.is_file() and p.suffix in ('.py','.cpp','.md','.json'):shutil.copyfile(p,code/p.name)
    shutil.copyfile(source/'code/runtime.py',code/'runtime.py')
    shutil.copyfile(HERE/'fixed_render.py',code/'fixed_render.py')
    shutil.copyfile(HERE/'portable_diagnostic.py',code/'replay.py')
    shutil.copyfile(source/'requirements.txt',diagnostic/'requirements.txt')
    shutil.copyfile(source/'data/lego/unit_008_asset/TARGET.npz',data/'TARGET.npz')
    shutil.copyfile(source/'data/lego/asset.json',data/'asset.json')
    shutil.copyfile(UNIT/'BUILD_MATCH.json',data/'BUILD_MATCH.json')
    (data/'paths').mkdir();(data/'frames').mkdir();cameras={}
    for arm in ('A','B','D'):
        for part in ('old','added'):shutil.copyfile(UNIT/'asset'/(arm+'_'+part+'.npz'),data/'paths'/(arm+'_'+part+'.npz'))
    for v in json.loads((UNIT/'CAMERAS.json').read_text())['views']:
        if v['kind']=='build' or v['camera']['view'] in cameras:continue
        view=v['camera']['view'];cameras[view]=v['camera'];shutil.copyfile(UNIT/v['kind']/view/'FRAME.npz',data/'frames'/(view+'.npz'))
    write(data/'CAMERAS.json',cameras)
    write(diagnostic/'MANIFEST.json',dict(files={str(p.relative_to(diagnostic)):sha(p) for p in sorted(diagnostic.rglob('*')) if p.is_file()},scope='All package-local cached-GS replay code, six reference frames, original target geometry and A/B/D paths.'))
    shutil.copytree(HERE,PACKAGE/'source/integration_unit',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(VENDOR,PACKAGE/'source/vendor',ignore=shutil.ignore_patterns('__pycache__'))
    evidence=PACKAGE/'evidence';evidence.mkdir()
    for i in range(1,12):
        src=ROOT/'units'/f'unit_{i:03d}';out=evidence/src.name;out.mkdir()
        for name in ('REPORT_ZH.md','STATUS.json','NEXT.json','PROTOCOL.json','AUDIT.json'):
            if (src/name).exists():shutil.copyfile(src/name,out/name)
    out=evidence/'unit_011'
    for name in ('ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','VISUAL_REVIEW.json','BUILD_MATCH.json','GEOMETRY_READBACK.json','FAR_ABSOLUTE.json','FAR_READBACK.json','VISIBLE_INTERVENTION.json','INPUT_LOCK.json','SOURCE_LOCK.json','EXECUTION_RECORDS.json'):
        shutil.copyfile(UNIT/name,out/name)
    shutil.copytree(UNIT/'asset',out/'asset');shutil.copytree(UNIT/'logs',out/'logs')
    shutil.copytree(UNIT/'attribution',out/'attribution');shutil.copytree(UNIT/'cached_integration_replay',out/'cached_integration_replay')
    shutil.copyfile(ROOT/'units/unit_001/cold_hybrid/RELOAD_RECEIPT.json',evidence/'COLD_HYBRID_RECEIPT.json')
    shutil.copyfile(ROOT/'units/unit_006/ALL_DEV_MATCHED.png',evidence/'H_LOCAL_PARTIAL_NOT_DEFAULT.png')
    write(PACKAGE/'README_ZH.md', '''# v07 截止交付

Lego载体/生成器实验没有建立整物体NPR优势；保留原A作为历史回放参照，H仅局部PARTIAL，不升级默认。unit011的380条固定种子在C上积分后映回O，仍无明确整物体收益。所有旧负结果保留在evidence各单元报告中。

- cold_baseline：包内原PLY、原行权重与完整CPU EWA冷回放CLI；--hybrid仅重放原A，不是新D。unit001已一次真实冷重放，五层逐值一致；此次打包不重复bootstrap。
- diagnostic：完全包内的source/paper/S缓存，加A/B/D路径实际重栅格化；支持六个已曝光相机。它不是冷GS回放。
- source：冻结科学实现及交付适配源码；科学生产者仍保留本机绝对路径，独立便携入口使用diagnostic/code/replay.py。
- evidence：11个单元报告/协议/状态；unit011完整核心数组、失败/执行日志和完整物体图；H局部图明确非默认。

依赖见各requirements.txt。已使用Linux CPU上的NumPy2.2.6、SciPy1.15.3、plyfile1.1.5、Pillow12.2.0、Open3D0.20.0；冷GS另需g++。没有安装、训练或GPU执行。只认证本机实际运行，不声称跨平台通过。

在解压目录用上述现有Python运行，输出必须为新目录：

```bash
python -B diagnostic/code/replay.py --view orbit_241_24_5.3 --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/user_diagnostic_replay_001
python -B cold_baseline/code/linked_source_cli.py mapping --scene lego --ids 0 1 310474
python -B cold_baseline/code/linked_source_cli.py render --scene lego --hybrid --verify --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/user_cold_baseline_001
```

以上cold命令供用户重放，本次交付不再次执行。source_index是原PLY零起始行号；区域S为原核alpha*T加权墨责任；新stroke有face/bary与原父路径来源，没有逐路径Gaussian所有权认证。代理来自既有vanilla-GS的CPU深度/TSDF，不是RaDe训练或真实表面。三后侧帧不是连续视频或时序认证。v05 far8.044%等旧失败、缺依赖旧独立验收失败与H zero_step_cycle均保留。

包MANIFEST.json覆盖内容文件，不把可变orchestration作为科学封印；父级独立验证仍待完成。
''')
    write(PACKAGE/'MANIFEST.json',dict(created_utc=now(),files={str(p.relative_to(PACKAGE)):sha(p) for p in sorted(PACKAGE.rglob('*')) if p.is_file()},scope='Content hashes only; not a scientific seal or parent acceptance. Orchestration excluded.'))
    print(json.dumps(dict(package=str(PACKAGE),files=len(json.loads((PACKAGE/'MANIFEST.json').read_text())['files']),manifest_sha256=sha(PACKAGE/'MANIFEST.json'))),flush=True)
if __name__=='__main__':main()
