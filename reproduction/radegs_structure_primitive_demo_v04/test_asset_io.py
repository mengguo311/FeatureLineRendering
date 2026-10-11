import unittest,numpy as np
from unittest.mock import patch
from run import reload_graph
class Mapping:
    def __init__(self):
        self.data={k:np.zeros((3,4,3) if k=='control' else (3,3) if k=='normal' else (3,)) for k in ['control','pixel','normal','opacity','width']};self.count={k:0 for k in self.data}
    def keys(self):return self.data.keys()
    def __getitem__(self,k):self.count[k]+=1;return self.data[k]
class IO(unittest.TestCase):
    def test_each_compressed_field_loaded_once(self):
        m=Mapping()
        with patch('run.np.load',return_value=m):g=reload_graph('dummy',[{} for _ in range(3)])
        self.assertTrue(all(c<=1 for c in m.count.values()),m.count);self.assertEqual(len(g),3)
if __name__=='__main__':unittest.main(verbosity=2)
