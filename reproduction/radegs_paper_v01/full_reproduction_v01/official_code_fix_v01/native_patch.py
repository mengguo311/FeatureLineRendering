"""Compose identified fixes onto clean C24; never import paper-text losses.

Only pointer fix has an official upstream provenance. Jn, eigen conditioning
and exact RGB VJP corrections are separate independently tested engineering fixes.
"""
from pathlib import Path
import importlib.util

H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
C24=H/'sources/RaDe-GS/submodules/diff-gaussian-rasterization/cuda_rasterizer'
PREC=H/'sources/paper_text_precision_v01/submodules/diff-gaussian-rasterization/cuda_rasterizer'

def patched_files():
    patcher=Path(__file__).resolve().parent.parent/'suite_execution_v01/scan69_cuda_failure_v01/rgb_vjp_fix_v01/source_patch.py'
    spec=importlib.util.spec_from_file_location('verified_rgb_patch',patcher);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    files={n:(C24/n).read_text() for n in ['forward.cu','backward.cu','rasterizer_impl.cu']}
    files['rasterizer_impl.cu']=m.patch_impl(files['rasterizer_impl.cu'])
    b=files['backward.cu'];fixed=(PREC/'backward.cu').read_text()
    start='\tfloat tz3 = tz2 * tz;';end='\t// Account for transformation of mean to t'
    assert b.count(start)==fixed.count(start)==b.count(end)==fixed.count(end)==1
    old=b[b.index(start):b.index(end)];new=fixed[fixed.index(start):fixed.index(end)]
    b=m.once(b,old,new);b=m.once(b,'\tfloat lv3 = lv2 * lv;\n','')
    files['backward.cu']=m.patch_backward(b)
    for name,expected in [('forward.cu',2),('backward.cu',1)]:
        text=files[name];needle='glm::findEigenvaluesSymReal(Vrk,Vrk_eigen_value,Vrk_eigen_vector)'
        assert text.count(needle)==expected
        files[name]='#include "paper_geometry_precision.cuh"\n'+text.replace(needle,'paper_find_eigenvalues(Vrk,Vrk_eigen_value,Vrk_eigen_vector)')
    files['paper_geometry_precision.cuh']=(PREC/'paper_geometry_precision.cuh').read_text()
    return files
