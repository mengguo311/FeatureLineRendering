"""Diagnostic-only entry point with actual-free admission, no source mutation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import diagnostic_runner
import shared_runner
import strict_shared_policy as policy

# Only this process's module bindings change. Reuse tested own-process stopping,
# context identity checks, 60-second gate, seal verification and failure archive.
shared_runner.can_start=policy.can_start
shared_runner.conflict=policy.conflict
shared_runner.query=policy.query
diagnostic_runner.can_start=policy.can_start
diagnostic_runner.query=policy.query

if __name__=='__main__':
    diagnostic_runner.main()
