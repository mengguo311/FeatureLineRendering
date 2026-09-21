# G1 implementation details frozen before any scene line output

The amended PROTOCOL.md and incorporated INHERITED_PROTOCOL.md remain authoritative.
G0 selected common Kmax128. Primary tau .90, all other five tau/cap combinations
and fixed first k4/k8/k16 remain controls. No new scientific thresholds.

Eight adjacent raster neighbors, ordered NW,N,NE,W,E,SW,S,SE. Exact discrete W1
integrates the union-depth CDF. ID histograms aggregate repeated IDs in the shuffled
slot null before Hellinger comparisons; native base IDs remain unique per pixel.
Shape depth matching uses the nearest retained neighbor layer within 3*pair scale,
then normalized Gaussian convolution (truncate4) and analytic quotient-rule Hessian
at scales1.5/2.5/4, divided by the central local depth scale. Subtract central depth
before accumulation for exact constant-field cancellation. This computes the
Hessian of a separately matched local field without averaging front/back layers.
Shape support uses frozen layer seedability and absolute layer mass. Polarity stays
separate as E_shape_ridge and E_shape_valley. Matching ties choose earliest layer.

E_layer uses maximum negative-Hessian ridge of variance/d^2 or entropy/log(max(K,2)),
with the frozen two-heavy-separated-layers, 5-of-9 and .75 directed-order gates.
Directed signs are oriented by the strongest adjacent front-depth difference.
E_occ uses the exact frozen pair formula. Its native pair detector uses the smallest
frozen scale1.5; shape/layer width uses the actual winning Hessian scale.
Hysteresis normal NMS is bilinear; continuation uses the frozen axial30-degree,
step45-degree, BC.25 and layer depth3*d rules. Width is ceil(winning sigma), admits
only pixels above the low threshold with matching depth layer and orientation.
Raw bands have no cleanup. Controls without IDs remove identity compatibility.

Expected/front/median controls use Gaussian depth gradients at the minimum frozen
scale1.5 and the same foreground support. No-ID removes identity factors from the
full geometry channels, including exact W1. Its raw W1 map is separately saved.
Density control projects all positive-camera-depth centers through full K and uses
the prior unit-center adaptive KDE and Hessian ridge (no visibility weighting).
RGB Canny uses official CUDA RGB, sigma1.2 and thresholds50/120, visual baseline only.
Scalar depth/density/RGB baselines are compared separately against each evidence
class; duplicated baseline arrays do not imply different baseline line classes.

Normalization is each full-method channel's exact positive99th percentile pooled
across the sixteen frozen TRAIN construction views. No C/DEV output is opened.
Both inherited hysteresis percentile grids run for every control and view.
Pairwise matched ink uses the minimum positive raw-band pixel count of full and
comparator, stable response ranking within each raw band, raster-index ties.
Matched masks are comparison artifacts only, never construction candidates.
Long-component ink is raw-band ink belonging to an 8-connected component whose
skeleton has at least24 pixels. Mechanism requires both the frozen .05 difference
and visible deterioration, never that diagnostic alone.

Every native event source and control's offsets/IDs/z/weights/stream positions,
layer assignments/histograms/residuals, raw fields, geometry, orientations/scales,
normalization, thresholds, NMS/anchors, both raw bands and pairwise matched masks
are saved. Contact sheets include every fixed view, control, channel/polarity, soft
field and both raw-band grids; RGB references are separate. Source and output
hashes, confinement and native-open audits cover the complete stages and reruns.
