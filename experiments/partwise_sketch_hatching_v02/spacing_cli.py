"""One frozen, band-preserving shade seed placement on the complete GT lamp.

The metric is a periodic anisotropic parameter-space heuristic, not geodesic
curve spacing. Original ID inks are deliberately retained after relocation.
"""
import time
PROCESS_ENTRY = time.perf_counter()
from common import *
import argparse, copy, shutil
from PIL import Image
from asset_cli import load_asset, validate_azimuths
from length_cli import revision, bound_file, detached_manifest, MESH_SHA256
from renderer import render

UNIT = OUT.parent / 'unit_011'
SCHEMA = 'shade_spacing_recipe_v1'
METHOD = 'band_anisotropic_farthest_v1'
BASELINE_CONFIG_SHA256 = '0c94581eac323cd00886040de75d87f4ab746a106adb5e316702f7881252ace9'
VIEWS = [30, 120, 210, 300]
PROFILE = np.array([[.85,1.4],[.52,2.35],[.485,2.35],[.815,1.4],[.85,1.4]])
PLACEMENT = dict(method=METHOD, candidate_multiplier=64, minimum_candidates=256,
    rng_entropy=[1729,11], circumferential_scale_world=.32,
    transverse_scale_world=.08, initial='nearest(theta=0,profile_t=.5)',
    tie='lowest_candidate_index', band_names=['outer','top_rim','inner','bottom_rim'])

def destination(value):
    path = Path(value).resolve()
    if path == UNIT or not path.is_relative_to(UNIT):
        raise ValueError('output must be a new directory below authorized unit011')
    if path.exists(): raise FileExistsError(path)
    return path

def generator_hashes():
    here = Path(__file__).resolve().parent
    files = {n:here/n for n in ('spacing_cli.py','length_cli.py','common.py','asset_cli.py','renderer.py')}
    files.update({'legacy/'+n:LEGACY/n for n in ('core.py','core_walk_v2.py')})
    return {n:sha(p) for n,p in files.items()}

def face_bands(mesh):
    """Match every triangle's vertex rings to one authored profile segment."""
    result = np.full(len(mesh['faces']), -1, np.int32)
    for face in np.flatnonzero(mesh['parts']==1):
        tri = mesh['tri'][face]
        ry = np.stack((np.hypot(tri[:,0],tri[:,2]),tri[:,1]),axis=1)
        hits = []
        for band in range(4):
            distance = np.linalg.norm(ry[:,None,:]-PROFILE[None,band:band+2,:],axis=2)
            if np.all(distance.min(axis=1)<1e-9) and set(distance.argmin(axis=1))=={0,1}:
                hits.append(band)
        if len(hits)!=1: raise ValueError('shade triangle does not identify one profile band')
        result[face]=hits[0]
    return result

def original_seeds(mesh):
    rng=np.random.default_rng(np.random.SeedSequence([1729,1]))
    faces=np.flatnonzero(mesh['parts']==1);prob=mesh['areas'][faces];prob=prob/prob.sum()
    bands=face_bands(mesh)
    rows=[]
    for index in range(260):
        face=int(rng.choice(faces,p=prob));q=rng.random(2);sq=np.sqrt(q[0])
        rows.append(dict(id=f'p1:seed{index:04d}:layer0',face=face,
            bary=np.array([1-sq,sq*(1-q[1]),sq*q[1]]),band=int(bands[face])))
    return rows

def band_candidates(mesh, band, count):
    bands=face_bands(mesh);faces=np.flatnonzero(bands==band)
    prob=mesh['areas'][faces];prob=prob/prob.sum()
    rng=np.random.default_rng(np.random.SeedSequence([1729,11,band]))
    n=max(256,64*count);sample_faces=[];barys=[]
    for _ in range(n):
        face=int(rng.choice(faces,p=prob));q=rng.random(2);sq=np.sqrt(q[0])
        sample_faces.append(face);barys.append([1-sq,sq*(1-q[1]),sq*q[1]])
    sample_faces=np.asarray(sample_faces,np.int32);barys=np.asarray(barys)
    points=np.einsum('ni,nij->nj',barys,mesh['tri'][sample_faces])
    theta=np.mod(np.arctan2(points[:,2],points[:,0]),2*np.pi)
    # Barycentric profile fraction follows the actual mesh surface, without
    # mapping a radial point to the nearby opposite wall.
    tri=mesh['tri'][sample_faces]
    vry=np.stack((np.hypot(tri[:,:,0],tri[:,:,2]),tri[:,:,1]),axis=2)
    ab=PROFILE[band+1]-PROFILE[band]
    vertex_t=np.einsum('nki,i->nk',vry-PROFILE[band],ab)/(ab@ab)
    t=(barys*vertex_t).sum(axis=1)
    return sample_faces,barys,theta,t

def select_band(mesh, band, count):
    if count==0: return []
    faces,barys,theta,t=band_candidates(mesh,band,count)
    rmid=float(PROFILE[band:band+2,0].mean());arc=float(np.linalg.norm(PROFILE[band+1]-PROFILE[band]))
    def distances(a,b):
        dtheta=np.abs(theta-a);dtheta=np.minimum(dtheta,2*np.pi-dtheta)
        return (rmid*dtheta/.32)**2+(arc*(t-b)/.08)**2
    selected=[];nearest=np.full(len(faces),np.inf)
    index=int(np.argmin(distances(0.,.5)))
    for _ in range(count):
        selected.append(index)
        nearest=np.minimum(nearest,distances(theta[index],t[index]));nearest[selected]=-1.
        index=int(np.argmax(nearest))
    return [dict(candidate_index=int(i),face=int(faces[i]),bary=barys[i].copy(),
        theta=float(theta[i]),profile_t=float(t[i]),band=band) for i in selected]

def validate_recipe(recipe):
    if (recipe.get('schema')!=SCHEMA or recipe.get('part')!=1
        or recipe.get('style')!='mixed' or recipe.get('placement')!=PLACEMENT
        or recipe.get('count')!=260 or recipe.get('length_world')!=.32
        or recipe.get('step_world')!=.015 or recipe.get('angle_deg')!=0.
        or recipe.get('seed')!=1729): raise ValueError('recipe outside frozen shade spacing domain')
    if recipe.get('generator_sha256')!=generator_hashes(): raise ValueError('generator SHA mismatch')
    if recipe.get('numpy_version')!=np.__version__: raise ValueError('NumPy version mismatch')
    config_bytes=(json.dumps(native(recipe.get('baseline_config')),indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if hashlib.sha256(config_bytes).hexdigest()!=BASELINE_CONFIG_SHA256: raise ValueError('baseline config outside frozen domain')
    rows=recipe.get('original_seed_identity',[])
    expected={f'p1:seed{i:04d}:layer0' for i in range(260)}
    if len(rows)!=260 or {r['id'] for r in rows}!=expected: raise ValueError('original 260 IDs required')
    if any(type(r['band']) is not int or r['band'] not in range(4)
        or isinstance(r['ink'],bool) or not np.isfinite(r['ink']) or not 0<=r['ink']<=1 for r in rows):
        raise ValueError('invalid band or fixed ink')

def make_recipe(manifest,files,mesh,strokes,cfg,source):
    if (sha(files['mesh'])!=MESH_SHA256 or sha(files['config'])!=BASELINE_CONFIG_SHA256
        or len({s['id'] for s in strokes})!=434
        or {p:sum(s['part']==p for s in strokes) for p in (1,2,3)}!={1:260,2:24,3:150}):
        raise ValueError('named434 GT lamp required')
    if (cfg['seed']!=1729 or cfg['strokes']['length_by_part']['1']!=.32
        or cfg['strokes']['length_by_part']['3']!=.12 or cfg['strokes']['step_world']!=.015
        or cfg.get('direction_by_part',{}).get('1',0.)!=0.): raise ValueError('wrong generator controls')
    target={s['id']:s for s in strokes if s['part']==1};rows=[]
    for seed in original_seeds(mesh):
        s=target[seed['id']]
        if not np.any((s['faces']==seed['face']) & np.all(np.abs(s['bary']-seed['bary'])<=1e-12,axis=1)):
            raise ValueError('original seed anchor missing')
        rows.append(dict(id=seed['id'],band=seed['band'],ink=s['ink']))
    metadata=detached_manifest(manifest)
    for key in ('mesh','strokes','config'): metadata.pop(key,None)
    return dict(schema=SCHEMA,part=1,style='mixed',seed=1729,count=260,length_world=.32,
        step_world=.015,angle_deg=0.,placement=copy.deepcopy(PLACEMENT),
        original_seed_identity=rows,generator_sha256=generator_hashes(),numpy_version=np.__version__,
        baseline_manifest=metadata,baseline_config=copy.deepcopy(cfg),
        ink_policy='retain original per-ID assigned ink; no normal/light recalculation',
        lineage=dict(parent_asset_sha256=sha(source),parent_strokes_sha256=sha(files['strokes']),
            parent_target_revision=revision(list(target.values())),
            non_target_revision=revision([s for s in strokes if s['part']!=1]),
            target_identity='Original seed IDs retained; all relocated targets are NEW geometry revisions'))

def generate(mesh,recipe):
    validate_recipe(recipe);bands=face_bands(mesh)
    original={r['id']:r['band'] for r in original_seeds(mesh)}
    if any(original[r['id']]!=r['band'] for r in recipe['original_seed_identity']):
        raise ValueError('original seed band identity mismatch')
    strokes=[]
    for band in range(4):
        identities=sorted((r for r in recipe['original_seed_identity'] if r['band']==band),key=lambda r:r['id'])
        for identity,seed in zip(identities,select_band(mesh,band,len(identities))):
            audits=[{},{}];face=seed['face'];bary=seed['bary']
            fa,ba=walker.walk(mesh,face,bary,1,'mixed',0,0.,.16,.015,-1,audits[0])
            fb,bb=walker.walk(mesh,face,bary,1,'mixed',0,0.,.16,.015,1,audits[1])
            faces=np.asarray(fa[::-1]+fb[1:],np.int32)
            strokes.append(dict(id=identity['id'],part=1,style='mixed',angle=0.,layer=0,
                faces=faces,bary=np.asarray(ba[::-1]+bb[1:]),ink=float(identity['ink']),
                seed_face=face,seed_bary=bary.copy(),seed_metadata=seed,walk_audit=audits,
                seed_band=band,path_bands=sorted(set(map(int,bands[faces])))))
    return sorted(strokes,key=lambda s:s['id'])

def read_recipe(path):
    path=Path(path).resolve(strict=True);recipe=json.loads(path.read_text());validate_recipe(recipe)
    files={k:bound_file(path.parent,recipe[k]) for k in ('mesh','retained','config')}
    if sha(files['mesh'])!=MESH_SHA256: raise ValueError('wrong mesh SHA')
    with np.load(files['mesh'],allow_pickle=False) as a: mesh=core.finalize_mesh(a['vertices'],a['faces'],a['parts'])
    kept=load_strokes(files['retained']);cfg=json.loads(files['config'].read_text())
    if ({p:sum(s['part']==p for s in kept) for p in (1,2,3)}!={1:0,2:24,3:150}
        or revision(kept)!=recipe['lineage']['non_target_revision']): raise ValueError('retained174 mismatch')
    expected=copy.deepcopy(recipe['baseline_config']);expected['seed_placement_by_part']={'1':METHOD}
    if cfg!=expected: raise ValueError('config changed outside shade seed placement')
    return recipe,files,mesh,kept,cfg

def execute(args):
    output=destination(args.output);views=validate_azimuths(args.azimuths);output.mkdir(parents=True)
    try: return execute_new(args,output,views)
    except Exception as error:
        write_json(output/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),partial_outputs_retained=True))
        raise

def execute_new(args,output,views):
    recipe=None;seconds=0.;generated=[];shade=[]
    if args.operation=='regenerate':
        source=Path(args.recipe).resolve();recipe,files,mesh,kept,cfg=read_recipe(source)
        start=time.perf_counter();shade=generate(mesh,recipe);seconds=time.perf_counter()-start
        if revision(shade)!=recipe['lineage']['target_path_revision']: raise ValueError('target revision mismatch')
        strokes=sorted(kept+shade,key=lambda s:s['id']);manifest=recipe['baseline_manifest'];generated=[1]
    else:
        source=(Path(args.bundle)/'asset.json' if args.operation=='replay' else Path(args.asset)).resolve()
        manifest,files,mesh,strokes,cfg=load_asset(source);kept=[s for s in strokes if s['part']!=1]
        if args.operation=='edit':
            recipe=make_recipe(manifest,files,mesh,strokes,cfg,source)
            start=time.perf_counter();shade=generate(mesh,recipe);seconds=time.perf_counter()-start
            recipe['lineage']['target_path_revision']=revision(shade)
            strokes=sorted(kept+shade,key=lambda s:s['id']);generated=[1]
            cfg=copy.deepcopy(cfg);cfg['seed_placement_by_part']={'1':METHOD}
        elif args.operation=='replay' and 'recipe' in manifest:
            recipe,rfiles,_,rkept,rcfg=read_recipe(bound_file(source.parent,manifest['recipe']))
            if cfg!=rcfg or revision(kept)!=revision(rkept) or revision([s for s in strokes if s['part']==1])!=recipe['lineage']['target_path_revision']:
                raise ValueError('saved bundle and recipe disagree')
    shutil.copyfile(files['mesh'],output/'mesh.npz');core.save_strokes(output/'strokes.npz',strokes)
    write_json(output/'config.json',cfg);bundle=detached_manifest(manifest)
    bundle['name']='selected434_'+(METHOD if recipe else 'original_shade_seeds')
    for key in ('mesh','strokes','config'):
        name=key+('.json' if key=='config' else '.npz');bundle[key]=dict(path=name,sha256=sha(output/name))
    if recipe:
        core.save_strokes(output/'retained.npz',kept)
        for key,name in [('mesh','mesh.npz'),('retained','retained.npz'),('config','config.json')]:
            recipe[key]=dict(path=name,sha256=sha(output/name))
        write_json(output/'recipe.json',recipe);bundle['recipe']=dict(path='recipe.json',sha256=sha(output/'recipe.json'))
        bundle['path_lineage']=recipe['lineage']
    bundle['operation_metadata']=dict(operation=args.operation,generated_parts=generated,retained_non_target_count=len(kept),promotion='NONE')
    write_json(output/'asset.json',bundle)
    if shade:
        write_json(output/'SEED_AUDIT.json',dict(strokes=[{k:s[k] for k in ('id','seed_face','seed_bary','seed_metadata','seed_band','path_bands','walk_audit')} for s in shade],
            crossing_ids=[s['id'] for s in shade if s['path_bands']!=[s['seed_band']]],
            original_band_counts={str(b):sum(r['band']==b for r in recipe['original_seed_identity']) for b in range(4)}))
    record=dict(operation=args.operation,source=str(source),source_sha256=sha(source),regenerated_parts=generated,
        regeneration_seconds=seconds,regenerated_path_count=260 if generated else 0,saved_path_count=len(strokes),
        counts_by_part={str(p):sum(s['part']==p for s in strokes) for p in (1,2,3)},per_view_seconds={},
        timing_scope='module entry through import, hashes, load, placement, walk, save and render; external receipt includes startup')
    (output/'renders').mkdir()
    for index,az in enumerate(views):
        start=time.perf_counter();r=render(mesh,strokes,cfg,azimuth=az,elevation=20,distance=4.5)
        record['per_view_seconds'][str(az)]=time.perf_counter()-start;prefix=output/'renders'/f'{az:03}'
        Image.fromarray(np.uint8(np.rint(r['image']*255))).save(prefix.with_suffix('.png'))
        np.savez_compressed(prefix.with_suffix('.npz'),**{k:r[k] for k in ('image','hatch','contours','rings','depth','parts')})
        write_json(prefix.with_suffix('.json'),dict(camera=r['camera'],diagnostics=r['diagnostics'],render_seconds=record['per_view_seconds'][str(az)]))
        if index==0:record['command_to_first_preview_seconds']=time.perf_counter()-PROCESS_ENTRY
    record['command_to_all_previews_seconds']=time.perf_counter()-PROCESS_ENTRY
    write_json(output/'EDIT.json',record);return record

def parser():
    ap=argparse.ArgumentParser(description=__doc__);commands=ap.add_subparsers(dest='operation',required=True)
    for name in ('preview','edit','regenerate','replay'):
        p=commands.add_parser(name)
        p.add_argument('--recipe' if name=='regenerate' else '--bundle' if name=='replay' else '--asset',required=True)
        p.add_argument('--output',required=True);p.add_argument('--azimuths',type=int,nargs='+',default=VIEWS)
        if name=='edit':p.add_argument('--part',choices=['shade'],required=True)
    return ap

def main():
    try: result=execute(parser().parse_args())
    except Exception as error:
        print(json.dumps(dict(error_type=type(error).__name__,message=str(error))),file=sys.stderr);return 1
    print(json.dumps(native(result),allow_nan=False));return 0
if __name__=='__main__':raise SystemExit(main())
