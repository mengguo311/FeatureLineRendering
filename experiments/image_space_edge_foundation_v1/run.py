#!/usr/bin/env python
import os,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from campaign import run
if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ['dev','production']:raise SystemExit('usage: run.py dev|production')
    run(sys.argv[1])
