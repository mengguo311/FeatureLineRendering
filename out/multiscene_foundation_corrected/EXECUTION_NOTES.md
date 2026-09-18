# Execution notes

The sampling RED slice observed actual center-mapping and direct-splat failures,
not only missing imports. The first corrected preregistration/config freeze is
commit fb4488e, pushed before qualification launch. No scene local result existed
when the following implementation details were fixed and synthetic-tested.

The inherited, never scene-executed shifted-control helper rolled nearest-edge
coordinate arrays without translating their coordinate values. A synthetic
on-edge residual test failed by exactly32 pixels. The new wrapper translates the
coordinates along with the maps, implementing the already-registered cyclic shift;
it changes no shift dose, detector or gate. The old helper/source is preserved.

Surface diagnosis uses indivisible delta/2 occupied cells; fixed hash parity splits
fit/holdout. Centers are represented by their cell means for equal-cell fits and
native-contribution barycenters for weighted fits. Plane/quadratic fits use weighted
least squares. Two-plane fitting uses three train-only PCA-coordinate median split
starts and ten fixed assignment steps; minimum training residual selects the fit.
Holdout never selects the model.32 fixed-seed cell bootstraps, adjacent scales and
all eligible posterior repeats determine whether a candidate can be called stable.
Volume scatter is descriptive, not a surface generator. All priors/thresholds remain
those frozen in config.json. This code is not imported by inference for generation.

Raw test logs preserve their original bytes, including unittest's whitespace.
Synthetic fixtures reduce sample counts only inside tests; scene config is unchanged.
