import os
import subprocess
import sys

files = ["social_media_tracker.py", "server.py", "reBound_browser.py"]

processes = []

# Configuration to hide output streams
spawn_kwargs = {
    "stdout": subprocess.DEVNULL,
    "stderr": subprocess.DEVNULL,
}

# Windows specific flag to prevent creating a console window
if sys.platform.startswith("win"):
    spawn_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

# Launch processes invisibly in the background
for file in files:
    abs_path = os.path.abspath(file)
    p = subprocess.Popen([sys.executable, abs_path], **spawn_kwargs)
    processes.append(p)

print("All scripts are running invisibly in the background.")

# Controller loop waiting for trigger word
while True:
    user_input = input("Type 'stop' to terminate all running scripts: ").strip().lower()
    
    if user_input == "stop":
        print("Terminating background processes...")
        for p in processes:
            p.terminate()  # Sends termination signal
            p.wait()       # Ensures process cleans up completely
        print("All background processes stopped.")
        break

#if you ever accidentally close all your vs code without typing stop, put: taskkill /f /im python.exe    inside of command prompt