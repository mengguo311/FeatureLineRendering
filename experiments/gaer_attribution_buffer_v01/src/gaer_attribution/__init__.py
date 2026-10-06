"""Public import for the isolated native experiment (run build.py once first)."""
from native import load_backend

_implementation = load_backend('patched')
GaussianRasterizer = _implementation.GaussianRasterizer
GaussianRasterizationSettings = _implementation.GaussianRasterizationSettings
AttributionOutput = _implementation.AttributionOutput
rasterize_gaussians_attribution = _implementation.rasterize_gaussians_attribution

__all__ = ['GaussianRasterizer', 'GaussianRasterizationSettings', 'AttributionOutput',
           'rasterize_gaussians_attribution']
