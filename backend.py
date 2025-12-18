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

    # 1. Start Celery Worker
    # Using '-P solo' for Windows compatibility to avoid 'spawn' issues without extra deps.
    # If you have 'gevent' installed, you can change 'solo' to 'gevent'.
    celery_command = [
        "celery", 
        "-A", "celery_service.celery_app", 
        "worker", 
        "--loglevel=info", 
        "-P", "solo"
    ]
    
    print(f"   > Launching Celery: {' '.join(celery_command)}")
    # shell=True allows finding the executable in the path more reliably on some Windows setups
    celery_process = subprocess.Popen(
        celery_command, 
        cwd=ROOT,
        shell=True
    )

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
            if celery_process.poll() is not None:
                print("❌ Celery worker terminated unexpected.")
                break
            if api_process.poll() is not None:
                print("❌ API server terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
    finally:
        # Cleanup
        if celery_process.poll() is None:
            print("   > Killing Celery...")
            # On Windows, terminate() sends SIGTERM which might be ignored by shell=True wrappers
            # We use taskkill to be sure the tree is dead
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(celery_process.pid)])
        
        if api_process.poll() is None:
            print("   > Killing API...")
            api_process.terminate()
            api_process.wait()

if __name__ == "__main__":
    main()
