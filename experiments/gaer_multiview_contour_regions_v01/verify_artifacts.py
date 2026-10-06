"""Independent delivery audit; never fits geometry or changes scientific verdict.

Run after both scenes finish:
  python experiments/gaer_multiview_contour_regions_v01/verify_artifacts.py
Use --assets-only to audit sealed assets before evaluating reserved cameras.
Missing artifacts remain INCOMPLETE; assertions are INVALID, never NO_GO.
"""
import runtime as rt
import argparse,hashlib,json,re,struct,subprocess,time,traceback
from pathlib import Path
import numpy as np

def need(condition,message):
 if not condition:raise AssertionError(message)

def read_json(path):
 if not Path(path).exists():raise FileNotFoundError(str(path))
 return json.loads(Path(path).read_text())

def checked_seal(unit):
 p=rt.ART/'seals'/(unit+'.json');s=read_json(p)
 need(s['unit']==unit,'seal unit differs')
 for rel,h in s['files'].items():
  q=(rt.ROOT/rel).resolve()
  need(any(q.is_relative_to(r) for r in (rt.ART,rt.EXP,rt.OUT)),'seal escaped stage')
  if not q.exists():raise FileNotFoundError(str(q))
  need(rt.sha(q)==h,'seal content changed: '+rel)
 return s,read_json(rt.ART/'results'/(unit+'.json'))

def geometry_hash(v,f):
 return rt.digest(dict(vertices_sha256=hashlib.sha256(v.tobytes()).hexdigest(),faces_sha256=hashlib.sha256(f.tobytes()).hexdigest()))

def glb_arrays(path):
 b=Path(path).read_bytes();magic,version,size=struct.unpack_from('<III',b)
 need((magic,version,size)==(0x46546c67,2,len(b)),'invalid GLB header')
 off=12;doc=None;binary=None
 while off<len(b):
  length,kind=struct.unpack_from('<II',b,off);off+=8;chunk=b[off:off+length];off+=length
  if kind==0x4e4f534a:doc=json.loads(chunk)
  elif kind==0x004e4942:binary=chunk
 need(doc is not None and binary is not None,'GLB JSON/BIN missing')
 need(len(doc['nodes'])==1 and doc['nodes'][0]['name']=='outer','unexpected GLB layer')
 need(doc['extras']['fixed_geometry'] and not doc['extras']['camera_dependent_update'],'GLB claims dynamic geometry')
 primitive=doc['meshes'][0]['primitives'][0];need(primitive.get('mode',4)==4,'GLB is not triangles')
 def accessor(i):
  a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']]
  need('byteStride' not in v,'unexpected interleaved buffer')
  dtype={5126:'<f4',5125:'<u4'}[a['componentType']];components={'VEC3':3,'SCALAR':1}[a['type']]
  return np.frombuffer(binary,dtype=dtype,count=a['count']*components,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],components)
 return accessor(primitive['attributes']['POSITION']),accessor(primitive['indices']).reshape(-1,3)

def obj_arrays(path):
 vs=[];fs=[];groups=[]
 with Path(path).open() as stream:
  for line in stream:
   p=line.split()
   if not p:continue
   if p[0]=='v':need(len(p)==4,'unexpected OBJ vertex');vs.append([float(x) for x in p[1:]])
   elif p[0]=='f':need(len(p)==4,'OBJ face is not triangle');fs.append([int(x)-1 for x in p[1:]])
   elif p[0]=='g':groups.append(p[1:])
 need(groups==[['outer']],'OBJ layer mismatch')
 return np.asarray(vs,np.float32),np.asarray(fs,np.int32)

def partitions(scene):
 roles=scene['roles'];flat=[]
 for role,count in [('construction',24),('dev',4),('reserved',8)]:
  keys=roles[role];need(len(keys)==count and len(set(keys))==count,role+' view count')
  need(set(keys)<=set(scene['cameras']),role+' absent actual filename');flat+=keys
 need(len(set(flat))==36,'construction/dev/reserved overlap')
 need({'r_7','r_33'}<=set(roles['construction']),'r7/r33 construction contract')
 need({'r_1','r_14'}<=set(roles['reserved']),'r1/r14 reserved contract')
 for k,c in scene['cameras'].items():
  need(Path(c['frame_file']).stem==k,'filename stem mismatch')
  own={x:y for x,y in c.items() if x!='camera_sha256'}
  need(rt.digest(own)==c['camera_sha256'],'frozen camera hash mismatch')
 return dict(construction=24,dev=4,reserved=8,disjoint=True,metadata_cameras=len(scene['cameras']))

def check_scene(name,s,assets_only=False):
 report=dict(partition=partitions(s),arms={});asset_seal,asset=checked_seal(name+'_asset')
 need(asset['status']=='SEALED_FIXED_ASSET','not a unique sealed asset')
 need(asset['model_sha256']==s['model_sha256'],'asset PLY provenance mismatch')
 need(rt.sha(s['model'])==s['model_sha256'],'original model changed')
 need(asset['construction']==s['roles']['construction'] and asset['dev']==s['roles']['dev'],'asset source roles changed')
 need(set(asset['arms'])=={'thin','widened','two_source','multi24'},'four controls missing')
 for arm,record in asset['arms'].items():
  paths={k:rt.ROOT/p for k,p in record['paths'].items()}
  with np.load(paths['npz']) as z:v=z['vertices'];f=z['faces']
  need(v.dtype==np.float32 and f.dtype==np.int32,'unexpected export dtype')
  need(v.ndim==2 and v.shape[1]==3 and f.ndim==2 and f.shape[1]==3 and len(f)>0,'nontriangle/empty asset')
  need(np.isfinite(v).all() and f.min()>=0 and f.max()<len(v),'invalid geometry indices')
  vg,fg=glb_arrays(paths['glb']);vo,fo=obj_arrays(paths['obj'])
  need(np.array_equal(v,vg) and np.array_equal(f,fg),'GLB differs from NPZ')
  need(np.array_equal(v,vo) and np.array_equal(f,fo),'OBJ differs from NPZ')
  canonical_hash=geometry_hash(v,f);hash_schema='SERIALIZED_FLOAT32_INT32'
  if canonical_hash!=record['geometry_sha256']:
   # Historical producer metadata for graph controls hashed pre-export int64
   # indices. Export canonicalizes to int32 without changing index values.
   # Preserve that metadata limitation; never mutate assets or their seals.
   need(arm in ('thin','widened') and geometry_hash(v,f.astype(np.int64))==record['geometry_sha256'],'sealed geometry hash mismatch')
   hash_schema='HASH_SCHEMA_PREEXPORT_INT64'
  need(len(v)==record['vertices'] and len(f)==record['triangles'],'asset dimensions differ')
  need(rt.sha(paths['glb'])==record['glb_sha256'],'GLB file hash differs')
  report['arms'][arm]=dict(vertices=len(v),triangles=len(f),glb_obj_npz_equal=True,geometry_sha256=record['geometry_sha256'],serialized_canonical_hash=canonical_hash,geometry_hash_schema=hash_schema)
  if hash_schema=='HASH_SCHEMA_PREEXPORT_INT64':
   report['arms'][arm]['engineering_limitation']='Primary metadata omitted that graph-control hash uses pre-export int64 indices; exact int64 rehash and all serialized vertex/index values independently verified. No geometry change, primary metadata preserved.'
 source_files=list((rt.ART/'sources'/name).glob('*.npz'))
 need({p.stem for p in source_files}==set(s['roles']['construction']),'source extraction leaked beyond construction or is incomplete')
 for key in s['roles']['construction']:
  _,rec=checked_seal(name+'_extract_'+key)
  need(rec['all_N'] and rec['topK'] is False and rec['N']==s['count'],'source mass is truncated')
  with np.load(rt.ART/'sources'/name/(key+'.npz')) as z:
   need(np.array_equal(z['original_ids'],np.arange(s['count'],dtype=np.int32)),'source original IDs were reindexed')
   need(str(z['role'])=='construction' and str(z['camera_sha256'])==s['cameras'][key]['camera_sha256'],'source role/camera mismatch')
   for k in ['visible_mass','rim_narrow','rim_wide','hole_mass']:
    need(z[k].shape==(s['count'],) and np.isfinite(z[k]).all() and np.min(z[k])>=0,'invalid full-N source '+k)
 for arm in ['two_source','multi24']:
  _,rec=checked_seal(name+'_fusion_'+arm)
  expected=s['roles']['construction'] if arm=='multi24' else s['roles']['construction'][:2]
  need(rec['sources']==expected,'fusion source sequence changed')
  with np.load(rt.ART/'fusion'/name/(arm+'.npz')) as z:
   need(z['views'].tolist()==expected and len(set(z['views'].tolist()))==len(expected),'fusion distinct source mismatch')
   ids=z['selected_ids'];need(len(ids)==len(np.unique(ids)) and ids.min()>=0 and ids.max()<s['count'],'fusion original ID range')
   mass=z['mass'].astype(np.float64);rim=z['raw_participation'].astype(np.float64);relative=np.divide(rim,mass,out=np.zeros_like(rim),where=mass>0)
   valid=(mass>=.1)&(rim>=.01);distinct=(valid&(relative>=.12)).sum(0)
   need(np.array_equal(distinct,z['distinct_views']),'distinct views count is not actual per-source support')
   selected=set(ids.tolist())
  from plyfile import PlyData
  ply=PlyData.read(str(rt.ART/'fusion'/name/(arm+'_kernel_support.ply')))['vertex']
  need(np.array_equal(np.asarray(ply['original_id']),ids),'support PLY original IDs differ')
  develop=read_json(rt.ART/'results'/(name+'_develop.json'))
  region=rt.ROOT/(develop['chosen']['path'] if arm=='multi24' else develop['two_source_path'])
  with np.load(region) as z:
   for key in ['support_ids','vertex_anchor_ids','fill_anchor_ids','fill_witness_ids','merge_ids']:
    values=z[key].reshape(-1);need(set(values.tolist())<=selected,'region lacks selected-ID anchors: '+key)
   offsets=z['fill_witness_offsets'];need(len(offsets)==len(z['fill_grid_indices'])+1 and offsets[0]==0 and offsets[-1]==len(z['fill_witness_ids']) and (np.diff(offsets)>=0).all(),'fill witness CSR invalid')
   for key in ['vertex_displacement','fill_distances','merge_distance']:
    need(np.isfinite(z[key]).all() and (z[key]>=0).all(),'invalid space attribution '+key)
  report['arms'][arm]['selected_original_ids']=len(ids)
 report['sources']=dict(construction_views=24,original_id_range_valid=True,distinct_observation_count_verified=True,region_anchor_ids_verified=True)
 if assets_only:return report
 _,reserved=checked_seal(name+'_reserved_complete');need(reserved['views']==s['roles']['reserved'],'reserved views incomplete')
 for key in s['roles']['reserved']:
  se,re=checked_seal(name+'_eval_'+key)
  need(se['utc']>=asset_seal['utc'],'reserved evaluation preceded asset seal')
  need(re['role']=='reserved' and re['camera_sha256']==s['cameras'][key]['camera_sha256'],'reserved camera contract')
  need(re['geometry_sha256']=={k:a['geometry_sha256'] for k,a in asset['arms'].items()},'geometry changed between reserved views')
 report['reserved']=dict(views=8,seal_precedes_evaluation=True,fixed_geometry=True)
 report['video']=check_video(name,s,asset,asset_seal)
 return report

def check_video(name,s,asset,asset_seal):
 import imageio_ffmpeg
 seal,result=checked_seal(name+'_arc_complete');need(seal['utc']>=asset_seal['utc'],'arc preceded sealed asset')
 folder=rt.ART/'media'/name/'arc';video=folder/'fixed_region_33.mp4';manifest=read_json(video.with_suffix('.manifest.json'))
 need(rt.sha(video)==manifest['sha256'],'video hash differs')
 need(len(s['arc'])==len(manifest['frames'])==manifest['decoded_frames']==manifest['expected_frames']==33,'full 33-frame contract')
 need(manifest['codec']=='h264' and manifest['pixel_format']=='yuv420p' and manifest['full_decode'] and manifest['all_frames_preserved'],'video encoding contract')
 fixed=asset['arms']['multi24']['geometry_sha256'];records=manifest['frames']
 for i,(fr,camera) in enumerate(zip(records,s['arc'])):
  need(fr['index']==i and fr['frame']==i and fr['camera']==camera,'arc actual camera sequence differs')
  need(fr['camera_sha256']==camera['camera_sha256'] and fr['geometry_sha256']==fixed,'arc camera/geometry hash mismatch')
  need(rt.sha(fr['source_png'])==fr['source_png_sha256'],'source arc frame modified')
  se,ar=checked_seal(name+'_arc_'+camera['key'])
  need(se['utc']>=asset_seal['utc'] and ar['geometry_sha256']==fixed and ar['camera_sha256']==camera['camera_sha256'],'arc frame seal inconsistency')
 b=video.read_bytes();atoms={};off=0
 while off+8<=len(b):
  length,kind=struct.unpack_from('>I4s',b,off)
  if length==1:length=struct.unpack_from('>Q',b,off+8)[0]
  if length==0:length=len(b)-off
  need(length>=8 and off+length<=len(b),'invalid MP4 atom');atoms[kind.decode('ascii',errors='replace')]=off;off+=length
 need(atoms.get('moov',len(b))<atoms.get('mdat',-1),'MP4 is not faststart')
 exe=imageio_ffmpeg.get_ffmpeg_exe();command=[exe,'-hide_banner','-loglevel','error','-threads','2','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-']
 proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);framebytes=manifest['width']*manifest['height']*3;decoded=[]
 try:
  while True:
   buffer=bytearray()
   while len(buffer)<framebytes:
    part=proc.stdout.read(framebytes-len(buffer))
    if not part:break
    buffer.extend(part)
   if not buffer:break
   need(len(buffer)==framebytes,'truncated decoded frame');decoded.append(hashlib.sha256(buffer).hexdigest())
  stderr=proc.stderr.read().decode();code=proc.wait();need(code==0,'full decode failed: '+stderr)
 finally:
  if proc.poll() is None:proc.kill();proc.wait()
  proc.stdout.close();proc.stderr.close()
 need(len(decoded)==33,'independent decode lost frames')
 need(decoded==[r['decoded_frame_sha256'] for r in records],'decoded pixel hashes differ from delivered manifest')
 return dict(independent_full_decode=True,decoded_frames=33,geometry_sha256=fixed,video_sha256=manifest['sha256'],faststart_atom_order=True,all_camera_and_geometry_hashes_checked=True)

def protected(freeze):
 checked=0
 for path,expected in freeze['protected_before'].items():
  p=Path(path);need(p.is_relative_to(Path('/home/u00134/3dgs_line')),'unexpected protected path outside experiment family')
  need(rt.sha(p)==expected,'historical protected file changed: '+path);checked+=1
 heads=dict(line.split(' ',1) for line in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],cwd=rt.ROOT,text=True).splitlines())
 current='refs/heads/gaer-multiview-contour-regions-v01';old=freeze['heads_before']
 for branch,h in old.items():
  if branch!=current:need(heads.get(branch)==h,'historical branch changed/deleted: '+branch)
 return dict(protected_file_hashes_checked=checked,all_unchanged=True,historical_branch_heads_checked=len(old)-int(current in old),historical_branch_heads_unchanged=True,new_branch_exempt=current)

def all_primary_seals(freeze,assets_only=False):
 """Traverse every producer seal, including nonselected width/depth inputs."""
 core_names=['runtime.py','contracts.py','cpu_native.py','fusion.py','regions.py','mesh_tools.py','mesh_raster.cpp','metrics.py','media_tools.py','pipeline.py','protocol.py']
 current={name:rt.sha(rt.EXP/name) for name in core_names}
 protocol=read_json(rt.ART/'PROTOCOL.json')
 for name in core_names:
  if name!='mesh_raster.cpp':need(protocol['method_sha256'].get(name)==current[name],'protocol/current method mismatch: '+name)
 mesh_build=read_json(rt.ART/'MESH_RASTER_BUILD.json')
 need(mesh_build['source_sha256']==current['mesh_raster.cpp'],'mesh raster build source stale')
 import cpu_native
 cpp_hash=hashlib.sha256(cpu_native.CPP.encode()).hexdigest()
 for scene in ('lego','chair'):
  for key in ('r_7','r_33'):
   c=read_json(rt.ART/'tdd'/('native_calibration_'+scene+'_'+key+'.json'))
   expected=dict(cpu_native_py_sha256=current['cpu_native.py'],cpp_sha256=cpp_hash,test_cpu_native_py_sha256=rt.sha(rt.EXP/'test_cpu_native.py'))
   need(c['status']=='PASS' and c.get('code_binding')==expected,'CPU calibration code binding stale')
 seal_paths=sorted((rt.ART/'seals').glob('*.json'));need(bool(seal_paths),'no primary seals')
 units={};file_owners={};entries=[];total_references=0
 for path in seal_paths:
  unit=path.stem;s,result=checked_seal(unit)
  need(result.get('method_hashes')==current,'current core method hash differs: '+unit)
  need(s['unit'] not in units,'duplicate primary seal unit');units[unit]=s
  for filename in s['files']:file_owners.setdefault(filename,[]).append(unit)
  total_references+=len(s['files'])
  entries.append(dict(unit=unit,seal_sha256=rt.sha(path),file_hashes_verified=len(s['files']),current_core_methods_equal=True))
 expected_units=set();chains={}
 for name,scene in freeze['scenes'].items():
  roles=scene['roles'];keys=roles['construction']+roles['dev']
  if not assets_only:keys+=roles['reserved']+[c['key'] for c in scene['arc']]
  expected_units.update(name+'_rgb_'+key for key in keys)
  expected_units.update(name+'_extract_'+key for key in roles['construction'])
  expected_units.update(name+'_'+suffix for suffix in ['fusion_two_source','fusion_multi24','develop','asset'])
  if not assets_only:
   expected_units.update(name+'_eval_'+key for key in roles['reserved'])
   expected_units.update(name+'_arc_'+c['key'] for c in scene['arc'])
   expected_units.update(name+'_'+suffix for suffix in ['reserved_complete','arc_complete'])
  for w in protocol['region']['width_candidates_voxels']:expected_units.add(name+'_region_multi24_'+str(w).replace('.','p'))
  dev=read_json(rt.ART/'results'/(name+'_develop.json'));expected_units.add(name+'_region_two_source_'+str(dev['chosen']['width']).replace('.','p'))
  # These are the actual paths read by build_arm, and not merely final exports.
  dependencies=[rt.OUT/'renders'/name/(key+'.npz') for key in roles['construction']]
  dependencies.extend(rt.ART/'sources'/name/(key+'.npz') for key in roles['construction'])
  dependencies.extend(rt.ART/'fusion'/name/(arm+'.npz') for arm in ('two_source','multi24'))
  region_paths=[rt.ART/'regions'/name/('multi24_'+str(w).replace('.','p')+'.npz') for w in protocol['region']['width_candidates_voxels']]
  region_paths.append(rt.ROOT/dev['two_source_path']);dependencies.extend(region_paths)
  dependencies.extend([rt.ART/'INPUT_FREEZE.json',rt.ART/'PROTOCOL.json'])
  need(all(str(p.relative_to(rt.ROOT)) in file_owners for p in dependencies),'unsealed raw-alpha/fusion/region dependency')
  for p in region_paths:
   with np.load(p) as z:
    for key in ['vertices','faces','support_ids','vertex_anchor_ids','fill_witness_offsets','fill_witness_ids','merge_ids','merge_distance','merge_direction','fill_rejected','rejected_first_view']:
     need(key in z.files,'region provenance key missing: '+str(p)+' '+key)
  chains[name]=dict(construction_raw_alpha_files=len(roles['construction']),construction_source_files=len(roles['construction']),fusion_files=2,all_width_region_provenance_files=len(region_paths),all_dependencies_have_verified_seals=True)
 need(expected_units<=set(units),'missing primary producer seals: '+str(sorted(expected_units-set(units))))
 return dict(all_existing_primary_seals_verified=True,seals=len(entries),expected_primary_units=len(expected_units),extra_existing_units=sorted(set(units)-expected_units),file_hash_references=total_references,unique_files=len(file_owners),core_method_hashes=current,dependency_chains=chains,units=entries)

def workspace_scope():
 base='fe3d832';allowed=[f'{prefix}/{rt.TAG}/' for prefix in ('experiments','artifacts','out')]
 def git(*args):return subprocess.check_output(['git',*args],cwd=rt.ROOT)
 base_commit=git('rev-parse',base+'^{commit}').decode().strip()
 branch=git('branch','--show-current').decode().strip();need(branch=='gaer-multiview-contour-regions-v01','not the authorized experiment branch')
 changed=[p.decode() for p in git('diff','--name-only','--no-renames','-z',base,'--').split(b'\0') if p]
 untracked=[p.decode() for p in git('ls-files','--others','--exclude-standard','-z').split(b'\0') if p]
 need(all(any(p.startswith(prefix) for prefix in allowed) for p in changed+untracked),'new branch/workspace diff escaped three authorized scopes')
 # Only this specifically authorized project config is read; no global config,
 # authentication files, process command lines, or SSH configuration are read.
 config=rt.ROOT/'.codex/config.toml';actual=config.read_bytes();original=git('show',base+':.codex/config.toml')
 need(actual==original,'authorized project model config changed since base')
 text=actual.decode();models=re.findall(r'^model\s*=\s*"([^"\n]+)"\s*$',text,re.M);efforts=re.findall(r'^model_reasoning_effort\s*=\s*"([^"\n]+)"\s*$',text,re.M)
 need(models==['gpt-6-astra'] and efforts==['ultra'],'project default is not Astra ultra')
 return dict(base_commit=base_commit,branch=branch,allowed_scopes=allowed,changed_tracked_paths=changed,untracked_path_count=len(untracked),untracked_paths_sha256=rt.digest(sorted(untracked)),all_paths_in_scope=True,project_config_sha256=rt.sha(config),project_config_equal_base=True,model='gpt-6-astra',reasoning_effort='ultra')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--assets-only',action='store_true');args=parser.parse_args()
 report=dict(status='INCOMPLETE',scientific_verdict_unchanged=True,audit_source_sha256=rt.sha(__file__),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),scope='assets_only' if args.assets_only else 'full',checks={},failures=[])
 frozen=read_json(rt.ART/'INPUT_FREEZE.json')
 checks=[('all_primary_seals',lambda:all_primary_seals(frozen,args.assets_only))]+[(name,lambda n=name:check_scene(n,frozen['scenes'][n],args.assets_only)) for name in ['lego','chair']]+[('protected',lambda:protected(frozen)),('workspace_scope',workspace_scope)]
 for name,fn in checks:
  try:report['checks'][name]=fn();print('PASS',name,flush=True)
  except Exception as e:
   report['failures'].append(dict(check=name,kind='INCOMPLETE' if isinstance(e,FileNotFoundError) else 'INVALID',error=repr(e),traceback=traceback.format_exc()));print('FAIL',name,repr(e),flush=True)
 report['status']='PASS' if not report['failures'] else ('INVALID' if any(x['kind']=='INVALID' for x in report['failures']) else 'INCOMPLETE')
 path=rt.ART/'results'/('ARTIFACT_AUDIT_ASSETS.json' if args.assets_only else 'ARTIFACT_AUDIT.json');rt.atomic_json(path,report)
 print(json.dumps(dict(status=report['status'],report=str(path))),flush=True)
 return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
