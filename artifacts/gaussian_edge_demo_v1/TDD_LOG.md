# Observed RED → GREEN execution record

This records tool execution actually observed, not fabricated timings. Synthetic fixtures live only in tests.

1. Frozen eligible ranking: `npm test` failed because `rankGlobal` was undefined. Implemented category offsets, eligible filtering, stable score/ID sorting, ceil density and score intersection. Subsequent run passed 1/1.
2. Cached brush weighting: new test failed because `brushSelection` was undefined. Implemented repeated-ID weighted aggregation with unknown tracked separately. Run exposed a zero-evidence selected ID at minScore=0; excluded zero numerator. Passed 2/2. Fixture uses IDs 0/1/2 with distinct per-slot weights and repeated occurrence, including unknown ID 2.
3. Interaction core tracer: new test failed on missing `nativePoint`. Implemented native coordinates, ROI pixels, kernel wxyz conversion, original-index background IDs, view lock transition and complete export. Passed 3/3. Quaternion regression later strengthened to asymmetric w/x/y/z fixture.
4. Loopback/gzip serving: new test failed on missing `createServer`. Implemented loopback read-only static serving, gzip binary mapping, health and traversal rejection. Passed 4/4.
5. Browser shell tracer: `node tests/browser-shell.mjs` failed because visible `#imageCanvas` did not exist. Added Chinese UI, local Three scene and native canvas/control wiring; actual system-Chrome WebGL test passed. First full real-data browser run subsequently exposed a favicon 404; explicit empty favicon removed the console error.
6. Exact camera projection: added real six-camera test; `npm test` failed on missing `alignNativeCamera`. Implemented OpenCV-to-Three flip and exact K projection. Passed 5/5, <1e-7 pixel tolerance. Added browser button assertion, observed count 0 != 1, then wired alignment button and browser shell passed.
7. Brush radius recomputation: browser test failed because ROI size did not change when radius slider changed. Added re-rasterization. Initial rerun still failed because test mouse click was outside scrolled viewport; test now scrolls real canvas before clicking. Final browser radius test passed.

Final verification exercises real exported Mic/Materials assets across all six frames. No source data or source scientific arrays were mutated. Test outcome artifacts are in `screenshots/`.
