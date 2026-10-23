"""Metadata-only readback correction; never rewrites frozen scientific payloads."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,js,sha,now
from pathlib import Path
import argparse,json,shutil,subprocess

WORK=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v06')

def main(record_commit=False):
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    correction=UNIT/'HANDOFF_METADATA_CORRECTION.json'
    if not correction.exists():
        js(correction,dict(utc=now(),reason='Merged CAMERAS.scope shadowed representation text in runtime metadata. Restore STATUS/delivery representation from frozen PROTOCOL.scope; retain scientific files unchanged. Clarify that direction degeneracy concerns cutting-plane NORMAL versus face normal.',
            original_hashes={n:sha(UNIT/n) for n in ('STATUS.json','REPORT_ZH.md','NEXT.json','VISUAL_REVIEW.json')},
            frozen_science_changed=False))
    old='当前全局XY切平面与面法线';new='当前全局XY切平面的法向与面法线'
    report=UNIT/'REPORT_ZH.md';report.write_text(report.read_text().replace(old,new))
    for name,key in [('NEXT.json','recommended_next_step'),('VISUAL_REVIEW.json','next_step')]:
        data=json.loads((UNIT/name).read_text());data[key]=data[key].replace(old,new);js(UNIT/name,data)
    status=json.loads((UNIT/'STATUS.json').read_text());delivery=json.loads((OUTPUT_ROOT/'DELIVERY_STATUS.json').read_text())
    receipts=[dict(name=f.name,**json.loads(f.read_text())) for f in sorted((UNIT/'logs').glob('*.receipt.json'))]
    for data in (status,delivery):
        data['gaussian_link_progress']['representation']=p['scope']
        data['variant_retained']=True;data['variant_scope']='diagnostic endpoint only; default not promoted'
        data['final_readback_utc']=now()
        data['metadata_note']='Frozen PROTOCOL defines representation; per-view scope string records camera exposure. No image, array, metric, protocol or source snapshot changed.'
    status['tests_and_actual_commands']=receipts
    if record_commit:
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=WORK,text=True).strip()
        assert branch=='partwise-sketch-hatching-gaussian-link-v06'
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip()
        clean=not subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).strip()
        for data in (status,delivery):data.update(local_commit=commit,worktree_clean=clean)
    js(UNIT/'STATUS.json',status);js(OUTPUT_ROOT/'DELIVERY_STATUS.json',delivery)
    doc=WORK/'docs/partwise_sketch_hatching_v06/unit009_same_support_saturation_zh.md'
    doc.write_text(report.read_text())
    hand=UNIT/'handoff_source';shutil.copy2(Path(__file__),hand/Path(__file__).name)
    js(UNIT/'FINAL_HANDOFF_SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in hand.iterdir() if f.is_file()},
        prior_handoff_lock_sha256=sha(UNIT/'HANDOFF_SOURCE_LOCK.json')))
    names=['REPORT_ZH.md','README_ZH.md','STATUS.json','NEXT.json','PROTOCOL.json','DECISION.json','VALIDATION.json','MEDIA_VALIDATION.json','cold_replay_001/REPLAY_CHECK.json']
    for name in names:assert (UNIT/name).is_file()
    js(UNIT/'FINAL_HANDOFF_CHECK.json',dict(utc=now(),files={n:sha(UNIT/n) for n in names},scientific_payload_unchanged=True,
        execution_state=status['execution_state'],next_action='continue',local_commit=status.get('local_commit'),worktree_clean=status.get('worktree_clean')))
    print('Final metadata readback complete; frozen science unchanged',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--record-commit',action='store_true');args=ap.parse_args();main(args.record_commit)
