"""Expected failure on sealed raw real RGB controls. Do not erase this result."""
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
failures=[]
for path in sorted((ROOT/'out/image_space_edge_foundation_v1/fixed_fields').glob('*/*/rgb_controls.npz')):
    z=np.load(path);o=z['original']
    for arm in ['sharpen','soften']:
        new=((z[arm]<0)|(z[arm]>1))&~((o<0)|(o>1))
        count=int(new.sum());print(path.parent.parent.name,path.parent.name,arm,'new_clipped_values',count)
        if count:failures.append((path.parent.parent.name,path.parent.name,arm,count))
print('RAW_CONTROL_GUARD', 'FAIL' if failures else 'PASS',failures)
sys.exit(1 if failures else 0)
