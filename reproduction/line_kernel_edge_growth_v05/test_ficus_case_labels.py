"""Actual output contract: below-threshold and inherited cases are not new material growth."""
from common import *
import common,tempfile,unittest,types
from unittest import mock
import protected_runner
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_016')

class Labels(unittest.TestCase):
    def test_ficus_fixed_cases_are_reference_controls(self):
        common.CFG=None;common.END=None;common.START=None
        carrier=types.SimpleNamespace(rows=np.arange(6),version=7)
        state=dict(carriers={33824:carrier,21870:carrier})
        c=dict(joint_state='joint',control_state='prefix',input_files={'joint':'j','prefix':'p'},
               material_case_ids=[33824],damaged_case_ids=[21870],
               joint_case_label='joint_reference_not_material',
               fixed_case_rule='Frozen ficus damaged controls, below-threshold33824 and inherited29734; no material-growth assertion.')
        labels={k:np.zeros(6,dtype=np.int64) for k in ('M3','M4_CONTROL','M4_JOINT','M4_VARIANT','PARENTS')}
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td)
            with mock.patch.object(protected_runner,'load_state',return_value=state),mock.patch.object(protected_runner,'group_figures'):
                protected_runner.fixed_case_figures(c,out,{},labels,None,[],np.zeros(6,dtype=np.int64))
                protected_runner.fixed_case_comparison(c,out,None,np.zeros(6,dtype=np.int64),[])
            figures=json.loads((out/'FIXED_CASES_SELECTION.json').read_text())
            comparison=json.loads((out/'FIXED_CASE_COMPARISON.json').read_text())
            self.assertEqual(figures['cases'][0]['kind'],'joint_reference_not_material')
            self.assertEqual(comparison['cases'][0]['kind'],'joint_reference_not_material')
            self.assertEqual(figures['rule'],c['fixed_case_rule'])

if __name__=='__main__':unittest.main()
