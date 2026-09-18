"""
DocuCraft Pro - Native Python Desktop GUI Launcher.

Launches the offline FastAPI backend, Vite dev server, and wraps the application
inside a native desktop window powered by pywebview.
"""

import os
import sys
import time
import subprocess
import threading
import uvicorn
import psutil

# Add root directory to python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api.server import create_app


def free_ports(ports=(8000, 5173)):
    """Find and terminate any existing processes using the specified ports."""
    current_pid = os.getpid()
    for port in ports:
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port == port and conn.pid and conn.pid != current_pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        print(f"[Port Cleanup] Clearing port {port} used by {proc.name()} (PID {conn.pid})...")
                        proc.terminate()
                        proc.wait(timeout=2)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    except Exception:
                        pass
        except Exception:
            pass


def run_backend(host="127.0.0.1", port=8000):
    """Run local FastAPI backend server."""
    workspace_dir = os.path.join(ROOT_DIR, "workspaces")
    app = create_app(workspace_root=workspace_dir)
    print(f"[Backend] Starting local offline API server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main():
    print("=" * 70)
    print("   DocuCraft Pro: Native Python Desktop GUI")
    print("   100% Offline • Zero Cloud AI • Native Windows Desktop Window")
    print("=" * 70)

    # 0. Free ports if in use by previous background instances
    free_ports([8000, 5173])
    time.sleep(0.5)

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
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=True,
    )

    app_url = "http://localhost:5173"
    print(f"\n>>> Launching Native Desktop GUI Window at: {app_url}\n")
    time.sleep(2)

    try:
        import webview
        # Open Native Desktop Window
        webview.create_window(
            title="DocuCraft Pro - Intelligent Offline Document & Book Formatter",
            url=app_url,
            width=1280,
            height=850,
            resizable=True,
            min_size=(900, 600),
        )
        webview.start()
    except Exception as e:
        print(f"[GUI Fallback] pywebview GUI exception: {e}")
        print("Fallback to standard web browser window...")
        import webbrowser
        webbrowser.open(app_url)
        frontend_proc.wait()
    finally:
        print("\nShutting down DocuCraft Pro Desktop GUI...")
        try:
            frontend_proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
