"""Fixed triangle assets, real world thickness, CPU rasterization and offline viewer.

Self-z-buffering only sees this asset. Without an independently calibrated
occluder_depth it is x-ray relative to the original GS object's opaque surfaces.
"""
import base64,ctypes,hashlib,json,os,struct,subprocess
from pathlib import Path
import numpy as np
import runtime as rt
_LIB=None

def _backend():
 global _LIB
 if _LIB is not None:return _LIB
 src=rt.EXP/'mesh_raster.cpp';h=rt.sha(src);folder=rt.OUT/'native';folder.mkdir(parents=True,exist_ok=True)
 dst=folder/('mesh_raster_'+h[:16]+'.so')
 if not dst.exists():
  rt.guard('mesh_raster_cpu_build');tmp=dst.with_suffix('.tmp.so')
  p=subprocess.run(['g++','-O3','-std=c++11','-shared','-fPIC',str(src),'-o',str(tmp)],text=True,capture_output=True,check=False)
  (rt.ART/'logs/mesh_raster_build.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError('stage CPU raster build failed; see mesh_raster_build.log')
  tmp.replace(dst)
 _LIB=ctypes.CDLL(str(dst));fn=_LIB.raster_mesh
 fn.argtypes=[ctypes.c_void_p,ctypes.c_int64,ctypes.c_void_p,ctypes.c_int64,ctypes.c_int,ctypes.c_int]+[ctypes.c_double]*5+[ctypes.c_void_p,ctypes.c_void_p];fn.restype=None
 rt.atomic_json(rt.ART/'MESH_RASTER_BUILD.json',dict(source=str(src),source_sha256=h,binary=str(dst),binary_sha256=rt.sha(dst),gpu=False,threads=1,near_clip=True,perspective_correct_depth=True,visibility='asset self-zbuffer; original GS opaque surface occlusion unavailable unless separately calibrated'))
 return _LIB

def _arrays(vertices,faces):
 v=np.asarray(vertices,dtype=np.float32).reshape(-1,3);f=np.asarray(faces,dtype=np.int32).reshape(-1,3)
 if not np.isfinite(v).all() or (len(f) and (f.min()<0 or f.max()>=len(v))):raise ValueError('finite vertices and valid triangle indices required')
 return np.ascontiguousarray(v),np.ascontiguousarray(f)

def render_mesh(vertices,faces,camera,color=(20,90,160),background=None,occluder_depth=None,occlusion_tolerance=0.0,near=.01):
 """Returns mask, camera-z depth, RGB and visible face_index. Input unchanged.

 Pixel centers are integer x/y, matching native cx=(width-1)/2 convention.
 Optional depth is a caller-supplied fixed visibility operator; its correctness
 must be independently established. No alpha/image mask is inferred here.
 """
 v,f=_arrays(vertices,faces);w=int(camera['width']);h=int(camera['height']);m=np.asarray(camera['w2c'],np.float64)
 q=np.ascontiguousarray(v.astype(np.float64)@m[:3,:3].T+m[:3,3]);fx=w/(2*np.tan(camera['FoVx']/2));fy=h/(2*np.tan(camera['FoVy']/2))
 z=np.empty((h,w),np.float32);winner=np.empty((h,w),np.int32)
 _backend().raster_mesh(q.ctypes.data,len(q),f.ctypes.data,len(f),w,h,fx,fy,(w-1)/2,(h-1)/2,float(near),z.ctypes.data,winner.ctypes.data)
 mask=np.isfinite(z);visibility='asset_self_only_xray_relative_to_GS'
 if occluder_depth is not None:
  oc=np.asarray(occluder_depth)
  if oc.shape!=(h,w):raise ValueError('occluder depth shape mismatch')
  mask &= z<=oc+float(occlusion_tolerance);visibility='external_depth_operator'
 rgb=np.full((h,w,3),255,np.uint8) if background is None else np.asarray(background,dtype=np.uint8).copy()
 if rgb.shape!=(h,w,3):raise ValueError('RGB background shape mismatch')
 rgb[mask]=np.asarray(color,np.uint8)
 return dict(mask=mask,depth=z,rgb=rgb,face_index=winner,visibility=visibility)

def tube_mesh(xyz,edges,radius,sides=8):
 """Closed straight tubes for an unchanged original edge graph; world radius."""
 p=np.asarray(xyz,dtype=np.float64);e=np.asarray(edges,dtype=np.int64).reshape(-1,2)
 if radius<=0 or sides<3:raise ValueError('positive radius and at least 3 sides required')
 if not len(e):return np.empty((0,3),np.float32),np.empty((0,3),np.int32)
 a=p[e[:,0]];b=p[e[:,1]];t=b-a;l=np.linalg.norm(t,axis=1)
 if np.any(l<=1e-12):raise ValueError('zero-length graph edge')
 t/=l[:,None];ref=np.eye(3)[np.argmin(np.abs(t),axis=1)];u=np.cross(t,ref);u/=np.linalg.norm(u,axis=1)[:,None];v=np.cross(t,u)
 theta=np.arange(sides)*2*np.pi/sides;ring=radius*(np.cos(theta)[None,:,None]*u[:,None]+np.sin(theta)[None,:,None]*v[:,None])
 vertices=np.stack([a[:,None]+ring,b[:,None]+ring],axis=1).reshape(-1,3).astype(np.float32)
 fs=[]
 for j in range(sides):
  k=(j+1)%sides;fs.extend([[j,k,sides+k],[j,sides+k,sides+j]])
 for j in range(1,sides-1):fs.extend([[0,j+1,j],[sides,sides+j,sides+j+1]])
 faces=(np.asarray(fs,np.int32)[None]+(np.arange(len(e))*2*sides)[:,None,None]).reshape(-1,3)
 return vertices,faces

def glb_bytes(vertices,faces,name='outer',color=(.025,.025,.025)):
 v,f=_arrays(vertices,faces);vb=v.astype('<f4').tobytes();fb=f.astype('<u4').tobytes();binary=vb+fb
 doc=dict(asset={'version':'2.0','generator':'GAER multiview lifted fixed thin curves'},scene=0,scenes=[{'nodes':[0]}],nodes=[{'mesh':0,'name':name}],
  meshes=[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'material':0,'mode':4}]}],materials=[{'pbrMetallicRoughness':{'baseColorFactor':list(color)+[1.],'metallicFactor':0.,'roughnessFactor':1.},'doubleSided':True,'extensions':{'KHR_materials_unlit':{}}}],extensionsUsed=['KHR_materials_unlit'],
  buffers=[{'byteLength':len(binary)}],bufferViews=[{'buffer':0,'byteOffset':0,'byteLength':len(vb),'target':34962},{'buffer':0,'byteOffset':len(vb),'byteLength':len(fb),'target':34963}],accessors=[{'bufferView':0,'componentType':5126,'count':len(v),'type':'VEC3'},{'bufferView':1,'componentType':5125,'count':f.size,'type':'SCALAR'}],extras={'fixed_geometry':True,'up_axis_original':'Z','camera_dependent_update':False,'surface_recovery_certified':False})
 if len(v):doc['accessors'][0].update(min=v.min(0).tolist(),max=v.max(0).tolist())
 if not len(f):doc.update(scenes=[{'nodes':[]}],nodes=[],meshes=[],bufferViews=[],accessors=[])
 j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary+=b'\0'*((-len(binary))%4)
 return struct.pack('<III',0x46546c67,2,28+len(j)+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary

def export_mesh(folder,vertices,faces,name='outer',color=(.025,.025,.025)):
 folder=rt.scoped(Path(folder)/'.allowed').parent;v,f=_arrays(vertices,faces);paths={k:str(folder/(name+'.'+k)) for k in ['glb','obj','npz']}
 Path(paths['glb']).write_bytes(glb_bytes(v,f,name,color))
 with Path(paths['obj']).open('w') as o:
  o.write('# Fixed lifted world-space thin curve tubes; no camera updates\ng '+name+'\n')
  for p in v:o.write('v %.9g %.9g %.9g\n'%tuple(p))
  for p in f+1:o.write('f %d %d %d\n'%tuple(p))
 rt.npz(paths['npz'],vertices=v,faces=f)
 return paths

def write_viewer(path,assets):
 """Standalone file:// WebGL2 mesh viewer; assets[label]={vertices,faces}."""
 data={}
 for name,asset in assets.items():
  v,f=_arrays(asset['vertices'],asset['faces'])
  data[name]=dict(vertices=base64.b64encode(v.astype('<f4').tobytes()).decode(),faces=base64.b64encode(f.astype('<u4').tobytes()).decode(),count=f.size,min=v.min(0).tolist() if len(v) else [0,0,0],max=v.max(0).tolist() if len(v) else [1,1,1],sha256=hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest())
 template=(rt.EXP/'mesh_viewer_template.html').read_text();rt.scoped(path).write_text(template.replace('__MESH_DATA__',json.dumps(data,separators=(',',':'))))
