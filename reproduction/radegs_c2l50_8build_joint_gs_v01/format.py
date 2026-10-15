from common import *
from plyfile import PlyData,PlyElement
from scipy.special import expit,logit
from scipy.spatial.transform import Rotation
def read_ply(path):return PlyData.read(path)['vertex'].data.copy()
def write_ply(path,a):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);PlyData([PlyElement.describe(a,'vertex')],text=False,byte_order='<',comments=['Frozen source plus C2L50 8BUILD arms/C ink; see group mapping and FORMAT_ZH']).write(path)
def vals(a,names):return np.stack([a[k] for k in names],1).astype(np.float64)
def activate(a):
 means=vals(a,['x','y','z']);sc=np.exp(vals(a,[f'scale_{i}' for i in range(3)]));q=vals(a,[f'rot_{i}' for i in range(4)]);q/=np.linalg.norm(q,axis=1,keepdims=True);R=Rotation.from_quat(q[:,[1,2,3,0]]).as_matrix();f=a['filter_3D'].astype(float) if 'filter_3D' in a.dtype.names else np.zeros(len(a));ss=sc*sc+f[:,None]**2;op=expit(a['opacity'].astype(float))*np.sqrt(np.prod(sc*sc/ss,axis=1));cov=(R*ss[:,None,:])@R.transpose(0,2,1)
 dc=vals(a,[f'f_dc_{i}' for i in range(3)]);rest=[k for k in a.dtype.names if k.startswith('f_rest_')];rest=sorted(rest,key=lambda k:int(k.split('_')[-1]));sh=np.concatenate([dc[:,:,None],vals(a,rest).reshape(len(a),3,-1)],2) if rest else dc[:,:,None]
 assert np.isfinite(means).all() and np.isfinite(cov).all() and np.isfinite(op).all() and np.isfinite(sh).all();assert (ss>0).all()
 return dict(means=means,covariance=cov,opacity=op,SH=sh)
def merge_native(s,l):
 dtype=list(s.dtype.descr)+[(k,l.dtype[k]) for k in l.dtype.names if k not in s.dtype.names]
 if 'filter_3D' in s.dtype.names and 'filter_3D' in l.dtype.names:assert np.all(l['filter_3D']==0)
 m=np.zeros(len(s)+len(l),dtype)
 for k in s.dtype.names:m[k][:len(s)]=s[k]
 for k in l.dtype.names:m[k][len(s):]=l[k]
 return m
def portable(native,eps=1e-7):
 keep=[k for k in native.dtype.names if k in ['x','y','z','nx','ny','nz','opacity'] or k.startswith(('scale_','rot_','f_dc_','f_rest_'))]
 out=np.zeros(len(native),[(k,native.dtype[k]) for k in keep])
 for k in keep:out[k]=native[k]
 f=native['filter_3D'].astype(float) if 'filter_3D' in native.dtype.names else np.zeros(len(native));sc=np.exp(vals(native,[f'scale_{i}' for i in range(3)]));ss=sc*sc+f[:,None]**2;op=expit(native['opacity'].astype(float))*np.sqrt(np.prod(sc*sc/ss,axis=1));clip=(op<eps)|(op>1-eps);change=(f!=0)|~np.isfinite(native['opacity'])|clip
 for i in range(3):out[f'scale_{i}'][f!=0]=.5*np.log(ss[f!=0,i])
 out['opacity'][change]=logit(np.clip(op[change],eps,1-eps))
 return out,dict(epsilon=eps,clip_count=int(clip.sum()),filter_baked_count=int((f!=0).sum()),raw_positive_inf=int(np.isposinf(native['opacity']).sum()),raw_negative_inf=int(np.isneginf(native['opacity']).sum()),modified_logit_count=int(change.sum()),max_opacity_error=float(np.max(abs(expit(out['opacity'].astype(float))-op),initial=0)),finite_portable_logit=bool(np.isfinite(out['opacity']).all()))
def mapping(nsource,line):
 nl=len(line['primitive_id']);n=nsource+nl;return dict(group_id=np.r_[np.zeros(nsource,np.uint8),np.ones(nl,np.uint8)],source_index=np.r_[np.arange(nsource,dtype=np.int32),np.full(nl,-1,np.int32)],line_index=np.r_[np.full(nsource,-1,np.int32),np.arange(nl,dtype=np.int32)],primitive_id=np.r_[np.full(nsource,-1,np.int32),line['primitive_id']],internal_piece_id=np.r_[np.full(nsource,-1,np.int32),line['internal_piece_id']],arc_t=np.r_[np.full(nsource,np.nan),line['arc_t']])
