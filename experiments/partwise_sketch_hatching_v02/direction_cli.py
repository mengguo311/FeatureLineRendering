"""Explicit complete-asset shade direction editing, recipe regeneration and replay.

Angles are absolute offsets from the authored circumferential shade field.
Only unit008 new output directories are authorized. Retained paths are assets,
not generated from obsolete whole-object seed counts.
"""
import time
PROCESS_ENTRY=time.perf_counter()
from common import *
import argparse,copy,math,shutil
from PIL import Image
from asset_cli import load_asset, validate_azimuths
from renderer import render
UNIT=OUT.parent/'unit_008'
VIEWS=[30,120,210,300]

def angle_value(value):
    value=float(value)
    if not math.isfinite(value) or not -45<=value<=45:
        raise ValueError('angle must be a finite absolute offset in [-45,45] degrees')
    return value

def destination(value):
    path=Path(value).resolve()
    if not path.is_relative_to(UNIT) or path==UNIT:raise ValueError('output must be below authorized unit008')
    if path.exists():raise FileExistsError(path)
    return path

def revision(strokes):
    h=hashlib.sha256()
    for s in sorted(strokes,key=lambda x:x['id']):
        h.update(s['id'].encode());h.update(np.asarray([s['part']],np.int64).tobytes())
        h.update(np.asarray([s['ink']],np.float64).tobytes())
        h.update(np.asarray(s['faces'],np.int32).tobytes());h.update(np.asarray(s['bary'],np.float64).tobytes())
    return h.hexdigest()

def generator_hashes():
    return {name:sha(LEGACY/name) for name in ('core.py','core_walk_v2.py')}

def generate(mesh,recipe):
    if recipe['schema']!='shade_direction_recipe_v1' or recipe['part']!=1 or recipe['style']!='mixed':
        raise ValueError('unsupported shade recipe')
    if recipe['generator_sha256']!=generator_hashes():raise ValueError('generator SHA mismatch')
    if recipe.get('numpy_version',np.__version__)!=np.__version__:raise ValueError('recipe NumPy version mismatch')
    angle=angle_value(recipe['angle_deg'])
    if recipe['count']!=260 or recipe['seed']!=1729 or recipe['length_world']!=.32 or recipe['step_world']!=.015:
        raise ValueError('recipe outside frozen selected458 generator domain')
    cfg=dict(seed=recipe['seed'],strokes=dict(counts_by_part={'1':recipe['count']},length_by_part={'1':recipe['length_world']},step_world=recipe['step_world']))
    return walker.generate_strokes(mesh,cfg,'mixed',only_part=1,angle=angle,counts={'1':recipe['count']})

def bound_file(base,item):
    path=Path(item['path'])
    if not path.is_absolute():path=base/path
    path=path.resolve(strict=True)
    if sha(path)!=item['sha256']:raise ValueError('recipe dependency SHA mismatch')
    return path

def read_recipe(path):
    path=Path(path).resolve(strict=True);recipe=json.loads(path.read_text())
    if recipe.get('schema')!='shade_direction_recipe_v1':raise ValueError('invalid recipe schema')
    files={k:bound_file(path.parent,recipe[k]) for k in ('mesh','retained','config')}
    with np.load(files['mesh'],allow_pickle=False) as a:mesh=core.finalize_mesh(a['vertices'],a['faces'],a['parts'])
    kept=load_strokes(files['retained'])
    if len(kept)!=198 or {p:sum(s['part']==p for s in kept) for p in (2,3)}!={2:48,3:150}:
        raise ValueError('retained asset must contain only48stem and150selectedbase paths')
    if revision(kept)!=recipe['lineage']['non_target_revision']:raise ValueError('retained revision mismatch')
    cfg=json.loads(files['config'].read_text())
    if cfg.get('direction_by_part')!={'1':recipe['angle_deg']}:raise ValueError('recipe/config angle mismatch')
    return recipe,files,mesh,kept,cfg

def execute(args):
    output=destination(args.output);views=validate_azimuths(args.azimuths)
    recipe=None;regen=[];regen_seconds=0.;source=None
    if args.operation=='regenerate':
        source=Path(args.recipe).resolve();recipe,files,mesh,kept,cfg=read_recipe(source)
        start=time.perf_counter();shade=generate(mesh,recipe);regen_seconds=time.perf_counter()-start;regen=[1]
        if revision(shade)!=recipe['lineage']['target_path_revision']:raise ValueError('regenerated target revision mismatch')
        strokes=sorted(kept+shade,key=lambda s:s['id']);manifest=copy.deepcopy(recipe['baseline_manifest'])
        meshfile=files['mesh']
    else:
        source=(Path(args.bundle)/'asset.json' if args.operation=='replay' else Path(args.asset)).resolve()
        manifest,files,mesh,strokes,cfg=load_asset(source);meshfile=files['mesh'];kept=[s for s in strokes if s['part']!=1]
        if args.operation=='edit':
            if args.part!='shade':raise ValueError('this recipe supports shade only')
            angle=angle_value(args.angle_deg)
            if ({p:sum(s['part']==p for s in strokes) for p in (1,2,3)}!={1:260,2:48,3:150}
                    or sha(meshfile)!='f8de0de7f1b8199dd3a8e3c1045dddaebc1a71a9419d8625665c17ce869a9d08'):
                raise ValueError('named selected458 lamp with260shade48stem150base required')
            recipe=dict(schema='shade_direction_recipe_v1',part=1,style='mixed',seed=1729,count=260,length_world=.32,step_world=.015,angle_deg=angle,
                angle_semantics='absolute offset from authored circumferential field; not accumulated delta',generator_sha256=generator_hashes(),numpy_version=np.__version__,
                baseline_manifest=copy.deepcopy(manifest))
            start=time.perf_counter();shade=generate(mesh,recipe);regen_seconds=time.perf_counter()-start;regen=[1]
            recipe['lineage']=dict(parent_asset_sha256=sha(source),parent_strokes_sha256=sha(files['strokes']),target_seed_identity='stroke_id',
                parent_target_revision=revision([s for s in strokes if s['part']==1]),target_path_revision=revision(shade),non_target_revision=revision(kept))
            strokes=sorted(kept+shade,key=lambda s:s['id']);cfg=copy.deepcopy(cfg);cfg['direction_by_part']={'1':angle}
        elif args.operation=='replay' and 'recipe' in manifest:
            recipefile=bound_file(source.parent,manifest['recipe']);recipe=json.loads(recipefile.read_text())
    record=dict(operation=args.operation,source=str(source),source_sha256=sha(source),regenerated_parts=regen,regeneration_seconds=regen_seconds,
        saved_path_count=len(strokes),counts_by_part={str(p):sum(s['part']==p for s in strokes) for p in (1,2,3)},
        angle_deg=cfg.get('direction_by_part',{}).get('1',0.),per_view_seconds={},timing_scope='module entry includes imports, input hashes/loading, regeneration, saving and CPU render; external receipt includes interpreter startup',
        inherited_verdict=manifest['verdict_metadata'],promotion='NONE; inherited visual NO_GO retained')
    output.mkdir(parents=True)
    try:
        shutil.copyfile(meshfile,output/'mesh.npz');core.save_strokes(output/'strokes.npz',strokes);write_json(output/'config.json',cfg)
        bundled=copy.deepcopy(manifest)
        for k in ('mesh','strokes','config'):
            filename=k+('.json' if k=='config' else '.npz');bundled[k]=dict(path=filename,sha256=sha(output/filename))
        if recipe is not None:
            core.save_strokes(output/'retained.npz',kept)
            for k,filename in (('mesh','mesh.npz'),('retained','retained.npz'),('config','config.json')):
                recipe[k]=dict(path=filename,sha256=sha(output/filename))
            write_json(output/'recipe.json',recipe);bundled['recipe']=dict(path='recipe.json',sha256=sha(output/'recipe.json'))
            bundled['path_lineage']=copy.deepcopy(recipe['lineage']);record['lineage']=copy.deepcopy(recipe['lineage'])
        write_json(output/'asset.json',bundled)
        folder=output/'renders';folder.mkdir()
        for i,az in enumerate(views):
            start=time.perf_counter();result=render(mesh,strokes,cfg,azimuth=az,elevation=20,distance=4.5)
            seconds=time.perf_counter()-start;prefix=folder/f'{az:03}'
            Image.fromarray(np.uint8(np.rint(result['image']*255))).save(prefix.with_suffix('.png'))
            if i==0:record['command_to_first_preview_seconds']=time.perf_counter()-PROCESS_ENTRY
            np.savez_compressed(prefix.with_suffix('.npz'),**{k:result[k] for k in ('image','hatch','contours','rings','depth','parts')})
            write_json(prefix.with_suffix('.json'),dict(camera=result['camera'],diagnostics=result['diagnostics'],render_seconds=seconds))
            record['per_view_seconds'][str(az)]=seconds
        record['command_to_all_previews_seconds']=time.perf_counter()-PROCESS_ENTRY
        write_json(output/'EDIT.json',record);return record
    except Exception as e:
        write_json(output/'FAILURE.json',dict(error_type=type(e).__name__,message=str(e),partial_outputs_retained=True));raise

def parser():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='operation',required=True)
    for name in ('preview','edit','regenerate','replay'):
        p=sub.add_parser(name)
        if name=='regenerate':p.add_argument('--recipe',required=True)
        elif name=='replay':p.add_argument('--bundle',required=True)
        else:p.add_argument('--asset',required=True)
        p.add_argument('--output',required=True);p.add_argument('--azimuths',nargs='+',type=int,default=VIEWS)
        if name=='edit':p.add_argument('--part',choices=['shade'],required=True);p.add_argument('--angle-deg',type=float,required=True)
    return ap

def main():
    try:record=execute(parser().parse_args())
    except Exception as e:
        print(json.dumps(dict(error_type=type(e).__name__,message=str(e))),file=sys.stderr);return 1
    print(json.dumps(native(record),allow_nan=False));return 0
if __name__=='__main__':raise SystemExit(main())
