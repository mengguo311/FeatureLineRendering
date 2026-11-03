"""External membership references are diagnostic only, never graph inputs."""
from runtime_io import *
def reference_views(c,d):
    refs={'M4_reference':(d['membership'],[])}
    for name,path in c.get('external_memberships',{}).items():
        with np.load(path,allow_pickle=False) as z:m={k:z[k] for k in ('line_kernel_id','edge_id')}
        np.testing.assert_array_equal(m['line_kernel_id'],d['membership']['line_kernel_id'])
        refs[name]=(m,[])
    return refs

def reference_comparisons(saved,refs):
    out={}
    for arm,(m,_) in saved.items():
        new=m['edge_id'];out[arm]={}
        for name,(ref,_) in refs.items():
            old=ref['edge_id'];order=np.argsort(old,kind='stable');o=old[order];n=new[order]
            split_ids=np.unique(o[1:][(o[1:]>=0)&(o[1:]==o[:-1])&(n[1:]!=n[:-1])])
            out[arm][name]=dict(assigned_gained=int(np.sum((old<0)&(new>=0))),assigned_lost=int(np.sum((old>=0)&(new<0))),changed_id_rows=int(np.sum(old!=new)),reference_groups_split=int(len(split_ids)),split_reference_ids=split_ids.tolist(),id_changes_not_accuracy=True)
    return out
