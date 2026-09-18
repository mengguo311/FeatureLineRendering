import ctypes,json,time,os
import numpy as np
from src.corrected_layers import AreaLayers,bind_fast_query
from src.foundation import project_jacobian
cpus=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,cpus[:4])
l=AreaLayers.from_native_arrays(np.array([0,1,2,2,3]),np.array([2,4,6],'f4'),np.array([.9,.5,.6],'f4'),2,2)
K=np.array([[200.,0,199.5],[0,200.,199.5],[0,0,1]]);w=np.eye(4);uv=np.zeros((1,2));z=np.array([3.]);point=np.array([[.1,.2,3.]])
t=time.monotonic()
for _ in range(5000):
 l.query(uv,z,.02)
 q,depth,J=project_jacobian(point,K,w)
 np.linalg.pinv(np.tile(J[0],(4,1)));np.linalg.inv(w)
print(json.dumps(dict(seconds=time.monotonic()-t,omp=os.environ.get('OMP_NUM_THREADS'),blas=os.environ.get('OPENBLAS_NUM_THREADS'),wait=os.environ.get('OMP_WAIT_POLICY'))))
