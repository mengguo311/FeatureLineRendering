"""Ship a single experimental Ficus alternative alongside the unchanged catalog."""
import runtime
from runtime import OUTPUT_ROOT, output_guard, js, sha, now
from pathlib import Path
import argparse, json, shutil, subprocess, sys
from validate_replays import compare


def run(unit,phase):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text())
    previous=Path(p['previous_unit']);here=Path(__file__).resolve().parent
    package=unit/'portable_demo'
    def logged(name,command):
        subprocess.run([sys.executable,str(here/'run_logged.py'),'--unit',str(unit),'--name',name,
            '--',*map(str,command)],timeout=590,check=True)
    if phase=='stage':
        decision=json.loads((unit/'DECISION.json').read_text())
        shutil.copytree(previous/'portable_demo',package)
        assert not (package/'runs').exists()
        for f in (package/'source').iterdir():
            if f.is_file():shutil.copy2(here/f.name,f)
        shutil.copytree(unit/'assets/edited',package/'assets/ficus_retained137k')
        shutil.copytree(unit/'assets/original',package/'assets/ficus_comparison30k')
        cat=json.loads((package/'CATALOG.json').read_text())
        cat['scenes']['ficus']['asset']='assets/ficus_retained137k'
        js(package/'EXPERIMENTAL_CATALOG.json',cat)
        if decision['promote_candidate']:
            js(package/'CATALOG.json',cat)
        out=package/'previews/unit010';out.mkdir()
        for f in (unit/'media').iterdir():
            if f.suffix in ('.png','.mkv'):shutil.copy2(f,out/f.name)
        shutil.copy2(unit/'PACKAGE_README_ZH.md',package/'README_ZH.md')
        metadata=json.loads((package/'PORTABLE_DEMO.json').read_text())
        metadata.update(created_utc=now(),source_unit=unit.name,
            previous_package_sha256=sha(previous/'portable_demo.tar.gz'),simplification_decision=decision,
            experimental_asset='assets/ficus_retained137k')
        js(package/'PORTABLE_DEMO.json',metadata)
        js(unit/'metrics/PACKAGE_INPUTS.json',dict(source=str(previous/'portable_demo'),
            files={str(f.relative_to(previous/'portable_demo')):sha(f) for f in (previous/'portable_demo').rglob('*') if f.is_file()},
            default_catalog_changed=decision['promote_candidate']))
    elif phase=='replay':
        package=unit/'relocated/portable_demo';rows=[]
        decision=json.loads((unit/'DECISION.json').read_text())
        for key in ('chair','lego','drums','ficus'):
            dest=package/f'runs/cold_{key}'
            command=[package/'run.sh','preview','--scene',key,'--output',dest]
            logged('portable_preview_'+key,command)
            reference=previous/f'relocated/portable_demo/runs/cold_{key}'
            if key=='ficus' and decision['promote_candidate']:reference=unit/'renders/static_edited'
            rows.append(dict(scene=key,exact_files=[compare(reference/f'frame_000_{s}',dest/f'frame_000_{s}')
                for s in ('image.png','arrays.npz')]))
        candidate=package/'assets/ficus_retained137k'
        dest=package/'runs/cold_candidate'
        logged('portable_candidate',[package/'run.sh','preview','--scene','ficus','--asset',candidate,'--output',dest])
        candidate_exact=[compare(unit/f'renders/static_edited/frame_000_{s}',dest/f'frame_000_{s}') for s in ('image.png','arrays.npz')]
        edited=package/'runs/candidate_recreated_baseline'
        logged('portable_candidate_edit',[package/'run.sh','edit','--scene','ficus','--asset',candidate,
            '--part','2','--angle','45','--output',edited])
        preview=package/'runs/candidate_recreated_preview'
        logged('portable_candidate_edit_preview',[package/'run.sh','preview','--scene','ficus','--asset',edited,'--output',preview])
        edit_exact=[compare(unit/f'renders/static_baseline/frame_000_{s}',preview/f'frame_000_{s}') for s in ('image.png','arrays.npz')]
        js(unit/'metrics/PORTABLE_REPLAY.json',dict(status='PASS',scenes=rows,candidate_exact=candidate_exact,
            candidate_edit_baseline_exact=edit_exact,original_PLY_not_required=True,python_environment_bundled=False))
    else:raise ValueError(phase)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',required=True,type=Path)
    ap.add_argument('phase',choices=['stage','replay']);a=ap.parse_args();run(a.unit,a.phase)
