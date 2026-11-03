"""Saved original-score comparison; all native scan65 delivery remains unchanged."""
from scan65_relaxed_delivery import *
import scan65_relaxed_delivery as inherited

def save_library(out,lib):
 inherited.save_library(out,lib)
 js(Path(out)/'SCORE_COMPARISON.json',serial(lib['score_comparison']))
