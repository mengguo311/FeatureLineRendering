"""Post-validation training-only diagnostics; no optimization or TEST reading."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,ART
from runner import unit
if __name__=='__main__':
    scripts=EXP/'scripts'
    unit('training_edge_record',[str(scripts/'record_edge.py'),'panels_high'],[EXP/'results/manifests/panels_high_edge_record.json'])
    unit('training_candidate_figure',[str(scripts/'visualize_candidates.py'),'panels_high'],[EXP/'results/manifests/panels_high_candidate_figure.json'])
    unit('single_cause_fixtures',[str(scripts/'diagnostic_injections.py')],[EXP/'results/tables/diagnostic_fixtures.json'])
