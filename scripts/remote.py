"""Developer helper: run a PowerShell script supplied on stdin via existing SSH auth."""
import base64
import subprocess
import sys

script = '[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); $ProgressPreference="SilentlyContinue";\n' + sys.stdin.read()
result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                         'marcos@10.0.2.141', 'powershell', '-NoProfile', '-EncodedCommand',
                         base64.b64encode(script.encode('utf-16le')).decode()], capture_output=True)
sys.stdout.write(result.stdout.decode('utf-8', errors='replace'))
sys.stderr.write(result.stderr.decode('utf-8', errors='replace'))
sys.exit(result.returncode)
