"""OSC-01 discarded-state rehearsal; backup delegates to the deployed operator."""
from pathlib import Path
import runpy
import subprocess
import sys

if sys.argv[1:] == ['rehearse']:
    subprocess.run([sys.executable,'-B','/opt/guala_oscillation_proof.py',
        '--capture','/opt/osc01-capture.json','--sha256',
        'c5c80e2baa61f3572e5b14118d090236f26f05b6fbd08c650c61a3dd71490373'],check=True,timeout=150)
elif sys.argv[1:] == ['backup']:
    runpy.run_path('/opt/a1_retention_release_operator.py',run_name='__main__')
else:
    raise RuntimeError('unknown OSC-01 operator mode')
