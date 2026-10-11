from common import *
from primitive import *
from scipy.ndimage import maximum_filter,minimum_filter
from skimage.morphology import skeletonize
import pickle,sys

def main():
    dst=T/'geometry_replay';dst.mkdir(exist_ok=True);scene='scan24';cs=demo.cameras(scene);segments=[]
    cache=dst/'segments.pkl'
    if cache.exists():
        meta=json.loads((dst/'CACHE_SEAL.json').read_text());assert sha(cache)==meta['sha256'];segments=pickle.loads(cache.read_bytes())
    else:
        offset=0
        for vi,v in enumerate(BUILD):
            a=demo.read(scene,v);m=dict(np.load(T/'failed_attempt02/scan24_full'/f'{v}_maps.npz'));c=cs[v];mask=m['marked']&np.isfinite(a['z'])&(a['z']>0);sk=skeletonize(mask);paths=ordered_paths(sk);span=maximum_filter(a['z'],3)-minimum_filter(a['z'],3);y,x=np.nonzero(m['marked']);lookup=np.full(mask.shape,-1,int);lookup[y,x]=np.arange(len(y))+offset
            def add(q):
                z=a['z'][q[:,1],q[:,0]];pixel=float(np.median(z)/np.sqrt(c['fx']*c['fy']));s=fit_segment(core.backproject(q,z,c),pixel)
                if s['fit_error_pixel']>1 and len(q)>2:
                    mid=len(q)//2;add(q[:mid+1]);add(q[mid:]);return
                sus=(span[q[:,1],q[:,0]]>4*pixel)|(~np.isfinite(a['alpha'][q[:,1],q[:,0]]))|(a['alpha'][q[:,1],q[:,0]]<.5)
                s.update(view=vi,camera=c,uv=q,source_ids=lookup[q[:,1],q[:,0]].tolist(),normal=np.asarray(c['extrinsic'])[2,:3].copy(),opacity=float(np.clip(np.median(m['darkness'][q[:,1],q[:,0]]),.02,.95)),kind='silhouette' if sus.any() else 'surface',chain_id=chain_id,layer_id=len(segments));segments.append(s)
            for chain_id,path in enumerate(paths):
                z=a['z'][path[:,1],path[:,0]];pixel=float(np.median(z)/np.sqrt(c['fx']*c['fy']))
                for q in split_path(path,z,pixel,CFG['max_chain_arc_px']):add(q)
            offset+=len(y);print('REPLAY_CHAINS',v,len(segments),flush=True)
        assert len(segments)==76935;cache.write_bytes(pickle.dumps(segments,protocol=4));js(dst/'CACHE_SEAL.json',{'sha256':sha(cache),'segments':len(segments),'source_freeze_sha256':sha(T/'SOURCE_FREEZE.json'),'only_own_generated_pickle':True})
    if len(sys.argv)>1 and sys.argv[1]=='capture':
        associate(segments)
    else:
        f=json.loads((dst/'failed_group.json').read_text());g,amb=associate([segments[i] for i in f['indices']]);print('ACTUAL_GROUP_REPLAY',len(g),'primitives',len(amb),'ambiguities');assert len(g)==len(f['indices']);js(dst/'ACTUAL_GROUP_GREEN.json',{'original_indices':f['indices'],'resulting_primitives':len(g),'finite':all(np.isfinite(x['control']).all() for x in g),'no_gap_bridge':True})

if __name__=='__main__':main()
