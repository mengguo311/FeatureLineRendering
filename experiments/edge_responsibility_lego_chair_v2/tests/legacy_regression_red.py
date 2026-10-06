"""The same rejected-profile regression against the unchanged v1 interface.

Expected failure is durable evidence; normal tests use the corrected interface.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from legacy_evidence import build_evidence
x=np.indices((64,64))[1]
rgb=np.repeat(np.where((x//4)%2,.8,.2)[...,None],3,2)
result=build_evidence(rgb,np.ones((64,64)))
assert len(result['profiles'])==0
assert np.mean(result['balanced_maps'],axis=0).sum()==0, 'v1 rejected profiles still feed main balanced scoring evidence'
