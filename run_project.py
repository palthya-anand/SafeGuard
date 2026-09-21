"""
SafeGuard — Project Runner
Launches both the FastAPI backend and the Streamlit dashboard.
"""

import subprocess
import sys
import time
import os
import webbrowser

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    print("=" * 60)
    print("  🚀 Starting SafeGuard System")
    print("=" * 60)

    # 1. Start FastAPI backend
    print("[1/2] Starting FastAPI backend on http://127.0.0.1:8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000"],
        cwd=root_dir,
    )

    # Give backend a moment to initialize
    time.sleep(2)

    # 2. Start Streamlit dashboard
    print("[2/2] Starting Streamlit dashboard on http://127.0.0.1:8501...")
    dashboard_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.headless", "true", "--server.address", "127.0.0.1", "--server.port", "8501"],
        cwd=root_dir,
    )

    print("\n" + "=" * 60)
    print("  ✓ SafeGuard is LIVE!")
    print("  📊 Dashboard: http://localhost:8501")
    print("  🔌 Backend API: http://localhost:8000")
    print("  📖 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    print("\nPress Ctrl+C to terminate both servers.\n")

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend exited unexpectedly!")
                break
            if dashboard_proc.poll() is not None:
                print("Dashboard exited unexpectedly!")
                break
    except KeyboardInterrupt:
        print("\nStopping SafeGuard services...")
    finally:
        backend_proc.terminate()
        dashboard_proc.terminate()
        print("Servers stopped cleanly.")

if __name__ == "__main__":
    main()
