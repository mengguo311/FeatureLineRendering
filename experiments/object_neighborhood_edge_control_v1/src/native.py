"""Bind unchanged upstream wrapper to isolated stock extension, never installed globally."""
import importlib.util
import sys
import types
import torch  # Load libtorch dependencies before importing the local extension.
from runtime import OUT

def install_stock():
    def binary(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    c = binary('onec_stock_C', OUT/'build/stock/onec_stock_C.so')
    sys.modules['diff_gaussian_rasterization._C'] = c
    source = OUT/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization/diff_gaussian_rasterization/__init__.py'
    spec = importlib.util.spec_from_file_location('diff_gaussian_rasterization', str(source),
                                                submodule_search_locations=[str(source.parent)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    k = binary('onec_knn_C', OUT/'build/knn/onec_knn_C.so')
    package = types.ModuleType('simple_knn')
    package.__path__ = []
    package._C = k
    sys.modules['simple_knn'] = package
    sys.modules['simple_knn._C'] = k
    sys.path.insert(1, str(OUT/'vendor/gaussian-splatting'))
    return mod

def install_cob():
    """Separate process only: official B4 has its own native mask-gradient branch."""
    install_stock()
    for name in list(sys.modules):
        if name=='diff_gaussian_rasterization' or name.startswith('diff_gaussian_rasterization.'):
            del sys.modules[name]
    spec=importlib.util.spec_from_file_location('onec_cob_C',str(OUT/'build/cob/onec_cob_C.so'))
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    sys.modules['diff_gaussian_rasterization._C']=c
    source=OUT/'vendor/COB-GS/submodules/diff-gaussian-rasterization/diff_gaussian_rasterization/__init__.py'
    spec=importlib.util.spec_from_file_location('diff_gaussian_rasterization',str(source),submodule_search_locations=[str(source.parent)])
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    sys.path.insert(1,str(OUT/'vendor/COB-GS'))
    return mod
