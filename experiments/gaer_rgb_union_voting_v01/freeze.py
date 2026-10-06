"""Freeze exact cached display-ink fields, archival cameras and source bytes."""
import json,math,re,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image
from runtime import *
from binding import boundary,NATIVE

PROTOCOL=dict(schema='mandatory-rgb-union-voting-v1',base='e682614a7fedcb529102f67efcf78f7905d3d519',
    scenes=['lego','chair'],K=8,delta=2.,numerical_D_floor=2e-6,normal_confidence_floor=.22,
    side_rule='unknown_Rminus+Rplus <= largest_center_visible_D + 2e-6; otherwise mandatory center alphaT fallback',
    marked_rule='darkness = 1 - original boundary.ink(union, gain=1, sigma=.5)[...,0]; darkness > .2',
    weak_rule='0 < darkness <= .2; retained independently, not mandatory vote domain',
    vote_views=['r_007','r_033','r_059','r_086','r_000','r_008','r_018','r_030'],
    evaluation_views=['r_001','r_014'],sensitivity_views=['r_007','r_000','r_018','r_030'],sensitivity_K=[16,32],
    ranking='raw pixel frequency desc, distinct-view count desc, original ID asc',
    fixed_budgets=[100,500,2000],main_budget=500,view_thresholds=[2,4,6],
    visualization_views=['r_000','r_008','r_018','r_030'],alpha_foreground_threshold=.5,interior_distance_pixels=4,
    coverage_thresholds=[.1,.5],random_seed=1729,random_mass_log_bin_width=.1,
    fullT_display_gain=6.,frequency_feature_display_gain=8.,
    selected_only='native unmodified original fullSH3 rows; removed rows change transmittance',
    evaluation_scope='historical GS/research-seen cameras; selection holdout only, not formal blind',
    no_training=True,no_new_kernel=True,no_new_primitives=True,no_model_edits=True)

def source_files():return {str(p.relative_to(ROOT)):sha(p) for p in sorted(EXP.rglob('*.py'))}

def make_freeze():
    dest=ART/'PRODUCTION_FREEZE.json'
    if dest.exists():
        frozen=json.loads(dest.read_text())
        if frozen['protocol']!=PROTOCOL or frozen['source_method_files']!=source_files():raise RuntimeError('production method changed after freeze')
        check_protected(frozen,raise_error=True);return frozen
    foundation_path=FOUNDATION/'artifacts/image_space_edge_foundation_v1/PRODUCTION_FREEZE.json'
    foundation=json.loads(foundation_path.read_text())
    data_path=ATTR/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
    data=json.loads(data_path.read_text());scenes={};protected={}
    def protect(p):
        p=Path(p);protected[str(p)]=sha(p)
    protect(foundation_path);protect(data_path)
    for name in PROTOCOL['scenes']:
        d=data['scenes'][name];f=foundation['scenes'][name];model=Path(d['model'])
        protect(model)
        if protected[str(model)]!=f['model_sha256'] or protected[str(model)]!=d['model_sha256']:raise RuntimeError('original model mismatch')
        meta=Path(re.search("source_path='([^']+)'",d['cfg_args'])[1])/'transforms_train.json'
        protect(meta);metadata=json.loads(meta.read_text());protect(d['training_manifest'])
        entries={e['key']:e for values in d['roles'].values() for e in values};votes=[];evals=[]
        for role in ('dev','fixed'):
            for e in f['groups'][role]:
                key=e['key'];c=e['native_camera'];fp=FOUNDATION/f'out/image_space_edge_foundation_v1/{role}_fields/{name}/{key}/fields.npz'
                rp=FOUNDATION/f'out/image_space_edge_foundation_v1/raw/{name}/{role}/{key}/native.npz'
                protect(fp);protect(rp)
                fields=np.load(fp);raw=np.load(rp)
                if fields['union'].shape!=(800,800) or fields['union'].dtype!=np.float32:raise RuntimeError('wrong cached union field')
                ink=1-boundary.ink(fields['union'])[...,0];line=ink>.2
                votes.append(dict(key=key,role=role,camera=c,camera_sha256=digest(c),fields=str(fp),raw=str(rp),
                    fields_sha256=sha(fp),raw_sha256=sha(rp),RGB_float32_sha256=array_sha(raw['rgb']),
                    union_float32_sha256=array_sha(fields['union']),ink_float32_sha256=array_sha(ink),
                    line_binary_sha256=array_sha(line),marked_pixels=int(line.sum()),weak_pixels=int(((ink>0)&~line).sum()),
                    previous_research_seen=True,GS_TRAIN_seen=e['GS_TRAIN_seen']))
                if role=='fixed':
                    png=FOUNDATION/f'artifacts/image_space_edge_foundation_v1/media/{name}/fixed/{key}/detail_union_ink.png';protect(png)
                    expected=np.round(np.clip(boundary.ink(fields['union']),0,1)*255).astype(np.uint8)
                    if not np.array_equal(np.asarray(Image.open(png).convert('RGB')),expected):raise RuntimeError('display union ink mismatch')
        for key in PROTOCOL['evaluation_views']:
            e=entries[key];c=dict(e['camera']);c['width']=c['height']=800
            focal=800/(2*math.tan(c['FoVx']/2));focaly=800/(2*math.tan(c['FoVy']/2))
            c['K']=[[focal,0,399.5],[0,focaly,399.5],[0,0,1]]
            evals.append(dict(key=key,role='selection_holdout',camera=c,camera_sha256=digest(c),
                previous_research_seen=True,GS_TRAIN_seen=True,field_method='exact old analyze frozen config, no retune'))
        # Independently check ALL ten archival RGBA frames and actual metadata.
        extrinsics=[]
        for v in votes+evals:
            c=v['camera'];e=entries[v['key']];matches=[(j,x) for j,x in enumerate(metadata['frames']) if Path(x['file_path']).stem==Path(e['original_path']).stem]
            if len(matches)!=1:raise RuntimeError('camera filename mismatch')
            j,frame=matches[0];c2w=np.asarray(frame['transform_matrix'],np.float64);c2w[:3,1:3]*=-1;actual=np.linalg.inv(c2w)
            err=float(np.abs(actual-np.asarray(c['w2c'])).max())
            if err>1e-10 or abs(float(metadata['camera_angle_x'])-c['FoVx'])>1e-10:raise RuntimeError('metadata camera mismatch')
            path=Path(e['original_path']);protect(path)
            with Image.open(path) as im:
                if im.size!=(800,800) or im.mode!='RGBA':raise RuntimeError('archival frame not 800 RGBA')
            v.update(metadata_index=j,metadata_path=str(meta),original_RGBA=str(path),original_RGBA_sha256=sha(path),metadata_w2c_error=err)
            extrinsics.append(array_sha(np.asarray(c['w2c'],np.float64)))
        if len(set(extrinsics))!=10 or len(votes)!=8:raise RuntimeError('duplicate or missing camera')
        scenes[name]=dict(model=str(model),model_sha256=sha(model),count=f['gaussian_count'],sh_degree=3,vote_views=votes,
            evaluation_views=evals,distinct_extrinsics=10)
    # Track all existing committed bytes in this workspace and read-only old
    # experiment trees, including their dirty reproduction/verification files.
    dirty={}
    for root in (ROOT,FOUNDATION,ATTR,VIEW):
        dirty[str(root)]=subprocess.check_output(['git','status','--short'],cwd=root,text=True)
        files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
        for rel in files:
            if not rel or rel.startswith(('experiments/gaer_rgb_union_voting_v01/','artifacts/gaer_rgb_union_voting_v01/')):continue
            p=root/rel
            if p.is_file():protect(p)
    for p in (NATIVE/'build/stock/onec_stock_C.so',ATTR/'out/gaer_attribution_buffer_v01/torch_extensions/gaer_native_C/gaer_native_C.so',
        ATTR/'out/gaer_attribution_buffer_v01/native/patched/diff_gaussian_rasterization/__init__.py'):protect(p)
    rec=dict(schema='frozen-before-voting',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        start_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),protocol=PROTOCOL,
        foundation_config=foundation['config'],foundation_freeze_sha256=sha(foundation_path),scenes=scenes,
        source_method_files=source_files(),protected_before=protected,old_dirty_status=dirty,
        AGENTS_search='No AGENTS.md found in workspace ancestors or project tree',native_build_reused=True)
    atomic_json(dest,rec);return rec

def check_protected(frozen,raise_error=False):
    after={p:sha(p) for p in frozen['protected_before']};changed=[p for p,h in after.items() if h!=frozen['protected_before'][p]]
    rec=dict(passed=not changed,checked_files=len(after),changed=changed,after=after)
    if changed and raise_error:raise RuntimeError('protected bytes changed: '+str(changed))
    return rec
