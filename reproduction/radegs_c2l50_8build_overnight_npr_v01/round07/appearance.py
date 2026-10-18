"""Read-only source color counterfactuals; never an albedo estimator."""
from env import *
import renderer as jr

ARMS=('full_sh','dc_only','anchor_sh')

def source_only(records, expected_count):
 if len(records)!=expected_count:raise ValueError('source count mismatch')
 if 'group_id' in records.dtype.names and np.any(records['group_id']!=0):raise ValueError('ink is not source evidence')
 return records

def color_mode(asset,camera,mode,anchor=None):
 if mode=='full_sh':return jr.colors(asset,camera)
 if mode=='dc_only':return np.maximum(0.,.5+.28209479177387814*asset['SH'][:,:,0])
 if mode=='anchor_sh':
  if anchor is None:raise ValueError('fixed DEV camera required')
  return jr.colors(asset,anchor)
 raise ValueError('unsupported color mode')

def activate_source(records,expected_count):
 from format import activate
 return activate(source_only(records,expected_count))

def render_mode(asset,camera,mode,anchor,background=(1,1,1),floor=.0144):
 a={k:asset[k] for k in ['means','covariance','opacity']}
 a['colors']=color_mode(asset,camera,mode,anchor)
 return jr.render(a,camera,background=background,floor=floor)
