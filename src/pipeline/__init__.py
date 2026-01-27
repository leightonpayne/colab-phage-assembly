"""Phage Pipeline - Interactive phage genome assembly and annotation."""

from .widget import create_launcher

__version__ = "0.2.0"

def launch():
    """Create and display the interactive pipeline launcher."""
    from IPython.display import display
    try:
        launcher = create_launcher()
        display(launcher)
    except Exception as e:
        print(f"❌ ERROR: {e}")

__all__ = ["create_launcher", "launch"]
