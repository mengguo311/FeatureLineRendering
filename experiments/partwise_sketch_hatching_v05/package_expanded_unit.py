"""Create a new continuation delivery; immutable science snapshot is copied."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import argparse,shutil,json


def package(unit):
    target=unit/'continuation_001/delivery';target.mkdir(parents=True,exist_ok=False)
    src=target/'source';shutil.copytree(unit/'source_snapshot',src)
    for name in ('continuation_exec.py','checked_expanded_replay.py','validate_expanded_unit.py','summarize_expanded_unit.py','finish_expanded_unit.py','inventory_unit005_resume.py','package_expanded_unit.py','seal_expanded_unit.py','verify_continuation_fixtures.py'):
        shutil.copyfile(Path(__file__).with_name(name),src/name)
    shell='''#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo 'Usage: bash run.sh UNIT_DIR {replay|query} --scene {chair|lego} [--index 0..3 --operation tint|opacity --output NEW_DIR]'
  exit 2
fi
unit="$1"
mode="$2"
shift 2
dir="$(cd "$(dirname "$0")" && pwd)"
python=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
case "$mode" in
  replay) exec "$python" "$dir/source/continuation_exec.py" "$dir/source/checked_expanded_replay.py" --unit "$unit" "$@" ;;
  query) exec "$python" "$dir/source/continuation_exec.py" "$dir/source/checked_expanded_replay.py" --unit "$unit" --query "$@" ;;
  *) echo 'Unknown mode' >&2; exit 2 ;;
esac
'''
    (target/'run.sh').write_text(shell);(target/'run.sh').chmod(0o755)
    text=f'''# Unit005 原始 Gaussian 联动复放

本包与 `{unit}` 的冻结协议、逐原行绑定和原始结果配套。源文件来自不可变 `source_snapshot`；新增续跑验证和临时目录适配器另列哈希。原始PLY、冻结代理资产和Python依赖仍是外部只读输入，没有声称跨机器独立安装。

从本目录执行以下命令。输出目录必须尚不存在，重复时换新名字：

```bash
bash run.sh {unit} replay --scene chair --index 0 --operation tint --arm specific --output {unit}/continuation_001/user_chair_tint
bash run.sh {unit} replay --scene lego --index 0 --operation opacity --arm specific --output {unit}/continuation_001/user_lego_opacity
bash run.sh {unit} query --scene lego --index 0 --arm specific --output {unit}/continuation_001/user_lego_paths
```

`replay` 从原PLY与保存的逐原行权重重新执行完整源渲染，逐数组对比既有结果；不使用代理面的彩色覆盖替代源编辑。`query` 导出每段锚点的全部实际接受原核ID与alpha×T、深度资格、权重和弃权；零事件/UNKNOWN锚点另存，不能解释为一线一点一核。

`results/<scene>/SOURCE_BINDING.npz` 是完整原始PLY行序的6通道M1证据、曝光、冲突和UNKNOWN；PATH_BINDING与FOOTPRINT_BINDING保存路径与完整核投影约束，EDIT_SELECTION保存原核编辑强度。PROTOCOL和BINDING_LOCK锁定数据、相机、阈值及控制。字段`previous_path`在unit005表示旧4视角**footprint**绑定。

绑定重建入口为 `source/run_expanded_unit.py --stage build`，随后budget 0..3、match、evaluate 0..3；它们必须逐阶段运行到另一个仅复制PROTOCOL.json/PROTOCOL_LOCK.json并预建results/scene的空输出目录，不能在已完成目录上重跑。所有冻结输入位置及SHA保存在协议，原始行数/顺序不变。该入口保留用于复现，本次交付不再次重跑已完成阶段。

全对象面板在 `results/<scene>/ALL_EVALUATION_VIEWS.png`；旧/新真实源编辑与明确放大的差分图在每视角expanded_vs_previous.png。media保存4个实际相机位置及4级实际源改色，全帧解码验收。PNG显示会裁剪颜色，raw RGB预算与另报clipped指标不同。

运行限制：CPU两核、单数值线程、CUDA关闭。临时文件仅进入本次parent continuation scratch。无环境转储、GPU、模型训练、源PLY写入或网络下载。当前为UNCERTIFIED_CPU_MAPPING；稀疏路径诊断不是整部件可用的Gaussian排线、语义分割或物理附着认证。
'''
    (target/'README_ZH.md').write_text(text)
    p=json.loads((unit/'PROTOCOL.json').read_text())
    for name,h in p['source_hashes'].items():assert sha(src/name)==h,name
    js(target/'PACKAGE_FILES.json',dict(utc=now(),unit=str(unit),protocol_sha256=sha(unit/'PROTOCOL.json'),
        original_frozen_source_exact=True,files={str(f.relative_to(target)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in target.rglob('*') if f.is_file()},
        external_inputs='Original PLY, saved proxy assets and readonly local Python; precise paths/hashes in PROTOCOL.json'))
    print(json.dumps(dict(delivery=str(target),source_members=len(p['source_hashes']),frozen_source_exact=True)),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);package(ap.parse_args().unit)
