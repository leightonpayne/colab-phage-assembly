"""Phage Pipeline Launcher widget."""

from boilerplate.widget import create_launcher as create_generic_launcher
from .pipeline import PhagePipeline

def create_launcher():
    """Create and configure a PhagePipeline widget.
    
    Returns:
        PipelineWidget: Configured launcher widget ready to be displayed.
    """
    pipeline = PhagePipeline()
    return create_generic_launcher(pipeline)
