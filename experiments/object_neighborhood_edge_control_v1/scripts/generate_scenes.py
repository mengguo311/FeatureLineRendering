import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP, resource_guard
from targets import generate
if __name__=='__main__':
    resource_guard(gpu=False)
    generate(json.loads((EXP/'configs/pilot.json').read_text()))
