"""Stable UIDs and explicit parent provenance, independent of row order."""
import numpy as np

class Identity:
    def __init__(self,uid,label,anchor,parent_uid=None,next_uid=None):
        self.uid=np.asarray(uid,dtype=np.int64)
        self.label=np.asarray(label,dtype=np.int32)
        self.anchor=np.asarray(anchor,dtype=float)
        self.parent_uid=np.full(len(self.uid),-1,dtype=np.int64) if parent_uid is None else np.asarray(parent_uid,dtype=np.int64)
        self.next_uid=int(self.uid.max()+1) if next_uid is None else int(next_uid)
        if len(set(self.uid))!=len(self.uid):raise ValueError('duplicate UID')
    def reorder(self,order):
        return Identity(self.uid[order],self.label[order],self.anchor[order],self.parent_uid[order],self.next_uid)
    def split(self,parent_uids,children):
        idx=np.flatnonzero(np.isin(self.uid,parent_uids));keep=np.flatnonzero(~np.isin(self.uid,parent_uids))
        # Same repeat order as upstream native split: children-major, parents-minor.
        parents=np.tile(idx,children);n=len(parents)
        return Identity(np.r_[self.uid[keep],np.arange(self.next_uid,self.next_uid+n)],
                        np.r_[self.label[keep],self.label[parents]],
                        np.concatenate([self.anchor[keep],self.anchor[parents]]),
                        np.r_[self.parent_uid[keep],self.uid[parents]],self.next_uid+n)
    def continuity_field(self):
        return .5+.5*np.sin(4*np.pi*self.anchor[:,1])
    def as_dict(self):
        return {k:getattr(self,k).tolist() for k in ('uid','parent_uid','label','anchor')}|{'next_uid':self.next_uid}
