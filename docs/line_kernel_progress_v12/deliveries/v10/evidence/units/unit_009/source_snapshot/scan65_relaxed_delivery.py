"""Scan65 M4/reference delivery, with compact relation rows and untouched native ink."""
from runtime_io import *
from r6_delivery import save_stage,native_full,serial,scientific,worst_events
from scan65_delivery import statistics,diagnostics
import r6_delivery

def save_library(out,lib):
 out=Path(out);r6_delivery.save_library(out,lib)
 nz(out/'RELATION_ROWS.npz',**lib['relation_rows'])
 js(out/'RELATION_DIAGNOSTICS.json',serial(dict(policies=lib['paired_relation_diagnostics'],same_state=True,diagnostic_only=True)))
