"""Diagnostic trap only: never reinterpret/drop malformed binning records."""
ANCHOR='\t// Generate no key/value pair for invisible Gaussians\n'
CHECK=r'''
    uint2 audit_min, audit_max;
    getRect(points_xy[idx], radii[idx], audit_min, audit_max, grid);
    uint32_t allocated = offsets[idx] - ((idx == 0) ? 0 : offsets[idx-1]);
    uint32_t actual = radii[idx] > 0 ?
        (audit_max.x-audit_min.x)*(audit_max.y-audit_min.y) : 0;
    if (allocated != actual) {
        printf("BINNING_MISMATCH id=%u radius=%d xy=(%.9g,%.9g) xybits=(%u,%u) depth=%.9g allocated=%u actual=%u rect=(%u,%u)-(%u,%u) grid=(%u,%u)\n",
          (unsigned)idx, radii[idx], points_xy[idx].x, points_xy[idx].y,
          __float_as_uint(points_xy[idx].x),__float_as_uint(points_xy[idx].y),depths[idx],
          allocated,actual,audit_min.x,audit_min.y,audit_max.x,audit_max.y,grid.x,grid.y);
        asm("trap;");
    }
'''
def instrument(source):
 if source.count(ANCHOR)!=1:raise ValueError('expected exactly one duplicateWithKeys anchor')
 return source.replace(ANCHOR,CHECK+ANCHOR)
