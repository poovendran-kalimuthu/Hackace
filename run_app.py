"""
Unified Desktop Application Launcher.

Starts the local high-performance FastAPI backend server, binds WebSocket telemetry,
spawns the Vite desktop interface, and launches the application.
"""

import os
import sys
import time
import subprocess
import webbrowser
import threading
import uvicorn

# Add root directory to python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api.server import create_app


def run_backend(host="127.0.0.1", port=8000):
    """Run local FastAPI backend server."""
    workspace_dir = os.path.join(ROOT_DIR, "workspaces")
    app = create_app(workspace_root=workspace_dir)
    print(f"[Backend] Starting local offline API server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main():
    print("=" * 70)
    print("   DocuCraft Pro: Intelligent Offline Document & Book Formatter")
    print("   100% Offline • Zero Cloud AI • Up to 10,000+ Pages Support")
    print("=" * 70)

    # 1. Start Backend in separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    time.sleep(1.5)

    # 2. Check if Vite frontend is installed
    frontend_dir = os.path.join(ROOT_DIR, "frontend")
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("[Frontend] Installing frontend dependencies via npm install...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, shell=True)

    print("[Frontend] Starting desktop interface...")
    # Start Vite in subprocess
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=True,
    )

    # 3. Open desktop browser window
    app_url = "http://localhost:5173"
    print(f"\n>>> Application ready at: {app_url}")
    print(">>> Opening application in your browser/desktop shell...\n")
    time.sleep(2)
    webbrowser.open(app_url)

    try:
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down DocuCraft Pro...")
        frontend_proc.terminate()


if __name__ == "__main__":
    main()
