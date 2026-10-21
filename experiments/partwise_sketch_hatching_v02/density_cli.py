"""Stem-only nested density editing of the explicit selected458 GT lamp.

Density is an absolute seed-budget fraction of the original48 short axial paths,
not geometric spacing. Re-selection consumes the saved original asset, never a
previously thinned subset. No target path regeneration or ink compensation.
"""
import time
PROCESS_ENTRY=time.perf_counter()
from common import *
import argparse,copy,math,shutil
from PIL import Image
from asset_cli import load_asset,validate_azimuths
from direction_cli import revision,bound_file
from renderer import render
UNIT=OUT.parent/'unit_009'
VIEWS=[30,120,210,300]

def density_value(value):
    if isinstance(value,(bool,np.bool_)):raise ValueError('density must be a real fraction, not bool')
    value=float(value)
    if not math.isfinite(value) or not 0<=value<=1:raise ValueError('density must be finite in [0,1]')
    return value

def destination(value):
    path=Path(value).resolve()
    if path==UNIT or not path.is_relative_to(UNIT):raise ValueError('output must be below authorized unit009')
    if path.exists():raise FileExistsError(path)
    return path

def select_stem(mesh,strokes,cfg,density):
    start=time.perf_counter();density=density_value(density)
    if cfg['seed']!=1729 or cfg['strokes']['counts_by_part']['2']!=48:
        raise ValueError('original48-seed1729 stem domain required')
    target=[s for s in strokes if s['part']==2]
    expected=[f'p2:seed{i:04d}:layer0' for i in range(48)]
    if len(target)!=48 or sorted(s['id'] for s in target)!=expected:
        raise ValueError('all original48 unique stem IDs required')
    if len(set(s['id'] for s in strokes))!=len(strokes):raise ValueError('duplicate stroke IDs')
    byid={s['id']:s for s in target};rng=np.random.default_rng(np.random.SeedSequence([1729,2]))
    faces=np.flatnonzero(mesh['parts']==2);prob=mesh['areas'][faces]/mesh['areas'][faces].sum()
    positions=[]
    for sid in expected:
        face=int(rng.choice(faces,p=prob));q=rng.random(2);sq=np.sqrt(q[0]);bary=np.array([1-sq,sq*(1-q[1]),sq*q[1]])
        s=byid[sid]
        if not np.any((s['faces']==face)&np.all(np.abs(s['bary']-bary)<=1e-12,axis=1)):
            raise ValueError('source seed/anchor mismatch: '+sid)
        positions.append(bary@mesh['tri'][face])
    positions=np.asarray(positions);available=np.ones(48,bool);nearest=np.full(48,np.inf);order=[]
    for _ in expected:
        i=int(np.argmax(np.where(available,nearest,-np.inf)))
        order.append(expected[i]);available[i]=False
        nearest=np.minimum(nearest,np.sum((positions-positions[i])**2,axis=1))
    count=int(math.floor(48*density+.5));selected=set(order[:count])
    output=[s for s in strokes if s['part']!=2 or s['id'] in selected]
    return output,dict(density=density,available_stem_paths=48,selected_stem_paths=count,ordered_stem_ids=order,
        selected_stem_ids=sorted(selected),seed_positions=dict(zip(expected,positions)),selection_seconds=time.perf_counter()-start,
        algorithm='Euclidean farthest seed; lexical seed0000 first; lexical tie break; nested prefix',
        limitation='Seed-budget density only; no geodesic/whole-curve spacing guarantee; retained inks unscaled')

def recipe_sources(path):
    path=Path(path).resolve(strict=True);recipe=json.loads(path.read_text())
    if recipe.get('schema')!='stem_density_recipe_v1' or recipe.get('part')!=2:raise ValueError('invalid stem density recipe')
    if recipe['selector_sha256']!=sha(Path(__file__)):raise ValueError('selector SHA mismatch')
    if recipe['numpy_version']!=np.__version__:raise ValueError('NumPy version mismatch')
    files={k:bound_file(path.parent,recipe[k]) for k in ('mesh','source_strokes','config')}
    with np.load(files['mesh'],allow_pickle=False) as a:mesh=core.finalize_mesh(a['vertices'],a['faces'],a['parts'])
    source_strokes=load_strokes(files['source_strokes']);cfg=json.loads(files['config'].read_text())
    if cfg.get('density_by_part')!={'2':density_value(recipe['density'])}:raise ValueError('recipe/config density mismatch')
    if revision(source_strokes)!=recipe['lineage']['source_revision']:raise ValueError('source revision mismatch')
    if {p:sum(s['part']==p for s in source_strokes) for p in (1,2,3)}!={1:260,2:48,3:150}:raise ValueError('source must be complete458 asset')
    return recipe,files,mesh,source_strokes,cfg

def execute(args):
    output=destination(args.output);views=validate_azimuths(args.azimuths);recipe=None;selection=None;source_strokes=None
    if args.operation=='reselect':
        source=Path(args.recipe).resolve();recipe,files,mesh,source_strokes,cfg=recipe_sources(source)
        meshfile=files['mesh'];strokes,selection=select_stem(mesh,source_strokes,cfg,recipe['density']);manifest=copy.deepcopy(recipe['baseline_manifest'])
        if revision(strokes)!=recipe['lineage']['selected_revision'] or selection['ordered_stem_ids']!=recipe['selection']['ordered_stem_ids']:
            raise ValueError('cold re-selection differs from declared recipe')
    else:
        source=(Path(args.bundle)/'asset.json' if args.operation=='replay' else Path(args.asset)).resolve()
        manifest,files,mesh,strokes,cfg=load_asset(source);meshfile=files['mesh']
        if args.operation=='edit':
            if args.part!='stem':raise ValueError('this operation supports stem only')
            if {p:sum(s['part']==p for s in strokes) for p in (1,2,3)}!={1:260,2:48,3:150}:raise ValueError('explicit original458 asset required')
            if sha(meshfile)!='f8de0de7f1b8199dd3a8e3c1045dddaebc1a71a9419d8625665c17ce869a9d08':raise ValueError('frozen lamp mesh required')
            density=density_value(args.density);source_strokes=strokes
            strokes,selection=select_stem(mesh,source_strokes,cfg,density);cfg=copy.deepcopy(cfg);cfg['density_by_part']={'2':density}
            recipe=dict(schema='stem_density_recipe_v1',part=2,density=density,original_count=48,selected_count=selection['selected_stem_paths'],
                selector_sha256=sha(Path(__file__)),numpy_version=np.__version__,baseline_manifest=copy.deepcopy(manifest),
                selection={k:v for k,v in selection.items() if k!='selection_seconds'},
                semantics='Absolute fraction of original48 source paths; not cumulative thinning, geometric spacing, LOD or regenerated paths',
                lineage=dict(parent_asset_sha256=sha(source),parent_strokes_sha256=sha(files['strokes']),source_revision=revision(source_strokes),
                    selected_revision=revision(strokes),non_target_revision=revision([s for s in source_strokes if s['part']!=2])))
        elif args.operation=='replay' and 'recipe' in manifest:
            rp=bound_file(source.parent,manifest['recipe']);recipe,_,_,source_strokes,_=recipe_sources(rp)
    record=dict(operation=args.operation,source=str(source),source_sha256=sha(source),regenerated_parts=[],selection_parts=[2] if selection else [],
        selection_seconds=selection['selection_seconds'] if selection else 0.,saved_path_count=len(strokes),
        counts_by_part={str(p):sum(s['part']==p for s in strokes) for p in (1,2,3)},density=cfg.get('density_by_part',{}).get('2',1.),
        per_view_seconds={},timing_scope='module entry includes imports, load/hash, selection, save, CPU render; external receipt includes interpreter startup',
        inherited_verdict=manifest['verdict_metadata'],promotion='NONE; fullvisual NO_GO retained')
    output.mkdir(parents=True)
    try:
        shutil.copyfile(meshfile,output/'mesh.npz');core.save_strokes(output/'strokes.npz',strokes);write_json(output/'config.json',cfg)
        bundled=copy.deepcopy(manifest);bundled['name']='selected458_stem_density'+str(record['density'])
        for k in ('mesh','strokes','config'):
            filename=k+('.json' if k=='config' else '.npz');bundled[k]=dict(path=filename,sha256=sha(output/filename))
        if recipe is not None:
            core.save_strokes(output/'source_strokes.npz',source_strokes)
            for k,filename in (('mesh','mesh.npz'),('source_strokes','source_strokes.npz'),('config','config.json')):
                recipe[k]=dict(path=filename,sha256=sha(output/filename))
            write_json(output/'recipe.json',recipe);bundled['recipe']=dict(path='recipe.json',sha256=sha(output/'recipe.json'))
            bundled['path_lineage']=recipe['lineage'];record['lineage']=recipe['lineage']
        write_json(output/'asset.json',bundled)
        if selection is not None:write_json(output/'SELECTION.json',selection)
        folder=output/'renders';folder.mkdir()
        for i,az in enumerate(views):
            start=time.perf_counter();result=render(mesh,strokes,cfg,azimuth=az,elevation=20,distance=4.5);seconds=time.perf_counter()-start;prefix=folder/f'{az:03}'
            Image.fromarray(np.uint8(np.rint(result['image']*255))).save(prefix.with_suffix('.png'))
            if i==0:record['command_to_first_preview_seconds']=time.perf_counter()-PROCESS_ENTRY
            np.savez_compressed(prefix.with_suffix('.npz'),**{k:result[k] for k in ('image','hatch','contours','rings','depth','parts')})
            write_json(prefix.with_suffix('.json'),dict(camera=result['camera'],diagnostics=result['diagnostics'],render_seconds=seconds))
            record['per_view_seconds'][str(az)]=seconds
        record['command_to_all_previews_seconds']=time.perf_counter()-PROCESS_ENTRY
        write_json(output/'EDIT.json',record);return record
    except Exception as error:
        write_json(output/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),partial_outputs_retained=True));raise

def parser():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='operation',required=True)
    for name in ('preview','edit','reselect','replay'):
        p=sub.add_parser(name)
        if name=='reselect':p.add_argument('--recipe',required=True)
        elif name=='replay':p.add_argument('--bundle',required=True)
        else:p.add_argument('--asset',required=True)
        p.add_argument('--output',required=True);p.add_argument('--azimuths',nargs='+',type=int,default=VIEWS)
        if name=='edit':p.add_argument('--part',choices=['stem'],required=True);p.add_argument('--density',type=float,required=True)
    return ap

def main():
    try:record=execute(parser().parse_args())
    except Exception as error:
        print(json.dumps(dict(error_type=type(error).__name__,message=str(error))),file=sys.stderr);return 1
    print(json.dumps(native(record),allow_nan=False));return 0
if __name__=='__main__':raise SystemExit(main())
