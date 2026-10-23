"""Combine explicitly identified camera evidence without changing M1 gates."""
import runtime
import numpy as np


def combine_evidence(blocks,n,source_sha256):
    keys=set();scores=[]
    for block in blocks:
        key=block['camera_key']
        if key in keys:raise ValueError('duplicate camera evidence')
        keys.add(key)
        if block['source_sha256']!=source_sha256 or not np.array_equal(block['source_index'],np.arange(n)):
            raise ValueError('source snapshot/order mismatch')
        score=np.asarray(block['score'])
        if score.shape!=(n,6) or not np.isfinite(score).all() or (score<0).any():
            raise ValueError('invalid per-original-row region evidence')
        scores.append(score)
    if not scores:raise ValueError('no evidence')
    return np.stack(scores)


def transition_counts(old,new):
    u=old['unknown'];v=new['unknown']
    if u.shape!=v.shape:raise ValueError('source universe mismatch')
    return dict(old_unknown=int(u.sum()),new_unknown=int(v.sum()),
        unknown_to_supported=int((u&~v).sum()),supported_to_unknown=int((~u&v).sum()),
        supported_label_changed=int((~u&~v&(old['region_id']!=new['region_id'])).sum()),
        old_conflicts=int(old['conflict'].sum()),new_conflicts=int(new['conflict'].sum()))
