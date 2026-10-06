"""Load aliased stock or isolated experimental package without installing anything."""
import importlib.util
import sys
from runtime import NATIVE, SOURCE, OUT

def load_package(name, init_path, binary_name, binary_path):
    import torch  # Load libtorch before the extension.
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(binary_name, str(binary_path))
    binary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(binary)
    sys.modules[name + '._C'] = binary
    spec = importlib.util.spec_from_file_location(name, str(init_path), submodule_search_locations=[str(init_path.parent)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return package

def load_backend(variant='patched'):
    if variant == 'actual':
        return load_package('gaer_actual_stock', SOURCE / 'diff_gaussian_rasterization/__init__.py',
                            'onec_stock_C', NATIVE / 'build/stock/onec_stock_C.so')
    name = 'gaer_rasterizer' if variant == 'patched' else 'gaer_original'
    binary_name = 'gaer_native_C' if variant == 'patched' else 'gaer_original_C'
    return load_package(name, OUT / 'native' / variant / 'diff_gaussian_rasterization/__init__.py',
                        binary_name, OUT / 'torch_extensions' / binary_name / (binary_name + '.so'))
