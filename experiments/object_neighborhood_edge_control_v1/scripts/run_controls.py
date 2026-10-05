import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import resource_guard
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('method');p.add_argument('--time-budget',type=float)
    args=p.parse_args();resource_guard()
    from local_optimization import optimize
    optimize(args.scene,args.method,args.time_budget)
