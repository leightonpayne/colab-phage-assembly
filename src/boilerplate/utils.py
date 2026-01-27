import io
import sys
import os
import subprocess
import threading
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from typing import Callable, Union, Any

def check_colab() -> bool:
    """Check if running in Google Colab."""
    return "google.colab" in sys.modules

def setup_colab():
    """Install Pixi and dependencies if running in Google Colab."""
    if not check_colab():
        return  # Not in Colab, skip
        
    print("✨ Detecting Google Colab environment...")
    
    # Install Pixi if not present
    if subprocess.call("which pixi", shell=True) != 0:
        print("📦 Installing Pixi package manager...")
        subprocess.run("curl -fsSL https://pixi.sh/install.sh | bash", shell=True, check=True)
        os.environ["PATH"] += os.pathsep + str(Path.home() / ".pixi/bin")
        
    # Install dependencies from pixi.lock
    print("🚀 Installing bioinformatics tools from pixi.lock...")
    subprocess.run("pixi install", shell=True, check=True)
    
    # Add pixi environment to PATH for this session
    # The default environment path is usually .pixi/envs/default
    pixi_env_bin = Path.cwd() / ".pixi/envs/default/bin"
    if pixi_env_bin.exists():
        os.environ["PATH"] = str(pixi_env_bin) + os.pathsep + os.environ["PATH"]
        print(f"✅ Added {pixi_env_bin} to PATH")
        
    print("✅ Environment setup complete!")

class LogWriter(io.StringIO):
    """A StringIO that calls a callback on each write."""
    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback

    def write(self, s: str) -> int:
        self.callback(s)
        return len(s)

    def flush(self):
        pass

def run_with_logs(func: Callable, log_callback: Union[Callable[[str], None], Any], *args, **kwargs):
    """Run a function with stdout/stderr redirected to a callback or widget logs."""
    
    def _log(text: str):
        if hasattr(log_callback, "logs"):
            # It's a widget with a logs trait
            log_callback.logs = (log_callback.logs or "") + text
        elif callable(log_callback):
            log_callback(text)

    log_writer = LogWriter(_log)
    try:
        with redirect_stdout(log_writer), redirect_stderr(log_writer):
            func(log_writer, *args, **kwargs)
    except Exception as e:
        _log(f"❌ Error: {e}\n")
        raise e

def keep_alive_thread(interval_seconds: int = 30):
    """Start a background thread to keep Colab alive (if needed)."""
    def _heartbeat():
        import time
        while True:
            time.sleep(interval_seconds)
            # No-op

    # Only start if not already running (simplified check)
    # in a real app potentially manage thread lifecycle better
    t = threading.Thread(target=_heartbeat, daemon=True)
    t.start()
    return t
