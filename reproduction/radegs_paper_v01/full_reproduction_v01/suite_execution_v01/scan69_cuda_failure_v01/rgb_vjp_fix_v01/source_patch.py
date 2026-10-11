"""Correct derivatives of the unchanged forward; no loss or forward changes."""
def once(source,old,new):
 if source.count(old)!=1:raise ValueError('source drift: '+old)
 return source.replace(old,new)

def patch_impl(source):
 return once(source,'(float4*)dL_dconic,\n\t\tdL_dopacity), debug)','geomState.conic_opacity,\n\t\tdL_dopacity), debug)')

def patch_backward(source):
 replacements={
 'const float opacity = combined_opacity / (coef + 1e-6);':'const double opacity = combined_opacity / static_cast<double>(coef);',
 'const float dL_dcoef = dL_dopacity[idx] * opacity;':'const double dL_dcoef = dL_dopacity[idx] * opacity;',
 'const float dL_dsqrtcoef = dL_dcoef * 0.5 * 1. / (coef + 1e-6);':'const double dL_dsqrtcoef = dL_dcoef * 0.5 / static_cast<double>(coef);',
 'const float dL_ddet0 = dL_dsqrtcoef / (det_1+1e-6);':'const double dL_ddet0 = dL_dsqrtcoef / (det_1+1e-6);',
 'const float dL_ddet1 = dL_dsqrtcoef * det_0 * (-1.f / (det_1 * det_1 + 1e-6));':'const double dL_ddet1 = -dL_dsqrtcoef * det_0 / ((det_1+1e-6) * (det_1+1e-6));',
 'const float dcoef_da =':'const double dcoef_da =',
 'const float dcoef_db =':'const double dcoef_db =',
 'const float dcoef_dc =':'const double dcoef_dc =',
 'float a = cov2D[0][0] + kernel_size;':'const double a = cov2D[0][0] + kernel_size;',
 'float b = cov2D[0][1];':'const double b = cov2D[0][1];',
 'float c = cov2D[1][1] + kernel_size;':'const double c = cov2D[1][1] + kernel_size;',
 'float denom = a * c - b * b;':'const double denom = a * c - b * b;',
 'float denom2inv = 1.0f / ((denom * denom) + 0.0000001f);':'const double denom2inv = 1.0 / (denom * denom);',
 }
 for old,new in replacements.items():source=once(source,old,new)
 return source
