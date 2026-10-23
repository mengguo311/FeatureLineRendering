"""Two targeted original-ID/occlusion checks for the resumed source renderer."""
import runtime
import unittest
from test_link import TraceTests
from test_footprint import FootprintTests

suite=unittest.TestSuite([
    TraceTests('test_explicit_permuted_ids_and_capture_bound'),
    FootprintTests('test_all_pixels_match_events_after_culling_and_sort'),
])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
