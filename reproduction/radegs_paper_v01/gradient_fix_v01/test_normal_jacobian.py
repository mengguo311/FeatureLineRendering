"""CPU double-precision oracle for the actual CUDA source's Jn->mean VJP.

Compile the exact scalar block, with unrelated incoming adjoints set to zero.
Every one of Jn's nine independent adjoints is compared to torch autograd.
"""
import ctypes
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import torch

HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
CUDA=HDD/'sources/paper_text_variant/submodules/diff-gaussian-rasterization'


def jn(t):
    x,y,z=t;zero=x*0;l=t.norm()
    return torch.stack((1/z,zero,x/l,zero,1/z,y/l,-x/z**2,-y/z**2,z/l)).reshape(3,3)


class NormalJacobianTests(unittest.TestCase):
    def test_exact_native_jn_chain_all_adjoints(self):
        source=(CUDA/'cuda_rasterizer/backward.cu').read_text()
        block=source.split('float dL_dtx =',1)[1].split('// Account for transformation of mean to t',1)[0]
        # Promote this SAME native scalar expression to double; GLM retains
        # its column-major indexing. Nothing from the oracle is in this block.
        block=('float dL_dtx ='+block).replace('float ','double ')
        with tempfile.TemporaryDirectory(dir=HDD/'tmp') as tmp:
            path=Path(tmp)
            cpp='''#include <cmath>
#include <glm/glm.hpp>
extern "C" void vjp(const double* p, const double* g, double lv, double* out) {
 glm::dvec3 t(p[0],p[1],p[2]);
 glm::dmat3 dL_dJn;
 for(int r=0;r<3;r++)for(int c=0;c<3;c++)dL_dJn[c][r]=g[r*3+c];
 double l=glm::length(t),l3=l*l*l,lv3=lv*lv*lv;
 double tz=1/t.z,tz2=tz*tz,tz3=tz2*tz;
 double x_grad_mul=1,y_grad_mul=1,h_x=0,h_y=0;
 double dL_dJ00=0,dL_dJ11=0,dL_dJ02=0,dL_dJ12=0,dL_du=0,dL_dv=0,tmp=0;
'''+block+'''
 out[0]=dL_dtx;out[1]=dL_dty;out[2]=dL_dtz;
}
'''
            (path/'test.cpp').write_text(cpp)
            subprocess.run(['g++','-shared','-fPIC','-O2','-I'+str(CUDA/'third_party/glm'),str(path/'test.cpp'),'-o',str(path/'test.so')],check=True)
            fun=ctypes.CDLL(str(path/'test.so')).vjp
            ptr=ctypes.POINTER(ctypes.c_double);fun.argtypes=[ptr,ptr,ctypes.c_double,ptr]
            failures=[]
            for xyz in ((.03,-.02,1.8),(-.07,.04,2.6),(.06,.01,3.2),(.4,-.3,2.)):
                t=torch.tensor(xyz,dtype=torch.double,requires_grad=True)
                for index in range(9):
                    g=torch.zeros(3,3,dtype=torch.double);g.flatten()[index]=1
                    expected=torch.autograd.grad((jn(t)*g).sum(),t)[0]
                    output=(ctypes.c_double*3)()
                    fun((ctypes.c_double*3)(*xyz),(ctypes.c_double*9)(*g.flatten().tolist()),1.04,output)
                    actual=torch.tensor(list(output),dtype=torch.double)
                    if not torch.allclose(actual,expected,rtol=1e-10,atol=1e-12):
                        failures.append({'xyz':xyz,'adjoint_index':index,'native':actual.tolist(),
                                         'oracle':expected.tolist(),'max_error':float((actual-expected).abs().max())})
            print(json.dumps({'Jn_vjp_cases':36,'failures':failures},indent=2),flush=True)
            self.assertEqual(failures,[])

    def test_reference_jn_gradcheck(self):
        t=torch.tensor([.03,-.02,1.8],dtype=torch.double,requires_grad=True)
        self.assertTrue(torch.autograd.gradcheck(jn,(t,),eps=1e-6,atol=1e-8,rtol=1e-6))


if __name__=='__main__':unittest.main(verbosity=2)
