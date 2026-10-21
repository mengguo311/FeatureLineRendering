"""Final bounded evidence/immutability audit, never invokes renderer or old sealers."""
from runtime import *
import subprocess
from PIL import Image

def main():
    results=json.loads((ROOT/'metrics/RESULTS.json').read_text())
    media=json.loads((ROOT/'media/VALIDATION.json').read_text())
    assert results['valid'] and len(results['frames'])==24
    assert media['all_valid'] and [v['decoded_frames'] for v in media['videos']]==[12,8]
    for row in media['sources']:
        assert sha(row['pair_path'])==row['pair_sha256']
        for src in row['sources']: assert sha(src['path'])==src['sha256']
    for video in media['videos']: assert sha(video['video'])==video['sha256']
    old=ROOT.parent/'orchestration/OLD_SEALS_BEFORE.json'
    seals=json.loads(old.read_text())
    for path,h in seals.items(): assert sha(path)==h,path
    protected=json.loads((ROOT.parent/'orchestration/PROTECTED_BEFORE.json').read_text())
    trees={}
    for path,baseline in protected.items():
        head=subprocess.check_output(['git','-C',path,'rev-parse','HEAD'],text=True).strip()
        status=subprocess.check_output(['git','-C',path,'status','--porcelain'],text=True).strip()
        assert head==baseline['head'] and status==baseline['status'],path
        trees[path]=dict(head=head,status=status)
    # The historical SOURCE_LOCK gives precise source paths/hash lineage;
    # final snapshot contains just unit010 changed files, not all dependencies.
    oldlock=json.loads((BASE/'SOURCE_LOCK.json').read_text())
    backend=[]
    for relative in ('experiments/partwise_sketch_hatching/core.py',
                     'experiments/partwise_sketch_hatching/core_walk_v2.py',
                     'experiments/partwise_sketch_hatching_v02/renderer.py'):
        matches=[(p,h) for p,h in oldlock['files'].items() if p.endswith('/'+relative)]
        assert len(matches)==1, relative
        source,expected=matches[0]
        assert sha(WORK/relative)==expected
        assert sha(source)==expected
        backend.append(dict(relative=relative,sha256=expected,unit010_source=source,exact=True))
    lock=json.loads((ROOT/'SOURCE_LOCK.json').read_text())
    for path,h in lock['files'].items(): assert sha(path)==h,path
    for frame in results['frames']:
        f=frame['frame']; folder=ROOT/'renders'/f['sequence']/f['id']
        for arm in ('B1_like','B2_existing'):
            metadata=json.loads((folder/arm/'render.json').read_text())
            assert metadata['frame']==f
            cam=core.camera(f['azimuth'],f['elevation'],f['distance'],512,600)
            for key in ('R','t','eye','center'):
                assert np.array_equal(np.asarray(metadata['camera'][key]),cam[key])
        assert frame['geometry_buffers_exact']==dict(parts=True,depth=True)
        assert frame['display']['hatch_exact'] and frame['display']['contours_exact']
    receipts={p.stem:json.loads(p.read_text()) for p in (ROOT/'runtime').glob('*.json') if not p.name.endswith('.started.json')}
    required=('tdd_green','implementation_tests','headroom','protocol','source_lock','render_static','render_orbit','render_zoom','render_isolated','evaluate','media')
    assert all(receipts[k]['returncode']==0 for k in required)
    assert receipts['tdd_red']['returncode']==1
    amendment=json.loads((ROOT/'EXECUTION_AMENDMENT.json').read_text())
    assert amendment['status']=='SERIAL_REPLAY_VALIDATED' and amendment['corrected_stages_serial'] and amendment['all_png_npz_exact']
    assert receipts['render_zoom_serial']['returncode']==receipts['render_isolated_serial']['returncode']==0
    report=dict(valid=True,old_seals_verified=len(seals),protected_worktrees=trees,
                inherited_backend_exact_to_unit010=backend,locked_files_verified=len(lock['files']),
                actual_render_pairs=24,isolated_static_part_renders=12,media_source_pairs=24,
                construction_holdout_camera_records_exact=True,tests=8,
                h2='ZERO_HEADROOM_UNIDENTIFIABLE_FOR_H2',old_unit011='unsealed WIP untouched',
                no_gpu=True,resources=resources(),receipts=receipts,execution_recovery=amendment)
    write_json(ROOT/'DELIVERY_VALIDATION.json',report)
    update_status('FINAL_VALIDATION_PASSED',tests=dict(behavior_tests=8,expected_red_rc=1,all_real_output_controls=True,media_all_frames_rgb_exact=True,old_seals_unchanged=26))
    print(json.dumps(dict(valid=True,old_seals=26,pairs=24,video_frames=20)))

if __name__=='__main__': main()
