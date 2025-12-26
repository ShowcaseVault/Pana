import subprocess
import time
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent

def main():
    """
    Starts both the Celery worker and the FastAPI server.
    """
    print("🚀 Starting Pana Backend Integration...")

    # 1. Start Celery Workers (Dedicated Queues)
    # Using '-P solo' for Windows compatibility to avoid 'spawn' issues without extra deps.
    
    # High Priority Worker
    celery_command_high = [
        "celery", "-A", "celery_service.celery_app", "worker", 
        "--loglevel=info", "-P", "solo", "-Q", "high_priority", "-n", "high_worker@%h"
    ]
    print(f"   > Launching High Priority Celery: {' '.join(celery_command_high)}")
    celery_process_high = subprocess.Popen(celery_command_high, cwd=ROOT, shell=True)

    # Default Priority Worker
    celery_command_default = [
        "celery", "-A", "celery_service.celery_app", "worker", 
        "--loglevel=info", "-P", "solo", "-Q", "default", "-n", "default_worker@%h"
    ]
    print(f"   > Launching Default Priority Celery: {' '.join(celery_command_default)}")
    celery_process_default = subprocess.Popen(celery_command_default, cwd=ROOT, shell=True)

    # 2. Start FastAPI Server
    api_command = ["python", "-m", "api.server"]
    print(f"   > Launching API: {' '.join(api_command)}")
    api_process = subprocess.Popen(
        api_command, 
        cwd=ROOT
    )

    print("\n✅ Services are running. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(0.5)
            # Check if any process has exited unexpectedly
            if celery_process_high.poll() is not None:
                print("❌ High priority Celery worker terminated unexpectedly.")
                break
            if celery_process_default.poll() is not None:
                print("❌ Default priority Celery worker terminated unexpectedly.")
                break
            if api_process.poll() is not None:
                print("❌ API server terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
    finally:
        # Cleanup
        for name, process in [
            ("High Priority Celery", celery_process_high),
            ("Default Priority Celery", celery_process_default),
            ("API", api_process)
        ]:
            if process.poll() is None:
                print(f"   > Killing {name}...")
                if "Celery" in name:
                    # On Windows, we use taskkill to be sure the tree is dead
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(process.pid)])
                else:
                    process.terminate()
                    process.wait()

if __name__ == "__main__":
    main()
