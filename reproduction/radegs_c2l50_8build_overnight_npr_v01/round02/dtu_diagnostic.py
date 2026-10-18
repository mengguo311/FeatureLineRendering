from env import *
from geometry import normal_evidence
import traceback
def compute(s,v):
 rgb,z,a=raw(s,v);c=cam(s,v);up=json.loads((R1/'A'/s/'model/MODEL.json').read_text())['axis']['up'];ar=normal_evidence(z,a,c,up);h,w=z.shape;y,x=np.mgrid[:h,:w];per=((x/w<.12)|(x/w>.88)|(y/h>.88))&(y/h>.65);cen=((x/w-.5)/.18)**2+((y/h-.5)/.26)**2<1
 valid=np.isfinite(z)&(z>.2)&(a>=.5);old=json.loads((V2/'stageA'/s/'model/MODEL.json').read_text())['plane'];uv=np.c_[x[valid],y[valid]];X=unproject(uv,z[valid],c);res=np.full(z.shape,np.nan);res[valid]=(X@np.asarray(old['normal'])+old['offset'])/(z[valid]/np.sqrt(c['fx']*c['fy']));ar.update(peripheral=per,central=cen,old_plane_signed_p=res)
 row=dict(scene=s,view=v,raw_valid=int(valid.sum()),local_qualified=int(ar['valid'].sum()),upright_local=int(ar['upright'].sum()),upright_in_pool=int((ar['upright']&per).sum()),upright_outside_pool=int((ar['upright']&~per).sum()),pool_raw_valid=int((valid&per).sum()),pool_local_qualified=int((ar['valid']&per).sum()),old_plane_band3p=int((valid&(abs(res)<=3)).sum()),old_plane_upright_agreement=int((ar['upright']&(abs(res)<=3)).sum()),formal_subject_gate='NO_GO',parts='NOT_RUN')
 return ar,row
def run(s,v):
 p=R/'A_DIAGNOSTIC'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);ar,row=compute(s,v);np.savez_compressed(p/'LOCAL_DEPTH.npz',**ar);js(p/'COUNT.json',row);rgb,z,a=raw(s,v);old=npz(R1/'A'/s/v/'SUBJECT.npz');ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');lab=np.zeros(z.shape,np.uint8);lab[ar['valid']]=2;lab[ar['upright']]=1;unknown=(a>=.1)&~ar['valid'];poolim=rgb.copy();poolim[ar['peripheral']]=.5*poolim[ar['peripheral']]+.5*np.array([.8,.2,.8]);panel(p/'FULL.jpg',[('Original source RGB',rgb),('Original C8 ink | XRAY reference',ref['line_rgb']),('TRUE joint | frozen CPU reference',ref['joint_rgb']),('r01 subject / UNKNOWN | unchanged failure',overlay(rgb,old['candidate'],old['unknown'])),('New local depth directions | blue upright, orange other',colors(rgb,lab,unknown)),('Old peripheral sample pool | purple overlay',poolim)],s+' / '+v+' | r02 support-observation diagnostic','Local depth normals are proxies, not GS covariance axes or true surfaces. No new subject mask, no downstream parts.',3);seal(p);print('DTU',row,flush=True)
def main():
 status('DTU_DIAGNOSTIC',children=[os.getpid()]);fail=[]
 for s in ['scan24','scan65']:
  for v in views(s):
   try:guard();run(s,v)
   except Exception as e:fail.append([s,v]);js(R/('ENGINEERING_DTU_'+s+'_'+v+'.json'),dict(error=repr(e),traceback=traceback.format_exc()))
 status('DTU_DIAGNOSTIC_DONE',children=[],failed=fail);raise SystemExit(bool(fail))
if __name__=='__main__':main()
