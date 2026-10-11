"""Unified source patch preserving exact bytes and missing-newline markers."""
import subprocess


def make_patch(before,after,relative):
    result=subprocess.run(['diff','-u','--label','a/'+relative if before is not None else '/dev/null',
                           '--label','b/'+relative,str(before) if before is not None else '/dev/null',str(after)],
                          text=True,capture_output=True)
    if result.returncode not in (0,1):raise RuntimeError(result.stderr)
    return result.stdout
