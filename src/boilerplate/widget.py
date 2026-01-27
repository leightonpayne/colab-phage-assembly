
from pathlib import Path
import threading

import anywidget
import traitlets
from .core import Pipeline
from .utils import run_with_logs, check_colab, keep_alive_thread

class PipelineWidget(anywidget.AnyWidget):
    """Generic Pipeline Widget."""
    
    _esm = (Path(__file__).parent / "widget.js").read_text()
    
    # Traits synced with JS
    params_schema = traitlets.Dict().tag(sync=True)
    config = traitlets.Dict().tag(sync=True)
    
    # State synced from JS to Python
    params_values = traitlets.Dict().tag(sync=True)
    
    # Control signals
    run_requested = traitlets.Bool(False).tag(sync=True)
    terminate_requested = traitlets.Bool(False).tag(sync=True)
    action_requested = traitlets.Unicode("").tag(sync=True)
    status_state = traitlets.Unicode("idle").tag(sync=True)
    status_message = traitlets.Unicode("").tag(sync=True)
    logs = traitlets.Unicode("").tag(sync=True)
    html_output = traitlets.Unicode("").tag(sync=True)
    
    # Results
    result_file_name = traitlets.Unicode("").tag(sync=True)
    result_file_data = traitlets.Unicode("").tag(sync=True)
    
    def __init__(self, pipeline: Pipeline, **kwargs):
        self.pipeline = pipeline
        
        # Initialize traits from pipeline definition before super().__init__
        # to ensure they are available for the initial frontend render.
        schema = self.pipeline.get_schema()
        params_schema = schema.get("parameters", {})
        config = schema.get("config", {})
        
        # Populate initial values from defaults
        initial_values = {}
        for cat in params_schema.values():
            for p in cat:
                if p.get("def") is not None:
                    initial_values[p["name"]] = p["def"]
        
        # Merge into kwargs if not already provided
        kwargs.setdefault("params_schema", params_schema)
        kwargs.setdefault("config", config)
        kwargs.setdefault("params_values", initial_values)
        
        super().__init__(**kwargs)
        self._setup_observers()
        
        # Start keepalive if in Colab
        if check_colab():
            keep_alive_thread()
        
    def _setup_observers(self):
        self.observe(self._on_run_requested, names=["run_requested"])
        self.observe(self._on_terminate_requested, names=["terminate_requested"])
        self.observe(self._on_action_requested, names=["action_requested"])

    def _on_terminate_requested(self, change):
        if not change.new: return
        self.terminate_requested = False
        
        self.logs = (self.logs or "") + "\n❯ Terminating pipeline...\n"
        self.pipeline.terminate()
        self.status_state = "aborted"
        self.status_message = "Terminated by user"
        
    def _on_run_requested(self, change):
        if not change.new: 
            return
        
        # Reset flag immediately
        self.run_requested = False
        self.status_state = "running"
        self.status_message = "Pipeline running..."
        self.logs = "" # Clear logs or keep? Let's clear for new run
        self.result_file_data = "" # Clear previous result
        self.result_file_name = ""
        
        def append_log(text: str):
            self.logs = (self.logs or "") + text
            
        def run_thread():
            try:
                success = False

                from contextlib import redirect_stderr, redirect_stdout
                from .utils import LogWriter
                import base64
                
                log_writer = LogWriter(append_log)
                
                with redirect_stdout(log_writer), redirect_stderr(log_writer):
                    append_log("❯ Starting Pipeline...\n")
                    success = self.pipeline.run(self.params_values, log_writer)
                
                if success:
                    self.status_state = "finished"
                    self.status_message = "Completed successfully"
                    append_log("\n❯ Completed successfully!\n")
                    
                    # Process result file
                    try:
                        project_name = self.params_values.get("output_name", "phage_project")
                        import os
                        zip_path = Path.cwd() / f"{project_name}_results.zip"
                        if zip_path.exists():
                            append_log(f"❯ Preparing download button for {zip_path.name}...\n")
                            # Check size - limit to 50MB for widget performance
                            size_mb = zip_path.stat().st_size / (1024 * 1024)
                            if size_mb > 50:
                                append_log(f"❯ File is too large ({size_mb:.1f}MB) for widget download. Please use file explorer.\n")
                            else:
                                with open(zip_path, "rb") as f:
                                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                                    self.result_file_name = zip_path.name
                                    self.result_file_data = f"data:application/zip;base64,{b64_data}"
                                append_log("❯ Ready to download.\n")
                    except Exception as e:
                        append_log(f"❯ Error preparing download: {e}\n")
                        
                elif getattr(self.pipeline, "_stop_requested", False):
                    self.status_state = "aborted"
                    self.status_message = "Terminated by user"
                    append_log("\n❯ Pipeline was terminated.\n")
                else:
                    self.status_state = "error"
                    self.status_message = "Failed"
                    append_log("\n❯ Pipeline failed.\n")
                    
            except Exception as e:
                self.status_state = "error"
                self.status_message = f"Error: {e}"
                append_log(f"\n❯ Exception: {e}\n")
        
        # Run in thread to not block UI
        threading.Thread(target=run_thread, daemon=True).start()

    def _on_action_requested(self, change):
        if not change.new: 
            return
        action_name = change.new
        
        # Reset flag
        self.action_requested = ""
        
        self.status_state = "running"
        self.logs = f"❯ Executing action: {action_name}...\n"
        
        def _target(logger):
            try:
                success = self.pipeline.handle_action(action_name, logger)
                self.status_state = "idle" if success else "error"
            except Exception as e:
                logger.write(f"❯ Action error: {str(e)}\n")
                self.status_state = "error"

        threading.Thread(target=run_with_logs, args=(_target, self)).start()

def create_launcher(pipeline: Pipeline) -> PipelineWidget:
    """Helper to create the widget."""
    return PipelineWidget(pipeline)
