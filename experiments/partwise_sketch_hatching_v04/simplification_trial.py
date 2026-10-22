"""One frozen real-Ficus face-budget comparison; never alter the source unit."""
import runtime
from runtime import OUTPUT_ROOT, output_guard, js, sha, now
from pathlib import Path
import argparse, copy, json, shutil, time
import numpy as np
from geometry import orbit_camera


def freeze(unit):
    unit = output_guard(unit)
    unit.mkdir(exist_ok=True)
    if (unit/'PROTOCOL.json').exists():
        raise FileExistsError('already frozen')
    old = OUTPUT_ROOT/'units/unit_009'
    p = json.loads((old/'PROTOCOL.json').read_text())
    p.update(version=10, frozen_utc=now(), previous_unit=str(old),
        unit_deadline_jst='2026-10-22T05:58:31+09:00')
    p['filtering']['simplify_faces'] = 150000
    p['static_cameras'] = p['static_cameras'][:4] + [orbit_camera(a,22,5.1) for a in (83,173,263,353)]
    p['orbit'] = [orbit_camera(83+30*k,22,5.1) for k in range(12)]
    p['zoom'] = [orbit_camera(113,26,float(d)) for d in np.linspace(5.5,4.5,6)]
    p['viewer_camera'] = dict(azimuth=83,elevation=22,distance=5.1)
    p['comparison_scope'] = 'One engineering simplification ablation: 30k versus retained cleaned mesh capped at 150k. Same source depths, TSDF, height rule and styles. No H1/H2 or independent surface truth.'
    p['exposure'] = 'Four original dataset cameras historically exposed; four new virtual static poses and trajectories frozen here before any candidate output. Not blind reconstruction holdout.'
    p['decision'] = 'Review shows canopy holes and fragmented paths. Test removing aggressive decimation once; no sweep, smoothing, GT repair or changed depth gates.'
    p['changed_variable'] = dict(geometry_comparison='face budget 30000 -> 150000; all paths regenerated on changed mesh; cross-arm path IDs are not correspondences',
        region=2, angle=95., fixed='within each asset local edit: geometry, labels, other-region paths/styles, cameras')
    p['permitted_engineering_fix'] = 'Read and validate explicit simplify_faces before data loading; retain legacy default 30000 and hard maximum 150000.'
    p['expected_tests'] = ['real fusion red then green', 'invalid budgets rejected before source reads',
        '8 full-object same-camera baseline/candidate comparisons', 'path length, ink, coverage and CPU costs',
        'local edit and cold reload', '12 orbit + 6 zoom full decode',
        'only promote if actual complete-object appearance is useful; preserve 30k asset regardless']
    p['candidate_acceptance'] = 'Descriptive primary-agent visual assessment of all views: retain more readable foliage/shape without obvious new clutter; report coverage/ink/cost alongside short-path fraction. No numerical post-hoc gate. If not useful retain 30k default and ship candidate as explicitly experimental.'
    inputs = [old/f for f in ('PROTOCOL.json','STATUS.json','REPORT_ZH.md','NEXT.json','ENGINEERING_SEAL.json','proxy/PROXY.json')]
    inputs += list((old/'assets/baseline').glob('*'))
    inputs += [old/'proxy'/(c['view']+'.npz') for c in p['build_cameras']]
    inputs += [Path(p['original']['original_ply']), *map(Path,p['references'].values())]
    p['inputs_sha256'] = {str(f):sha(f) for f in inputs if f.is_file()}
    assert sha(p['original']['original_ply']) == p['original']['sha256']
    js(unit/'PROTOCOL.json',p)
    js(Path('docs/partwise_sketch_hatching_v04/UNIT010_PROTOCOL.json'),p)
    for dest in (unit,unit/'tests/fusion_red'):
        (dest/'proxy').mkdir(parents=True)
        if dest != unit: shutil.copy2(unit/'PROTOCOL.json',dest/'PROTOCOL.json')
        for c in p['build_cameras']:
            shutil.copy2(old/'proxy'/(c['view']+'.npz'),dest/'proxy'/(c['view']+'.npz'))
    (unit/'build').mkdir()
    shutil.copy2(old/'build/libsource.so',unit/'build/libsource.so')
    original = unit/'assets/original'
    shutil.copytree(old/'assets/baseline',original)
    meta = json.loads((original/'asset.json').read_text())
    meta.update(cameras=p['static_cameras'],orbit=p['orbit'],zoom=p['zoom'],viewer_camera=p['viewer_camera'],
        replay_source_asset_sha256=sha(old/'assets/baseline/asset.json'))
    js(original/'asset.json',meta)
    js(unit/'INPUT_REUSE.json',dict(qualified_depth_files=24,source=str(old),
        copied_depths_exact=all(sha(unit/'proxy'/(c['view']+'.npz')) == p['inputs_sha256'][str(old/'proxy'/(c['view']+'.npz'))] for c in p['build_cameras']),
        source_renderer_sha256=sha(unit/'build/libsource.so'),original_paths_unchanged=True))
    print(json.dumps(dict(protocol=str(unit/'PROTOCOL.json'),sha256=sha(unit/'PROTOCOL.json'))))


def test_fuse(unit):
    from fuse_cpu import fuse
    fuse(unit)
    actual = json.loads((unit/'proxy/PROXY.json').read_text())
    expected = json.loads((OUTPUT_ROOT/'units/unit_009/proxy/PROXY.json').read_text())['before_simplification_faces']
    result = dict(expected_cleaned_faces=expected,actual_faces=actual['faces'],
        requested_budget=150000,source='actual frozen Ficus qualified depths',
        passed=actual['faces']==expected and actual['faces']>30000)
    js(unit/'RESULT.json',result)
    assert result['passed'], 'fuse ignores protocol face budget and decimates the real Ficus mesh'


def invalid_budgets(unit):
    from fuse_cpu import fuse
    rows=[]
    for i,value in enumerate((0,-1,True,150001,30000.5,'150000',None)):
        dest=unit/'tests/invalid_budgets'/str(i)
        dest.mkdir(parents=True)
        # No original source or proxy directory: invalid configuration must fail first.
        js(dest/'PROTOCOL.json',dict(filtering=dict(simplify_faces=value)))
        try: fuse(dest)
        except ValueError as exc: rows.append(dict(value=value,error=str(exc)))
        else: raise AssertionError('accepted invalid face budget')
    js(unit/'tests/INVALID_BUDGETS.json',dict(status='PASS',cases=rows))


def compare(unit):
    from demo import load_asset
    from scipy import ndimage
    from PIL import Image
    from media import contact
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text())
    result=dict(utc=now(),scope=p['comparison_scope'],arms={})
    for arm in ('original','baseline'):
        mesh,paths,meta=load_asset(unit/'assets'/arm)
        per={}
        for r,s in paths.items():
            seg=np.linalg.norm(s['points'][:,1]-s['points'][:,0],axis=1)
            _,idx=np.unique(s['stroke_id'],return_inverse=True)
            lengths=np.bincount(idx,weights=seg)
            per[str(r)]=dict(paths=len(lengths),segments=len(seg),length_world=float(lengths.sum()),
                short_paths=int((lengths<meta['styles'][str(r)]['length']/2).sum()),
                short_fraction=float((lengths<meta['styles'][str(r)]['length']/2).mean()),
                median_length=float(np.median(lengths)))
        rows=[]
        for i,c in enumerate(p['static_cameras']):
            with np.load(unit/f'renders/static_{arm}/frame_{i:03d}_arrays.npz') as f:
                a={k:f[k] for k in f.files}
            rec=json.loads((unit/f'renders/static_{arm}/frame_{i:03d}.json').read_text())
            mask=a['regions']>0
            closed=ndimage.binary_fill_holes(mask)
            _,components=ndimage.label(mask)
            regions={str(r):dict(visible_pixels=int((a['regions']==r).sum()),
                hatch_pixels=int(((a['regions']==r)&(a['hatch']>.1)).sum()),
                hatch_ink=float(a[f'layer_{r}'].sum())) for r in paths}
            iou=None
            if c['view'] in p['references']:
                ref=np.asarray(Image.open(p['references'][c['view']]).convert('RGBA').resize((512,512),Image.Resampling.NEAREST))[:,:,3]>=128
                iou=float((mask&ref).sum()/max(1,(mask|ref).sum()))
            rows.append(dict(view=c['view'],seconds=rec['seconds'],complete_object=rec['bounds']['all_proxy_vertices_inside'],
                foreground_pixels=int(mask.sum()),image_mask_components=int(components),
                enclosed_background_pixels=int((closed&~mask).sum()),
                hatch_ink=float(a['hatch'].sum()),contour_ink=float(a['contour'].sum()),
                total_ink=float((1-a['image']).sum()),reference_alpha_iou=iou,regions=regions))
        result['arms'][arm]=dict(vertices=len(mesh['vertices']),faces=len(mesh['faces']),regions=per,
            total_paths=sum(x['paths'] for x in per.values()),short_paths=sum(x['short_paths'] for x in per.values()),
            length_world=sum(x['length_world'] for x in per.values()),frames=rows,
            median_render_seconds=float(np.median([x['seconds'] for x in rows])))
    result['limitations']=['mask holes/components are image-space descriptive counts and include legitimate leaf gaps',
        'same-model source depths and self-proxy attachment are not independent geometry truth',
        'shared height rule produces different per-face boundaries after remeshing; no cross-mesh path identity claim',
        'denser triangulation changes path segmentation and CPU cost; fewer short paths alone is not a quality verdict']
    out=unit/'media';out.mkdir(exist_ok=True)
    for start,label in ((0,'historical'),(4,'new')):
        items=[]
        for i in range(start,start+4):
            c=p['static_cameras'][i]
            ref=Image.open(p['references'].get(c['view'],str(unit/f'source_model/frame_{i:03d}_rgb.png'))).convert('RGBA')
            bg=Image.new('RGBA',ref.size,'white');bg.alpha_composite(ref)
            items.append((c['view']+' | reference / source RGB',bg))
            for arm,key,title in [('original','proxy','30k proxy'),('baseline','proxy','137k retained proxy'),
                                  ('original','image','30k fixed hatching'),('baseline','image','137k fixed hatching')]:
                items.append((title,Image.open(unit/f'renders/static_{arm}/frame_{i:03d}_{key}.png')))
        contact(out/f'simplification_{label}_views.png',items,cols=5,size=384,
                title='Ficus | same qualified depths, TSDF, height rule, styles, cameras | face budget only')
    js(unit/'metrics/SIMPLIFICATION_COMPARISON.json',result)
    print(json.dumps({k:{x:v for x,v in a.items() if x not in ('frames','regions')} for k,a in result['arms'].items()}))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',required=True,type=Path)
    ap.add_argument('phase',choices=['freeze','test-fuse','invalid-budgets','compare'])
    a=ap.parse_args()
    {'freeze':freeze,'test-fuse':test_fuse,'invalid-budgets':invalid_budgets,'compare':compare}[a.phase](a.unit)
