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

The first Chair GS arm completed in374.918s with0 accepted modes; its complete
output is retained under local/chair/attempt_00_thread_contention/F/gs. The ongoing
Chair no-GS arm and Lego GS arm were interrupted by the owner, with exit logs and
all partial artifacts retained. A5000-iteration synthetic geometry/query benchmark
measured33.174s with4 BLAS/OpenMP threads versus1.019s with1 thread/passive waiting.
A full synthetic multimodal-inference plus2300 native-query fixture was byte-identical
(SHA25671ef140f0482850a7386af8a4861705f521a2aca37317d6eeb6832b2947bcdd1).
Both primary processes were restarted with the same method, queries, inputs and
thresholds, changing only resource scheduling. Completed Chair outputs will be
compared array-for-array against the repeat. No posterior was retrained. The
separately tested conditional-OpenMP query library is not used by the scientific
runner; the original native query arithmetic remains in use.

The native-open audit's first pass flagged the pinned stock repository directory
and arguments/__init__.py during interpreter startup, before confinement. The
source file was checked against the archived pinned source hash; these are explicit
bootstrap source exceptions, not photograph/data exemptions. The failed audit
attempt is retained. Administrative audit-module extensions after early launches
are versioned in Git; no inference formula or gate was changed by this accounting.

The single-thread geometry benchmark isolates scheduling overhead; it does not
promise the same speedup for a full scene. Full scene profiles retain thousands of
modes and remained expensive. Independent arms are therefore dispatched to four
single-thread forked workers per scene, inheriting the same Landlock restrictions
and read-only evidence. A RED/GREEN fixture compares every accepted/mode record
and every profile array to serial execution exactly. This changes only scheduling;
each child calls the identical run_inference_arm and writes its own exclusive arm
directory. No C worker starts until every F arm is frozen. Partial serial attempts
are retained, and their completed outputs are checked against final repetitions.
