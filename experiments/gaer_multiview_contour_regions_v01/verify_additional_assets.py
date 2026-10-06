"""Independent numeric/serialization check of the post-protocol ink controls."""
import runtime as rt
import hashlib,json,struct,time,traceback
from pathlib import Path
import numpy as np

def require(ok,message):
 if not ok:raise AssertionError(message)

def gh(v,f):
 return rt.digest(dict(vertices_sha256=hashlib.sha256(v.tobytes()).hexdigest(),faces_sha256=hashlib.sha256(f.tobytes()).hexdigest()))

def check(scene):
 unit=scene+'_post_protocol_dev_ink_diagnostic_asset'
 require(rt.resume(unit),'diagnostic asset seal absent or stale')
 rec=json.loads((rt.ART/'results'/(unit+'.json')).read_text());paths={k:rt.ROOT/p for k,p in rec['paths'].items()}
 with np.load(paths['npz']) as z:v=z['vertices'];f=z['faces']
 require(v.dtype==np.float32 and f.dtype==np.int32,'serialized dtype mismatch')
 require(v.shape[1:]==(3,) and f.shape[1:]==(3,) and len(f)>0,'nontriangle or empty asset')
 require(np.isfinite(v).all() and f.min()>=0 and f.max()<len(v),'invalid vertex/index')
 b=paths['glb'].read_bytes();require(struct.unpack_from('<III',b)==(0x46546c67,2,len(b)),'GLB header mismatch')
 offset=12;doc=None;binary=None
 while offset<len(b):
  length,kind=struct.unpack_from('<II',b,offset);offset+=8
  if kind==0x4e4f534a:doc=json.loads(b[offset:offset+length])
  elif kind==0x004e4942:binary=b[offset:offset+length]
  offset+=length
 require(doc is not None and binary is not None,'missing GLB chunks')
 require(doc['nodes']==[{'mesh':0,'name':'same_A_matched_ink_outer'}],'GLB node differs')
 prim=doc['meshes'][0]['primitives'][0];require(prim['mode']==4,'GLB primitive is not triangle')
 def arr(index):
  a=doc['accessors'][index];bv=doc['bufferViews'][a['bufferView']];require('byteStride' not in bv,'interleaved accessor unexpected')
  c={'VEC3':3,'SCALAR':1}[a['type']];dtype={5126:'<f4',5125:'<u4'}[a['componentType']]
  return np.frombuffer(binary,dtype=dtype,count=c*a['count'],offset=bv.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,c)
 vg=arr(prim['attributes']['POSITION']);fg=arr(prim['indices']).reshape(-1,3)
 vo=[];fo=[];groups=[]
 with paths['obj'].open() as stream:
  for line in stream:
   fields=line.split()
   if not fields:continue
   if fields[0]=='v':require(len(fields)==4,'OBJ vertex shape');vo.append([float(x) for x in fields[1:]])
   elif fields[0]=='f':require(len(fields)==4,'OBJ triangle shape');fo.append([int(x)-1 for x in fields[1:]])
   elif fields[0]=='g':groups.append(fields[1:])
 require(groups==[['same_A_matched_ink_outer']],'OBJ group mismatch')
 require(np.array_equal(v,vg) and np.array_equal(f,fg),'GLB numerical geometry differs')
 require(np.array_equal(v,np.array(vo,np.float32)) and np.array_equal(f,np.array(fo,np.int32)),'OBJ numerical geometry differs')
 canonical=gh(v,f);require(canonical==rec['geometry_sha256'],'diagnostic canonical hash mismatch')
 require(rec['diagnostic_geometry_hash_convention']=='float32 vertices / int32 faces, matching exported NPZ storage','missing or wrong hash schema')
 require(len(v)==rec['unchanged_graph_edges']*16 and len(f)==rec['unchanged_graph_edges']*28,'8-sided closed A tube counts differ')
 require(rec['preregistered_main_arm'] is False and rec['reserved_read_by_this_diagnostic'] is False and rec['reserved_already_used_by_main_experiment'] is True,'post-protocol role metadata mismatch')
 return dict(status='PASS',vertices=len(v),triangles=len(f),glb_obj_npz_numeric_equality=True,canonical_geometry_sha256=canonical,geometry_hash_schema='SERIALIZED_FLOAT32_INT32',int64_fallback_needed=False,paths={k:str(p.relative_to(rt.ROOT)) for k,p in paths.items()},file_sha256={k:rt.sha(p) for k,p in paths.items()},asset_result_sha256=rt.sha(rt.ART/'results'/(unit+'.json')),asset_seal_sha256=rt.sha(rt.ART/'seals'/(unit+'.json')),post_protocol_diagnostic=True,primary_assets_modified=False)

def main():
 result=dict(status='INCOMPLETE',audit_source_sha256=rt.sha(__file__),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),scenes={},scope='Two additional post-protocol DEV-ink assets; no video re-decode or scientific reevaluation')
 for scene in ['lego','chair']:
  try:result['scenes'][scene]=check(scene)
  except Exception as e:result['scenes'][scene]=dict(status='INVALID',error=repr(e),traceback=traceback.format_exc())
 result['status']='PASS' if all(x['status']=='PASS' for x in result['scenes'].values()) else 'INVALID'
 rt.atomic_json(rt.ART/'results/ADDITIONAL_ASSET_AUDIT.json',result)
 print(json.dumps({s:{k:v for k,v in r.items() if k in ['status','vertices','triangles','geometry_hash_schema','error']} for s,r in result['scenes'].items()}),flush=True)
 return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
