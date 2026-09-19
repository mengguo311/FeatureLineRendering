"""Supplemental visibility strata; never edits all-in-frame gates or geometry."""
import numpy as np
from cc import classify_support

def stratify(sample,z,layer,delta):
    uv=np.asarray(sample['uv'],float).reshape(-1,2)
    front,support=layer.query(uv,z,delta)
    inside=np.asarray(sample['inside'],bool);joint=np.asarray(sample['joint'],bool)
    weights=np.asarray(sample['projected_weights'],float)
    labels=classify_support(front,support,inside);classes=np.array(labels,dtype=str)
    def summarize(mask):
        length=float(weights[mask].sum());good=float(weights[mask&joint].sum())
        return dict(samples=int(mask.sum()),projected_length=length,supported_length=good,unsupported_length=length-good,joint_fraction=good/length if length else None)
    return dict(classifications=labels,strata={k:summarize(classes==k) for k in ['visible_supported','visible_unsupported','uncertain','hidden','out_of_frame']},all_in_frame=summarize(inside))
