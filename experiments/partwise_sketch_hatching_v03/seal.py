"""Seal ONLY validated experiment001 evidence; mutable runtime is excluded."""
from runtime import *
import subprocess

def main():
    if (ROOT/'SEAL.json').exists(): raise FileExistsError(ROOT/'SEAL.json')
    validation=json.loads((ROOT/'DELIVERY_VALIDATION.json').read_text())
    results=json.loads((ROOT/'metrics/RESULTS.json').read_text())
    media=json.loads((ROOT/'media/VALIDATION.json').read_text())
    visual=json.loads((ROOT/'VISUAL_REVIEW.json').read_text())
    assert validation['valid'] and results['valid'] and media['all_valid'] and visual['reviewed']
    assert (ROOT/'REPORT_ZH.md').is_file() and (ROOT/'REPRODUCE.md').is_file()
    assert subprocess.check_output(['git','status','--porcelain'],text=True).strip()==''
    final_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-p2-v03'
    subprocess.run(['git','merge-base','--is-ancestor','653db72d8888ff63ebaa60638c119b374960dfe7','HEAD'],check=True)
    lock=json.loads((ROOT/'SOURCE_LOCK.json').read_text())
    for path,h in lock['files'].items(): assert sha(path)==h,path
    for source in sorted((ROOT/'runtime').glob('*')):
        if source.is_file() and not source.name.startswith('seal'):
            shutil.copyfile(source,output_path(ROOT/'evidence/runtime'/source.name))
    files=list(CODE.glob('*.py'))+list(DOC.glob('*'))
    files += [WORK/'experiments/partwise_sketch_hatching/core.py',WORK/'experiments/partwise_sketch_hatching/core_walk_v2.py',WORK/'experiments/partwise_sketch_hatching_v02/renderer.py',
              WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md',WORK/'docs/partwise_sketch_hatching_v02/P1_ROADMAP_ZH.md',WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit010_ZH.md']
    for source in files:
        shutil.copyfile(source,output_path(ROOT/'source_snapshot'/source.relative_to(WORK)))
    for name in ('asset.json','mesh.npz','strokes.npz','config.json','recipe.json','retained.npz'):
        shutil.copyfile(ASSET/name,output_path(ROOT/'inputs'/name))
    shutil.copyfile(ROOT.parent/'orchestration/BRIEF.md',output_path(ROOT/'BRIEF_SNAPSHOT.md'))
    import scipy, PIL
    write_json(ROOT/'DEPENDENCIES.json',dict(python_executable=PYTHON,python_version=sys.version,numpy=np.__version__,scipy=scipy.__version__,pillow=PIL.__version__,ffmpeg=FFMPEG,ffmpeg_sha256=sha(FFMPEG)))
    update_status('COMPLETE',execution_state='VALIDATED_COMPLETE',scientific_verdict='ZERO_HEADROOM_UNIDENTIFIABLE_FOR_H2__VALID_AUTHORED_STRUCTURE_DISPLAY',
        artifacts=dict(report=str(ROOT/'REPORT_ZH.md'),protocol=str(ROOT/'PROTOCOL.json'),metrics=str(ROOT/'metrics/RESULTS.json'),full_object=str(ROOT/'media/static_all_frames.png'),
                       orbit=str(ROOT/'media/orbit_comparison.mkv'),zoom=str(ROOT/'media/zoom_comparison.mkv'),validation=str(ROOT/'DELIVERY_VALIDATION.json'),
                       seal=str(ROOT/'SEAL.json'),manifest=str(ROOT/'SHA256_MANIFEST.json'),next=str(ROOT/'NEXT.json')),
        tests=dict(behavior_tests=8,tdd_red_rc=1,tdd_green_rc=0,comparison_camera_pairs=24,actual_output_controls=True,decoded_exact_frames=20,old_seals_unchanged=26,serial_replay_exact_files=56),
        blockers=['H2 has zero connected physical boundary support on accepted GT lamp; not tested.','No verified reconstructed lamp input; no reconstruction/H1-H5/novelty/temporal certification claim.'],
        commits=dict(protocol='ef135f45',implementation='ff6aafd3',final=final_commit),automatic_continuation=False,
        recovery='Delivery complete; do not run next experiment or unit011. Verify SHA256_MANIFEST with SEAL. Mutable runtime_final.json is deliberately outside seal.')
    skip={'SHA256_MANIFEST.json','SEAL.json','runtime_final.json'}
    manifest=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file(): continue
        rel=path.relative_to(ROOT)
        if rel.parts[0]=='runtime' or str(rel) in skip: continue
        assert not path.name.endswith('.partial')
        manifest.append(dict(path=str(rel),bytes=path.stat().st_size,sha256=sha(path)))
    write_json(ROOT/'SHA256_MANIFEST.json',dict(root=str(ROOT),files=manifest,excluded=['runtime/**','runtime_final.json','SHA256_MANIFEST.json','SEAL.json']))
    for row in manifest: assert sha(ROOT/row['path'])==row['sha256']
    seal=dict(manifest='SHA256_MANIFEST.json',manifest_sha256=sha(ROOT/'SHA256_MANIFEST.json'),file_count=len(manifest),
              total_bytes=sum(x['bytes'] for x in manifest),final_commit=final_commit,protocol_commit='ef135f45',implementation_commit='ff6aafd3',
              scientific_verdict='ZERO_HEADROOM_UNIDENTIFIABLE_FOR_H2',engineering_verdict='VALID_AUTHORED_STRUCTURE_DISPLAY',
              verified=True,scope='Producer-validated bounded GT diagnostic; no independent human certification.',
              created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),resources=resources())
    write_json(ROOT/'SEAL.json',seal)
    print(json.dumps(native(seal),allow_nan=False))

if __name__=='__main__': main()
