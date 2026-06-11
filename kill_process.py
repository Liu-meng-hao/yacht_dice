import os
import signal

# 杀掉占用 8000 端口的进程
try:
    os.kill(25060, signal.SIGTERM)
    print(f"Killed process 25060")
except Exception as e:
    print(f"Error: {e}")

try:
    os.kill(25664, signal.SIGTERM)
    print(f"Killed process 25664")
except Exception as e:
    print(f"Error: {e}")

print("Done!")
