import subprocess
import re

print("Finding processes using port 8000...")
result = subprocess.run(
    ['netstat', '-ano'],
    capture_output=True,
    text=True,
    shell=True
)

# 查找 8000 端口
pattern = r':8000\s+.*LISTENING\s+(\d+)'
matches = re.findall(pattern, result.stdout)

if matches:
    pids = set(matches)
    print(f"Found PIDs: {pids}")
    
    for pid in pids:
        try:
            print(f"Killing process {pid}...")
            subprocess.run(
                ['taskkill', '/F', '/PID', pid],
                shell=True,
                capture_output=True
            )
        except Exception as e:
            print(f"Error killing {pid}: {e}")
else:
    print("No process found on port 8000")

print("Done!")
